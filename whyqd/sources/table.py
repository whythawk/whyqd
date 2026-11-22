# SPDX-License-Identifier: BSD-3-Clause
from typing import ClassVar
import warnings

import polars as pl

from whyqd.dtypes import Place
from whyqd.models import DialectModel
from whyqd.sources.grid import GridParser, ReadFault
from whyqd.sources.row_key import RowKeyParser


class TableParser:
    """The grid as a table: the rows below the header, each column named once, each row keyed.

    In order: the rows before the header are skipped (`skipRows`); records over several rows are joined
    (`rowsPerRecord`); each cell is trimmed (`trim`), one left empty becoming empty; the header rows
    (`headerRowCount`) name the columns and leave the table; the row key is added. Nothing is inferred from the data:
    every setting is the dialect's, with its defaults. Frames beside the grid, such as each cell's type, take the same
    rows, so a column can be profiled as its cells read.
    """

    # Polars' string method for each end the dialect's `trim` names
    TRIM: ClassVar[dict[bool | str, str]] = {
        True: "strip_chars",
        "start": "strip_chars_start",
        "end": "strip_chars_end",
    }
    # What `trim` strips: every character Python's `str.isspace` takes, which Polars' own default does not (U+001C to
    # U+001F)
    WHITESPACE: ClassVar[str] = "".join(
        map(chr, (0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x85, 0xA0, 0x1680))
    ) + "".join(map(chr, (*range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000)))
    # A header's column with no name, and a named column the file leaves empty, each by its position from 0
    UNNAMED: ClassVar[str] = "Unnamed: {}"
    EMPTY: ClassVar[str] = "empty_{}"

    def __init__(self) -> None:
        self.grids = GridParser()
        self.row_key = RowKeyParser()

    def table(
        self,
        *,
        grid: pl.DataFrame,
        lines: list[int],
        dialect: DialectModel,
        source: str,
        place: Place,
        names: list[str] | None = None,
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
        source: str
            The file's name, for messages.
        names: list[str] | None, default None
            One name per column, in place of the header row's; required for a header over several rows. Names past the
            grid's last column are columns the file leaves empty, which the grid trims: each is added, empty, so every
            file of a format with fixed fields reads to one shape. Columns past the last name are named by position,
            with a warning, so no cell is lost and none moves.
        place: Place
            What `lines` counts, as the wrangler would look for it: a text file's `line`, a sheet's `row`.
        beside: list[pl.DataFrame] | None, default None
            Frames in the grid's shape, such as each cell's type.

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
            return pl.DataFrame({self.row_key.ROW: []}, schema={self.row_key.ROW: pl.UInt32}), [pl.DataFrame()] * len(
                beside
            )
        frames, lines = [f.slice(dialect.skipRows) for f in [grid, *beside]], lines[dialect.skipRows :]
        if dialect.rowsPerRecord:
            self.fit(grid=frames[0], lines=lines, fields=dialect.rowsPerRecord, source=source, place=place)
            frames = [self.join(grid=f, fields=dialect.rowsPerRecord) for f in frames]
            lines = lines[:: len(dialect.rowsPerRecord)]
        if side := self.TRIM.get(dialect.trim):
            stripped = [getattr(pl.col(c).str, side)(self.WHITESPACE) for c in frames[0].columns]
            frames[0] = frames[0].with_columns(
                pl.when(s == "").then(None).otherwise(s).alias(c)
                for s, c in zip(stripped, frames[0].columns, strict=True)
            )
        header = frames[0].head(dialect.headerRowCount)
        frames = [f.slice(dialect.headerRowCount) for f in frames]
        if header.height < dialect.headerRowCount:
            raise ReadFault(
                f"`{source}` ends before its header: `skipRows` {dialect.skipRows} and `headerRowCount` "
                f"{dialect.headerRowCount} pass every row. Declare where the header starts. [whyqd:header-past-end]",
                setting="skipRows",
            )
        if dialect.skipBlankRows:
            kept = ~frames[0].select(pl.all_horizontal(pl.all().is_null())).to_series()
            frames = [f.filter(kept) for f in frames]
        columns = self.names(header=header, names=names, dialect=dialect, source=source)
        empty = [pl.lit(None, dtype=pl.String).alias(self.EMPTY.format(i)) for i in range(header.width, len(columns))]
        frames = [f.with_columns(empty) for f in frames]
        for frame in frames:
            frame.columns = columns
        grid, *beside = frames
        return grid.with_row_index(self.row_key.ROW), beside

    def names(self, *, header: pl.DataFrame, names: list[str] | None, dialect: DialectModel, source: str) -> list[str]:
        width = header.width
        if names is not None:
            if len(names) < width:
                warnings.warn(
                    f"`names` gives {len(names)} names for the {width} columns of `{source}`, so the rest are named by "
                    "position. Check the list, and give one per column, in order. [whyqd:names-short]",
                    UserWarning,
                    stacklevel=2,
                )
                names = [*names, *(self.UNNAMED.format(i) for i in range(len(names), width))]
        elif dialect.headerRowCount > 1:
            raise ValueError(
                f"`{source}` has `headerRowCount` {dialect.headerRowCount}, so declare its names in `names`, one for "
                f"each of its {width} columns, in order. [whyqd:header-names]"
            )
        elif dialect.headerRowCount == 0:
            names = [self.grids.COLUMN.format(i) for i in range(width)]
        else:
            names = [self.UNNAMED.format(i) if n is None else n for i, n in enumerate(header.row(0))]
        return self.row_key.deconflict(columns=names)

    def fit(self, *, grid: pl.DataFrame, lines: list[int], fields: list[int], source: str, place: Place) -> None:
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
                raise ReadFault(
                    f"`rowsPerRecord` {fields} declares {n} field{'s' if n != 1 else ''} on {place} {lines[i]} of "
                    f"`{source}`, but it holds more. Check the file there: a record may have lost a row. "
                    "[whyqd:record-overflow]",
                    setting="rowsPerRecord",
                )
        if grid.height % span:
            last = grid.height - grid.height % span
            raise ReadFault(
                f"`rowsPerRecord` {fields} declares {span} rows to a record, but the last in `{source}`, from {place} "
                f"{lines[last]}, has {grid.height - last}. Check the file's end, or declare `rowsPerRecord` again. "
                "[whyqd:record-short]",
                setting="rowsPerRecord",
            )

    def join(self, *, grid: pl.DataFrame, fields: list[int]) -> pl.DataFrame:
        """Each record's rows joined into one: the first `fields[0]` cells of its first row, then the first
        `fields[1]` of its next, and on."""
        span, width = len(fields), grid.width
        parts = []
        for j, n in enumerate(fields):
            part = grid.gather_every(span, offset=j).select(pl.nth(range(min(n, width))))
            for k in range(part.width, n):
                part = part.with_columns(pl.lit(None, dtype=pl.String).alias(self.grids.COLUMN.format(k)))
            parts.append(part.rename(lambda c, j=j: f"{j}:{c}"))
        return pl.concat(parts, how="horizontal")
