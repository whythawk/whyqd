# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path

import polars as pl

from whyqd.dtypes import MimeType
from whyqd.models import DialectModel
from whyqd.parsers.cell import CellParser
from whyqd.parsers.grid import GridParser


class ArrowParser:
    """A Parquet or Feather file as the grid: its column names as the first row, then each value in whyqd's text.

    A columnar file stores types, not text, so each value is rendered as `CellParser.render` gives it, and the file
    reads as the same table written as a CSV does. Its names are its header row, so the dialect's defaults read them.
    """

    PLACE = "row"

    def __init__(self) -> None:
        self.cell = CellParser()
        self.grids = GridParser()

    def grid(self, *, source: Path, mime: MimeType, dialect: DialectModel) -> tuple[pl.DataFrame, list[int], DialectModel]:
        """The file's grid, the row of the file each grid row is, counted from 1, and the dialect unchanged.

        Raises
        ------
        ValueError
            For a column holding a type whyqd has no text for, naming it.
        """
        df = pl.read_parquet(source) if mime in (MimeType.PARQUET, MimeType.PRQ) else pl.read_ipc(source)
        columns = {}
        for i, name in enumerate(df.columns):
            try:
                cells = [self.cell.render(value=v) for v in df[name].to_list()]
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"`{source.name}` column `{name}` holds {df.schema[name]} values, which whyqd cannot read as text "
                    f"({e}). Write the column as text, numbers, booleans, or dates."
                ) from e
            columns[f"column_{i}"] = [name, *(None if c is None else c[1] for c in cells)]
        grid = self.grids.trim(grid=pl.DataFrame(columns, schema={c: pl.String for c in columns}))
        return grid, list(range(1, grid.height + 1)), dialect
