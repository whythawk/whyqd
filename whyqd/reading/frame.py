# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import ast
import math
from decimal import Decimal
from typing import ClassVar

import pandas as pd
import polars as pl

from whyqd.dtypes import CellType, FieldType
from whyqd.models import PolicyModel
from whyqd.reading.reading import ReadingParser
from whyqd.sources.cell import CellParser


class FrameParser:
    """What crosses between the actions' pandas frames and the reader's Polars columns, until the actions are written in
    Polars: a pandas column as cells to read, a reading as a pandas column, and whether a column already holds a type.

    Examples:
      ```python
      frame = FrameParser()
      frame.values(column=df["amount"], dtype="number", policy=policy)
      frame.is_typed_as(df["date"], "date")
      ```
    """

    TEXT: ClassVar[str] = FieldType.STRING.value
    PANDAS: ClassVar[dict[str, str]] = {
        FieldType.NUMBER.value: "Float64",
        FieldType.INTEGER.value: "Int64",
        FieldType.BOOLEAN.value: "boolean",
        FieldType.STRING.value: "string",
    }

    def __init__(self) -> None:
        self.reading = ReadingParser()
        self.cell = CellParser()

    def cells(self, column: pd.Series) -> pl.Series:
        """A pandas column's values as text cells, null where missing."""
        texts = [None if pd.isna(value) else str(value) for value in column.astype(object).tolist()]
        return pl.Series(self.reading.CELL, texts, dtype=pl.String)

    def without_blanks(self, *, column: pd.Series) -> pd.Series:
        """A text column with each blank cell, empty or only whitespace, as an empty one: a blank is never a value."""
        return column.where(~self.reading.is_blank(self.cells(column)).to_numpy(), None)

    def is_usable_as(self, column: pd.Series, dtype: str) -> bool:
        """Whether an action can use a column's values as they are, as a number or a date."""
        kind = str(column.dtype).lower()
        if dtype == FieldType.NUMBER.value:
            return kind in ("float64", "int64")
        return dtype == FieldType.DATE.value and "datetime64" in kind

    def values(self, *, column: pd.Series, dtype: str, policy: PolicyModel | None = None) -> pd.Series:
        """A column an action reads as `dtype`: as it is if already typed, or read by its field's declaration, with a
        cell that cannot be read left empty, since the transform has already recorded its refusal."""
        if self.is_usable_as(column, dtype):
            if dtype == FieldType.NUMBER.value:
                return pd.Series(column.to_numpy(dtype="float64", na_value=float("nan")), index=column.index)
            return column
        read = self.reading.column(cells=self.cells(column), dtype=dtype, policy=policy)
        if dtype == FieldType.NUMBER.value:
            return pd.Series(read[self.reading.VALUE].to_list(), index=column.index, dtype="Float64").astype("float64")
        return pd.Series(pd.to_datetime(read[self.reading.VALUE].to_list(), errors="coerce"), index=column.index)

    def pandas(self, value: pl.Series, dtype: str, index: pd.Index) -> pd.Series:
        """A read column for the pandas frame."""
        if nullable := self.PANDAS.get(dtype):
            return pd.Series(value.to_list(), dtype=nullable if value.dtype != pl.Decimal else object, index=index)
        return pd.Series(value.to_pandas().to_numpy(), index=index)

    def strings(self, cells: pl.Series, index: pd.Index) -> pd.Series:
        """A column kept as text for the pandas frame, null where empty."""
        return (
            cells.to_pandas()
            .astype(self.PANDAS[self.TEXT])
            .set_axis(index)
            .astype(object)
            .where(cells.is_not_null().to_numpy(), None)
        )

    def as_cells(self, column: pd.Series) -> tuple[pl.Series, pl.Series]:
        """A built column as a reader takes it: each value's text and cell type, rendered as a stored cell would be, so
        a value has one text whichever path it takes. Text, an empty one included, stays as written; an exact decimal
        and an infinity, which no cell stores, keep their own text."""
        texts, tags = [], []
        for value in column.astype(object).tolist():
            if value is None or value is pd.NA or value is pd.NaT or (isinstance(value, float) and math.isnan(value)):
                tag, text = CellType.STRING, None
            elif isinstance(value, str):
                tag, text = CellType.STRING, value
            elif isinstance(value, Decimal) or (isinstance(value, float) and math.isinf(value)):
                tag, text = CellType.NUMBER, str(value)
            else:
                tag, text = self.cell.render(value=value)
            texts.append(text)
            tags.append(tag.value)
        return pl.Series(self.reading.CELL, texts, dtype=pl.String), pl.Series(self.reading.CELL, tags, dtype=pl.String)

    def as_list(self, value) -> list | None:
        """An array's value, from a list or the literal a saved file holds, each item as text."""
        if isinstance(value, str):
            value = ast.literal_eval(value)
        if value is None or not len(value):
            return None
        return [None if pd.isna(item) else self.as_item(item) for item in value]

    def as_item(self, item) -> str:
        """An array's item as text: a date read at the source as its date alone, as a date cell renders."""
        if isinstance(item, pd.Timestamp) and item == item.normalize():
            return item.date().isoformat()
        return str(item).strip()

    def is_typed_as(self, column: pd.Series, dtype: str) -> bool:
        """Whether a built column already holds its destination type, so it is passed on as it is."""
        kind = str(column.dtype).lower()
        if dtype == FieldType.NUMBER.value:
            return kind in ("float64", "float32")
        if dtype == FieldType.BOOLEAN.value:
            return kind == "boolean"
        if dtype == FieldType.DATE.value:
            values = column.dropna()
            return "datetime64" in kind and "," not in kind and (values == values.dt.normalize()).all()
        if dtype == FieldType.DATETIME.value:
            return "datetime64" in kind
        if dtype == FieldType.TIME.value:
            return (
                kind == "object"
                and column.dropna().map(lambda v: type(v).__name__ == "time").all()
                and column.notna().any()
            )
        if dtype == FieldType.DURATION.value:
            return "timedelta" in kind
        return False
