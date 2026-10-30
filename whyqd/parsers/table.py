# SPDX-License-Identifier: BSD-3-Clause
import polars as pl

from whyqd.models import DialectModel
from whyqd.parsers.row_key import RowKeyParser


class TableParser:
    """The grid as a table: the rows below the header, each column named once, each row keyed.

    In order: the rows before the header are skipped (`skipRows`); records over several rows are joined
    (`rowsPerRecord`); the header rows (`headerRowCount`) name the columns and leave the table; the row key is added.
    Nothing is inferred from the data: every setting is the dialect's, with its defaults.
    """

    def __init__(self) -> None:
        self.row_key = RowKeyParser()

    def table(
        self, *, grid: pl.DataFrame, lines: list[int], dialect: DialectModel, names: list[str] | None = None
    ) -> pl.DataFrame:
        """The table a grid reads as under its dialect, its first column the row key.

        Parameters
        ----------
        grid: pl.DataFrame
            Each cell's text, null where empty, as a reader gives it.
        lines: list[int]
            The line of the file each grid row starts on, counted from 1, for messages.
        dialect: DialectModel
        names: list[str] | None, default None
            One name per column, in place of the header row's; required for a header over several rows.

        Raises
        ------
        ValueError
            For a declaration the file does not fit, or one that is incomplete.

        Returns
        -------
        pl.DataFrame
            Row `0` is the first row after the header; each column's name is its only name.
        """
        if grid.width == 0:
            raise ValueError("The file holds no cells, so there is no table to read.")
        grid, lines = grid.slice(dialect.skipRows), lines[dialect.skipRows :]
        if dialect.rowsPerRecord:
            grid, lines = self.join(grid=grid, lines=lines, fields=dialect.rowsPerRecord)
        header, grid = grid.head(dialect.headerRowCount), grid.slice(dialect.headerRowCount)
        if header.height < dialect.headerRowCount:
            raise ValueError(
                f"The file ends before its header: `skipRows` {dialect.skipRows} and `headerRowCount` "
                f"{dialect.headerRowCount} pass every row. Look at where the header starts, and declare it there."
            )
        if dialect.skipBlankRows:
            grid = grid.filter(~pl.all_horizontal(pl.all().is_null()))
        grid.columns = self.names(header=header, names=names, dialect=dialect)
        return grid.with_row_index(self.row_key.ROW)

    def names(self, *, header: pl.DataFrame, names: list[str] | None, dialect: DialectModel) -> list[str]:
        width = header.width
        if names is not None:
            if len(names) != width:
                raise ValueError(
                    f"`names` gives {len(names)} names for a table of {width} columns. Give one name per column, in "
                    "order."
                )
        elif dialect.headerRowCount > 1:
            raise ValueError(
                f"`headerRowCount` is {dialect.headerRowCount}, so each column's name is spread over "
                f"{dialect.headerRowCount} rows, and a cell over two columns may be one title or a heading over "
                f"subheadings. Declare the names with `names`, one per column ({width}), in order."
            )
        elif dialect.headerRowCount == 0:
            names = [f"column_{i}" for i in range(width)]
        else:
            names = [f"Unnamed: {i}" if n is None else n for i, n in enumerate(header.row(0))]
        return self.row_key.deconflict(columns=names)

    def join(self, *, grid: pl.DataFrame, lines: list[int], fields: list[int]) -> tuple[pl.DataFrame, list[int]]:
        """Each record's rows joined into one: the first `fields[0]` cells of its first row, then the first
        `fields[1]` of its next, and on.

        Raises
        ------
        ValueError
            Naming the line where a row holds values past its fields, or where the file ends inside a record, since
            every record after it would be misread.
        """
        span, width = len(fields), grid.width
        for i in range(grid.height):
            n = fields[i % span]
            if n < width and any(v is not None for v in grid.row(i)[n:]):
                raise ValueError(
                    f"`rowsPerRecord` {fields} declares {n} field{'s' if n != 1 else ''} on line {lines[i]}, row "
                    f"{i % span + 1} of a record, but it holds values past them. Either a record has lost a row "
                    "there, so each record after it would be misread, or the declaration does not fit the file. "
                    f"Look at the file around line {lines[i]}."
                )
        if grid.height % span:
            last = grid.height - grid.height % span
            raise ValueError(
                f"`rowsPerRecord` {fields} declares {span} rows to a record, but the record starting on line "
                f"{lines[last]} has only {grid.height - last} before the file ends. Look at the end of the file."
            )
        parts = []
        for j, n in enumerate(fields):
            part = grid.gather_every(span, offset=j).select(pl.nth(range(min(n, width))))
            for k in range(part.width, n):
                part = part.with_columns(pl.lit(None, dtype=pl.String).alias(f"column_{k}"))
            parts.append(part.rename(lambda c, j=j: f"{j}:{c}"))
        return pl.concat(parts, how="horizontal"), lines[::span]
