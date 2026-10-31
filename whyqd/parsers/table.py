# SPDX-License-Identifier: BSD-3-Clause
import polars as pl

from whyqd.models import DialectModel
from whyqd.parsers.row_key import RowKeyParser


class TableParser:
    """The grid as a table: the rows below the header, each column named once, each row keyed.

    In order: the rows before the header are skipped (`skipRows`); records over several rows are joined
    (`rowsPerRecord`); each cell is trimmed (`trim`), one left empty becoming empty; the header rows
    (`headerRowCount`) name the columns and leave the table; the row key is added. Nothing is inferred from the data:
    every setting is the dialect's, with its defaults. Frames beside the grid, such as each cell's stored type, take
    the same rows, so a column can be profiled as its cells are stored.
    """

    TRIM = {True: str.strip, "start": str.lstrip, "end": str.rstrip}

    def __init__(self) -> None:
        self.row_key = RowKeyParser()

    def table(
        self,
        *,
        grid: pl.DataFrame,
        lines: list[int],
        dialect: DialectModel,
        names: list[str] | None = None,
        place: str = "line",
        beside: list[pl.DataFrame] | None = None,
    ) -> tuple[pl.DataFrame, list[pl.DataFrame]]:
        """The table a grid reads as under its dialect, its first column the row key, and the frames beside it.

        Parameters
        ----------
        grid: pl.DataFrame
            Each cell's text, null where empty, as a reader gives it.
        lines: list[int]
            Where in the file each grid row starts, counted from 1, for messages.
        dialect: DialectModel
        names: list[str] | None, default None
            One name per column, in place of the header row's; required for a header over several rows.
        place: str, default "line"
            What `lines` counts, as the wrangler would look for it: a text file's `line`, a sheet's `row`.
        beside: list[pl.DataFrame] | None, default None
            Frames in the grid's shape, such as each cell's stored type.

        Raises
        ------
        ValueError
            For a declaration the file does not fit, or one that is incomplete.

        Returns
        -------
        tuple[pl.DataFrame, list[pl.DataFrame]]
            The table: row `0` is the first row after the header; each column's name is its only name. A grid with no
            cells gives a table of no columns and no rows. Then each frame beside it, its rows and names the table's,
            without the row key, and its cells untrimmed.
        """
        beside = beside or []
        if grid.width == 0:
            return pl.DataFrame({self.row_key.ROW: []}, schema={self.row_key.ROW: pl.UInt32}), [pl.DataFrame()] * len(beside)
        frames, lines = [f.slice(dialect.skipRows) for f in [grid, *beside]], lines[dialect.skipRows :]
        if dialect.rowsPerRecord:
            self.fit(grid=frames[0], lines=lines, fields=dialect.rowsPerRecord, place=place)
            frames = [self.join(grid=f, fields=dialect.rowsPerRecord) for f in frames]
            lines = lines[:: len(dialect.rowsPerRecord)]
        if trim := self.TRIM.get(dialect.trim):
            frames[0] = frames[0].with_columns(
                pl.col(c).map_elements(lambda v: trim(v) or None, return_dtype=pl.String) for c in frames[0].columns
            )
        header = frames[0].head(dialect.headerRowCount)
        frames = [f.slice(dialect.headerRowCount) for f in frames]
        if header.height < dialect.headerRowCount:
            raise ValueError(
                f"The file ends before its header: `skipRows` {dialect.skipRows} and `headerRowCount` "
                f"{dialect.headerRowCount} pass every row. Declare where the header starts. [whyqd:header-past-end]"
            )
        if dialect.skipBlankRows:
            kept = ~frames[0].select(pl.all_horizontal(pl.all().is_null())).to_series()
            frames = [f.filter(kept) for f in frames]
        columns = self.names(header=header, names=names, dialect=dialect)
        for frame in frames:
            frame.columns = columns
        grid, *beside = frames
        return grid.with_row_index(self.row_key.ROW), beside

    def names(self, *, header: pl.DataFrame, names: list[str] | None, dialect: DialectModel) -> list[str]:
        width = header.width
        if names is not None:
            if len(names) != width:
                raise ValueError(
                    f"`names` gives {len(names)} names for a table of {width} columns. Give one per column, in order. "
                    "[whyqd:names-count]"
                )
        elif dialect.headerRowCount > 1:
            raise ValueError(
                f"`headerRowCount` is {dialect.headerRowCount}, so declare the names in `names`, one for each of its "
                f"{width} columns, in order. [whyqd:header-names]"
            )
        elif dialect.headerRowCount == 0:
            names = [f"column_{i}" for i in range(width)]
        else:
            names = [f"Unnamed: {i}" if n is None else n for i, n in enumerate(header.row(0))]
        return self.row_key.deconflict(columns=names)

    def fit(self, *, grid: pl.DataFrame, lines: list[int], fields: list[int], place: str = "line") -> None:
        """Whether a grid's rows fit their records.

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
                    f"`rowsPerRecord` {fields} declares {n} field{'s' if n != 1 else ''} on {place} {lines[i]}, but "
                    "it holds more. Check the file there: a record may have lost a row. [whyqd:record-overflow]"
                )
        if grid.height % span:
            last = grid.height - grid.height % span
            raise ValueError(
                f"`rowsPerRecord` {fields} declares {span} rows to a record, but the last, from {place} "
                f"{lines[last]}, has {grid.height - last}. [whyqd:record-short]"
            )

    def join(self, *, grid: pl.DataFrame, fields: list[int]) -> pl.DataFrame:
        """Each record's rows joined into one: the first `fields[0]` cells of its first row, then the first
        `fields[1]` of its next, and on."""
        span, width = len(fields), grid.width
        parts = []
        for j, n in enumerate(fields):
            part = grid.gather_every(span, offset=j).select(pl.nth(range(min(n, width))))
            for k in range(part.width, n):
                part = part.with_columns(pl.lit(None, dtype=pl.String).alias(f"column_{k}"))
            parts.append(part.rename(lambda c, j=j: f"{j}:{c}"))
        return pl.concat(parts, how="horizontal")
