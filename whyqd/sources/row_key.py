# SPDX-License-Identifier: BSD-3-Clause
from collections.abc import Iterable
import re
from typing import ClassVar

from whyqd.config.patterns import PythonPatterns
from whyqd.sources.column import ColumnParser


class RowKeyParser:
    """The row key: every row's number from the read, carried through every action.

    Rows are numbered from `0` by their position in the table as read, each sheet from `0`: row `0` is the first row
    after the header, or the file's first where its dialect declares no header row (`headerRowCount` 0). A 1.x data
    source reads by a dialect with no header row, so its rows are numbered as 1.x numbered them. An action never
    renumbers a row, so `DELETE_ROWS` and `PIVOT_CATEGORIES` address the same rows wherever they run.

    The key is the column `__row__`. An action that turns one row into several adds a part, `__row__1` and so on,
    holding the row's position within the rows it made; sorting by every part, in order, gives the table its order.

    The key is not in the source, so it is never a field of the source schema. A source may already hold a column
    named like one of its parts, so adding the key takes three steps, in order: check the source's names, rename any
    that clash (`deconflict`), then add the key. The renamed column keeps its data, and its new name is its name
    everywhere: in the source schema, every preview, and every crosswalk script. The key is added by Polars'
    `with_row_index`, which refuses an existing name, never by assignment, which would overwrite a column that slipped
    through.
    """

    ROW: ClassVar[str] = "__row__"

    def __init__(self) -> None:
        self.column = ColumnParser()
        self.patterns = PythonPatterns()
        self._part = re.compile(self.patterns.ROW_PART.format(row=re.escape(self.ROW)))

    def is_part(self, column: str) -> bool:
        """Whether a column name is a part of the row key: `__row__`, or `__row__1` and on, never `__row__0`."""
        match = self._part.match(column)
        return bool(match) and match.group(1) != "0"

    def deconflict(self, *, columns: Iterable[str]) -> list[str]:
        """Source column names with any named like a part of the key renamed, so the key can be added.

        Parameters:
          columns: Column names as read from the source.

        Returns:
          The names as `ColumnParser.deconflict` gives them: `__row__` becomes `__row__.1`.
        """
        return self.column.deconflict(columns=columns, reserved=self.is_part)
