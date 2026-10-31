# SPDX-License-Identifier: BSD-3-Clause
import polars as pl

from whyqd.dtypes import CellType


class GridParser:
    """The grid every reader gives: each cell's text, null where empty, in columns `column_0` on, and beside it each
    cell's stored type, a `CellType`, in a frame of the same shape.

    A format that stores no types (CSV, PDF) holds text only, so each of its cells is `s`. A reader's grid is trimmed
    of trailing empty rows and columns, so a file's grid does not depend on how far a program that saved it left empty
    cells: a trailing delimiter, or a workbook's used range past its data.
    """

    def trim(self, *, grid: pl.DataFrame, types: pl.DataFrame | None = None) -> tuple[pl.DataFrame, pl.DataFrame]:
        """The grid and its types without the grid's trailing empty columns and rows.

        Parameters
        ----------
        grid: pl.DataFrame
        types: pl.DataFrame | None, default None
            Each cell's `CellType` value, in the grid's shape; where `None`, every cell holding text is `s`.

        Example
        -------
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
