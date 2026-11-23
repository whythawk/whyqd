# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from functools import partial

import polars as pl

from whyqd.dtypes import CellType, FieldType
from whyqd.models import PolicyModel
from whyqd.reading.booleans import BooleanParser
from whyqd.reading.dates import DateParser
from whyqd.reading.durations import DurationParser
from whyqd.reading.numbers import NumberParser
from whyqd.reading.reader import BaseReadingParser


class ReadingParser(BaseReadingParser):
    """Read a column's cells as the type its field declares: each a value, a blank, or a refusal with its reason.

    A cell reads by the declaration alone, never by another cell or the machine's locale, and a cell it cannot read is
    refused, never read another way. A workbook's stored cell is already a value, so a policy's text rules read only
    text cells. A cell without a type is text. Each type has its own reader, which this sends the column to.

    Examples:
      ```python
      import polars as pl

      from whyqd.models import PolicyModel
      from whyqd.reading.reading import ReadingParser

      policy = PolicyModel(format={"decimalChar": ",", "groupChar": "."}, rules={"currency": ["€"]})
      cells = pl.Series(["1.234,50 €", "1,234.50", ""])
      ReadingParser().column(cells=cells, dtype="number", policy=policy)["kind"]   # value, refused, blank
      ```
    """

    def __init__(self) -> None:
        super().__init__()
        self.numbers = NumberParser()
        self.booleans = BooleanParser()
        self.dates = DateParser()
        self.durations = DurationParser()
        self.readers = {
            FieldType.NUMBER.value: self.numbers.read_number,
            FieldType.INTEGER.value: self.numbers.read_integer,
            FieldType.BOOLEAN.value: self.booleans.read_boolean,
            FieldType.STRING.value: self.read_string,
            FieldType.DATE.value: partial(self.dates.read_temporal, dtype=FieldType.DATE.value),
            FieldType.TIME.value: partial(self.dates.read_temporal, dtype=FieldType.TIME.value),
            FieldType.DATETIME.value: partial(self.dates.read_temporal, dtype=FieldType.DATETIME.value),
            FieldType.MONTH.value: partial(self.dates.read_temporal, dtype=FieldType.MONTH.value),
            FieldType.QUARTER.value: partial(self.dates.read_temporal, dtype=FieldType.QUARTER.value),
            FieldType.YEAR.value: partial(self.dates.read_temporal, dtype=FieldType.YEAR.value),
            FieldType.DURATION.value: self.durations.read_duration,
        }

    def column(
        self, *, cells: pl.Series, dtype: str, policy: PolicyModel | None = None, types: pl.Series | None = None
    ) -> pl.DataFrame:
        """A column's readings, one row to a cell: its `kind`, `value`, `reason`, `detail`, and `warnings`, and for a
        number the currency `marks` it holds.

        Parameters:
          cells: Each cell's text as stored, null where empty.
          dtype: The field's type.
          policy: The field's declaration; with none, the type's canonical form.
          types: Each cell's `CellType` tag, for a file that stores them.

        Returns:
          One row to a cell, in the order given.

        Raises:
          AttributeError: For a type with no reader.
        """
        if dtype == FieldType.USDATE.value:
            dtype, policy = FieldType.DATE.value, policy or PolicyModel(**PolicyModel.USDATE)
        if dtype not in self.readers:
            raise AttributeError(f"`{dtype}` has no reader.")
        # A Series method runs as `col(series.name)`, so a source's column name must not reach it
        cells = cells.alias(self.CELL)
        types = pl.repeat(CellType.STRING.value, cells.len(), eager=True) if types is None else types
        types = types.alias(self.CELL).fill_null(CellType.STRING.value)
        return self.readers[dtype](cells=cells, types=types, policy=policy or PolicyModel())
