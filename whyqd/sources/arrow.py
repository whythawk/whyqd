# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
from typing import ClassVar

import polars as pl

from whyqd.dtypes import CellType, MimeType, Place
from whyqd.models import DialectModel
from whyqd.sources.cell import CellParser
from whyqd.sources.grid import GridParser
from whyqd.sources.reader import Reader


class ArrowParser(Reader):
    """A Parquet or Feather file as the grid: its column names as the first row, then each value in whyqd's text.

    A columnar file stores types, not text, so each value is rendered as `CellParser.render` gives it, and the file
    reads as the same table written as a CSV does. Its names are its header row, so the dialect's defaults read them.
    """

    PLACE: ClassVar[Place] = Place.ROW
    DIALECT: ClassVar[tuple[str, ...]] = ()

    def __init__(self) -> None:
        self.cell = CellParser()
        self.grids = GridParser()

    def grid(
        self, *, source: Path, mime: MimeType, dialect: DialectModel
    ) -> tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel]:
        """The file's grid and each value's type (its names `s`), the row of the file each grid row is, counted from
        1, and the dialect unchanged.

        Raises:
          ValueError: For a file that is not what its format says, or a column holding a type whyqd has no text for,
            naming it.
        """
        try:
            df = pl.read_parquet(source) if mime == MimeType.PARQUET else pl.read_ipc(source)
        except pl.exceptions.PolarsError as e:
            raise self.unreadable(source=source, kind=f"a {mime.name} file") from e
        columns, types = [], []
        for name in df.columns:
            try:
                cells = [self.cell.render(value=v) for v in df[name].to_list()]
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"`{source.name}` column `{name}` holds {df.schema[name]} values, which whyqd cannot read as text "
                    f"({e}). Write it as text, numbers, booleans, or dates. [whyqd:arrow-type]"
                ) from e
            columns.append([name, *(None if c is None else c[1] for c in cells)])
            types.append([CellType.STRING.value, *(None if c is None else c[0].value for c in cells)])
        grid, types = self.grids.build(columns=columns, types=types)
        return grid, types, self.grids.numbers(grid=grid), dialect
