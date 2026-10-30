# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import csv
import io

import polars as pl

from whyqd.dtypes import EncodingStep
from whyqd.models import DialectModel
from whyqd.parsers.encoding import EncodingParser


class CsvParser:
    """A CSV file as the grid: each cell's text as written, in rows as read, by the dialect and nothing else.

    Every line end (`\\r\\n`, `\\n`, `\\r`) ends a row, and a quoted cell keeps its line breaks. The grid is as wide
    as its widest row, a shorter row's missing cells empty; trailing empty rows and columns are trimmed. An empty cell is
    null; any other text, whitespace included, is kept.

    Python's `csv` parses, not Polars' reader, which fixes a table's width from its first row and has no escape for a
    quote, so it cannot read every file as written.
    """

    def __init__(self) -> None:
        self.encoding = EncodingParser()

    def grid(self, *, source: Path, dialect: DialectModel) -> tuple[pl.DataFrame, list[int], DialectModel]:
        """The file's grid, the line each of its rows starts on, and the dialect with the encoding recorded.

        Parameters
        ----------
        source: Path
        dialect: DialectModel
            How the file is written. Its encoding is read as declared where the wrangler declared it; otherwise the
            ladder settles it, and the dialect returned records which step did.

        Raises
        ------
        ValueError
            Where the file cannot be read as the dialect describes it, naming the line and the setting.

        Returns
        -------
        tuple[pl.DataFrame, list[int], DialectModel]
        """
        declared = None
        if dialect.encodingStep == EncodingStep.DECLARED or (
            dialect.encodingStep is None and "encoding" in dialect.model_fields_set
        ):
            declared = dialect.encoding
        text, encoding, step = self.encoding.decode(data=source.read_bytes(), declared=declared, source=f"`{source.name}`")
        dialect = dialect.model_copy(update={"encoding": encoding, "encodingStep": step})
        rows, lines = self.rows(text=text, dialect=dialect, source=source)
        grid = self.to_grid(rows=rows)
        return grid, lines[: grid.height], dialect

    def rows(self, *, text: str, dialect: DialectModel, source: Path) -> tuple[list[list[str]], list[int]]:
        settings = {"delimiter": dialect.delimiter, "doublequote": dialect.doubleQuote, "strict": True}
        if dialect.quoteChar is None:
            settings["quoting"] = csv.QUOTE_NONE
        else:
            settings["quotechar"] = dialect.quoteChar
        if not dialect.doubleQuote:
            settings["escapechar"] = "\\"
        try:
            reader = csv.reader(io.StringIO(text, newline=""), **settings)
        except TypeError as e:
            raise ValueError(
                f"`{source.name}` cannot be read with `delimiter` {dialect.delimiter!r} and `quoteChar` "
                f"{dialect.quoteChar!r}: each must be one character ({e})."
            ) from e
        trim = {True: str.strip, "start": str.lstrip, "end": str.rstrip}.get(dialect.trim)
        rows, lines, line = [], [], 1
        try:
            for row in reader:
                rows.append([trim(c) for c in row] if trim else row)
                lines.append(line)
                line = reader.line_num + 1
        except csv.Error as e:
            raise ValueError(
                f"`{source.name}` cannot be read from line {line}: {e}. A quote that never closes is the usual cause, "
                "and the rest of the file is then one cell. Look at the line; if a quote there is part of the text, "
                "declare `quoteChar` as null so quotes are read as text, or declare the file's own quote character."
            ) from e
        return rows, lines

    def to_grid(self, *, rows: list[list[str]]) -> pl.DataFrame:
        while rows and not any(rows[-1]):
            rows.pop()
        width = max((len(r) for r in rows), default=0)
        while width and not any(len(r) >= width and r[width - 1] for r in rows):
            width -= 1
        return pl.DataFrame(
            {
                f"column_{i}": [r[i] if i < len(r) and r[i] != "" else None for r in rows]
                for i in range(width)
            },
            schema={f"column_{i}": pl.String for i in range(width)},
        )
