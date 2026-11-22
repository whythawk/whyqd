# SPDX-License-Identifier: BSD-3-Clause
from typing import ClassVar

import polars as pl

from whyqd.dtypes import CellType


class ReadFault(ValueError):
    """A file that cannot be read as its dialect describes, saying where, and which setting addresses it."""

    def __init__(self, message: str, *, rows: list[int] | None = None, setting: str | None = None) -> None:
        super().__init__(message)
        self.rows = rows or []
        self.setting = setting


class GridParser:
    """The grid every reader gives: each cell's text, null where empty, in columns `column_0` on, and beside it each
    cell's type, a `CellType`, in a frame of the same shape.

    A format that stores no types (CSV, PDF) holds text only, so each of its cells is `s`. A reader's grid is trimmed
    of trailing empty rows and columns, so a file's grid does not depend on how far a program that saved it left empty
    cells: a trailing delimiter, or a workbook's used range past its data.
    """

    COLUMN: ClassVar[str] = "column_{}"

    def build(
        self, *, columns: list[list[str | None]], types: list[list[str | None]] | None = None
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """The grid and its types from a reader's columns, trimmed.

        Parameters:
            columns: Each column's cells, top to bottom, as text, `None` where empty.
            types: Each cell's `CellType` value, in the columns' shape; where `None`, every cell holding text is `s`.

        Examples:
            ```python
            GridParser().build(columns=[["Code", "12"]], types=[["s", "n"]])
            ```
        """
        names = [self.COLUMN.format(i) for i in range(len(columns))]
        schema = {name: pl.String for name in names}
        grid = pl.DataFrame(dict(zip(names, columns, strict=True)), schema=schema)
        if types is not None:
            types = pl.DataFrame(dict(zip(names, types, strict=True)), schema=schema)
        return self.trim(grid=grid, types=types)

    def from_rows(self, *, rows: list[list[str | None]]) -> tuple[pl.DataFrame, pl.DataFrame]:
        """The grid and its types from rows of text, as wide as the widest, a shorter row's missing cells and any
        empty text `None`.

        Examples:
            ```python
            GridParser().from_rows(rows=[["Code", "Name"], ["12"]])   # two columns, "Name" above an empty cell
            ```
        """
        width = max((len(row) for row in rows), default=0)
        return self.build(columns=[[(row[i] or None) if i < len(row) else None for row in rows] for i in range(width)])

    def numbers(self, *, grid: pl.DataFrame) -> list[int]:
        """Each grid row's number, counted from 1, for a format whose rows are its own: a sheet's, or a PDF's in the
        order read."""
        return list(range(1, grid.height + 1))

    def trim(self, *, grid: pl.DataFrame, types: pl.DataFrame | None = None) -> tuple[pl.DataFrame, pl.DataFrame]:
        """The grid and its types without the grid's trailing empty columns and rows.

        Parameters:
            grid: Each cell's text, null where empty.
            types: Each cell's `CellType` value, in the grid's shape; where `None`, every cell holding text is `s`.

        Examples:
            ```python
            grid = pl.DataFrame({"column_0": ["a", None], "column_1": [None, None]})
            GridParser().trim(grid=grid)   # one column, one row: "a", typed "s"
            ```
        """
        filled = [c for c in grid.columns if grid[c].null_count() < grid.height]
        if not filled:
            grid = grid.clear().select([])
        else:
            grid = grid.select(grid.columns[: grid.columns.index(filled[-1]) + 1])
            rows = grid.select(pl.any_horizontal(pl.all().is_not_null())).to_series()
            grid = grid.head(rows.arg_true().max() + 1)
        if types is None:
            types = grid.select(
                pl.when(pl.col(c).is_not_null()).then(pl.lit(CellType.STRING.value)).alias(c) for c in grid.columns
            )
        else:
            types = types.select(grid.columns).head(grid.height)
        return grid, types
