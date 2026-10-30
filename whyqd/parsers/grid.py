# SPDX-License-Identifier: BSD-3-Clause
import polars as pl


class GridParser:
    """The grid every reader gives: each cell's text, null where empty, in columns `column_0` on.

    A reader's grid is trimmed of trailing empty rows and columns, so a file's grid does not depend on how far a program
    that saved it left empty cells: a trailing delimiter, or a workbook's used range past its data.
    """

    def trim(self, *, grid: pl.DataFrame) -> pl.DataFrame:
        """The grid without its trailing empty columns and rows.

        Example
        -------
        ```python
        grid = pl.DataFrame({"column_0": ["a", None], "column_1": [None, None]})
        GridParser().trim(grid=grid)   # one column, one row: "a"
        ```
        """
        filled = [c for c in grid.columns if grid[c].null_count() < grid.height]
        if not filled:
            return grid.clear().select([])
        grid = grid.select(grid.columns[: grid.columns.index(filled[-1]) + 1])
        rows = grid.select(pl.any_horizontal(pl.all().is_not_null())).to_series()
        return grid.head(rows.arg_true().max() + 1)
