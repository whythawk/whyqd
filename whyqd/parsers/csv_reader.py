# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import csv

import polars as pl

from whyqd.config.patterns import PythonPatterns
from whyqd.dtypes import EncodingStep, MimeType
from whyqd.models import DialectModel
from whyqd.parsers.encoding import EncodingParser
from whyqd.parsers.grid import GridParser


class CsvParser:
    """A CSV file as the grid: each cell's text as written, in rows as read, by the dialect and nothing else.

    Every line end (`\\r\\n`, `\\n`, `\\r`) ends a row, and a quoted cell keeps its line breaks. The grid is as wide
    as its widest row, a shorter row's missing cells empty; trailing empty rows and columns are trimmed. An empty cell is
    null; any other text, whitespace included, is kept.

    Python's `csv` parses, not Polars' reader, which fixes a table's width from its first row and has no escape for a
    quote, so it cannot read every file as written.
    """

    PLACE = "line"

    def __init__(self) -> None:
        self.encoding = EncodingParser()
        self.grids = GridParser()
        self.patterns = PythonPatterns()

    def grid(
        self, *, source: Path, mime: MimeType, dialect: DialectModel
    ) -> tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel]:
        """The file's grid and its types, the line each of its rows starts on, and the dialect with the encoding
        recorded. Every cell is text, so typed `s`; each is kept as written, `trim` being the table's.

        Parameters
        ----------
        source: Path
        mime: MimeType
            Read only to share the interface every reader has.
        dialect: DialectModel
            How the file is written. Its encoding is read as declared where the wrangler declared it; otherwise the
            ladder settles it, and the dialect returned records which step did.

        Raises
        ------
        ValueError
            Where the file cannot be read as the dialect describes it, naming the line and the setting.

        Returns
        -------
        tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel]
        """
        declared = None
        if dialect.encodingStep == EncodingStep.DECLARED or (
            dialect.encodingStep is None and "encoding" in dialect.model_fields_set
        ):
            declared = dialect.encoding
        text, encoding, step = self.encoding.decode(data=source.read_bytes(), declared=declared, source=f"`{source.name}`")
        dialect = dialect.model_copy(update={"encoding": encoding, "encodingStep": step})
        rows, lines = self.rows(text=text, dialect=dialect, source=source)
        grid, types = self.to_grid(rows=rows)
        return grid, types, lines[: grid.height], dialect

    def rows(self, *, text: str, dialect: DialectModel, source: Path) -> tuple[list[list[str]], list[int]]:
        settings = {"delimiter": dialect.delimiter, "doublequote": dialect.doubleQuote, "strict": True}
        if dialect.quoteChar is None:
            settings["quoting"] = csv.QUOTE_NONE
        else:
            settings["quotechar"] = dialect.quoteChar
        if not dialect.doubleQuote:
            settings["escapechar"] = "\\"
        try:
            # lines matched from the text, since `io.StringIO` copies it at four bytes a character
            reader = csv.reader((m.group() for m in self.patterns.LINE.finditer(text)), **settings)
        except TypeError as e:
            raise ValueError(
                f"`{source.name}` cannot be read with `delimiter` {dialect.delimiter!r} and `quoteChar` "
                f"{dialect.quoteChar!r}: each must be one character ({e}). [whyqd:csv-character]"
            ) from e
        rows, lines, line = [], [], 1
        try:
            for row in reader:
                rows.append(row)
                lines.append(line)
                line = reader.line_num + 1
        except csv.Error as e:
            raise ValueError(
                f"`{source.name}` cannot be read from line {line}: {e}. If a quote there is text, declare `quoteChar` "
                "as null. [whyqd:csv-quote]"
            ) from e
        return rows, lines

    def to_grid(self, *, rows: list[list[str]]) -> tuple[pl.DataFrame, pl.DataFrame]:
        width = max((len(r) for r in rows), default=0)
        grid = pl.DataFrame(
            {
                f"column_{i}": [r[i] if i < len(r) and r[i] != "" else None for r in rows]
                for i in range(width)
            },
            schema={f"column_{i}": pl.String for i in range(width)},
        )
        return self.grids.trim(grid=grid)
