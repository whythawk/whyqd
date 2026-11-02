# SPDX-License-Identifier: BSD-3-Clause
from itertools import islice
from pathlib import Path
import csv
import warnings

import polars as pl

from whyqd.config.patterns import PythonPatterns
from whyqd.config.settings import settings
from whyqd.dtypes import EncodingStep, MimeType
from whyqd.models import DialectModel, FindingModel, ProposalModel
from whyqd.parsers.encoding import EncodingParser
from whyqd.parsers.grid import GridParser, ReadFault


class CsvParser:
    """A CSV file as the grid: each cell's text as written, in rows as read, by the dialect and nothing else.

    Every line end (`\\r\\n`, `\\n`, `\\r`) ends a row, and a quoted cell keeps its line breaks. The grid is as wide
    as its widest row, a shorter row's missing cells empty; trailing empty rows and columns are trimmed. An empty cell is
    null; any other text, whitespace included, is kept.

    Python's `csv` parses, not Polars' reader, which fixes a table's width from its first row and has no escape for a
    quote, so it cannot read every file as written.
    """

    PLACE = "line"
    DIALECT = ("encoding", "encodingStep", "delimiter", "quoteChar", "doubleQuote")
    # What a proposed delimiter is chosen among
    DELIMITERS = (",", ";", "\t", "|")
    # What a `csv-quote` fault's setting takes, to read past it
    PAST_QUOTE = {"quoteChar": None, "doubleQuote": False}

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
        text, encoding, step = self.decoded(source=source, dialect=dialect)
        dialect = dialect.model_copy(update={"encoding": encoding, "encodingStep": step})
        rows, lines = self.rows(text=text, dialect=dialect, source=source)
        grid, types = self.to_grid(rows=rows)
        return grid, types, lines[: grid.height], dialect

    def decoded(self, *, source: Path, dialect: DialectModel) -> tuple[str, str, EncodingStep]:
        declared = None
        if dialect.encodingStep == EncodingStep.DECLARED or (
            dialect.encodingStep is None and "encoding" in dialect.model_fields_set
        ):
            declared = dialect.encoding
        return self.encoding.decode(data=source.read_bytes(), declared=declared, source=f"`{source.name}`")

    def proposals(
        self, *, source: Path, mime: MimeType, dialect: DialectModel, faults: list[FindingModel]
    ) -> list[ProposalModel]:
        """The settings that would read past this file's faults, each with its evidence: what lets the file read at all,
        or else a delimiter that fits its lines where the one read by does not.

        A quote setting is proposed only once the whole file has read with it. A delimiter is proposed only where one
        alone gives every line the same width, over one cell, and the one read by does not, so a sound file is never
        second-guessed. Where the evidence is mixed, nothing is proposed.
        """
        found = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for fault in faults:
                if fault.code != "csv-quote" or fault.setting not in self.PAST_QUOTE:
                    continue
                value = self.PAST_QUOTE[fault.setting]
                try:
                    self.grid(source=source, mime=mime, dialect=dialect.model_copy(update={fault.setting: value}))
                except ValueError:
                    continue
                found.append(
                    ProposalModel(
                        setting=fault.setting,
                        value=value,
                        evidence=f"Line {fault.rows[0]} cannot be read without it, and the whole file reads with it.",
                    )
                )
            if not found and not any(f.code == "csv-quote" for f in faults):
                text = self.decoded(source=source, dialect=dialect)[0]
                found += self.delimiter(text=text, dialect=dialect)
        return found

    def delimiter(self, *, text: str, dialect: DialectModel) -> list[ProposalModel]:
        lines = [m.group() for m in islice(self.patterns.LINE.finditer(text), settings.REPORT_SAMPLE_LINES)]
        lines = [line for line in lines if line.strip("\r\n")]

        def width(delimiter: str) -> int | None:
            try:
                widths = {len(row) for row in csv.reader(lines, delimiter=delimiter) if row}
            except csv.Error:
                return None
            return widths.pop() if len(widths) == 1 else None

        if width(dialect.delimiter) is not None:
            return []
        fits = {d: w for d in self.DELIMITERS if d != dialect.delimiter and (w := width(d)) is not None and w > 1}
        if len(fits) != 1:
            return []
        delimiter, cells = fits.popitem()
        return [
            ProposalModel(
                setting="delimiter",
                value=delimiter,
                evidence=f"It gives each of the first {len(lines)} lines {cells} cells; "
                f"`{dialect.delimiter}` gives them differing widths.",
            )
        ]

    def encoding_proposal(
        self, *, source: Path, dialect: DialectModel, faults: list[FindingModel]
    ) -> ProposalModel | None:
        """The encoding this file more likely is, where its read could only fall back on `windows-1252`, or replaced
        bytes it could not decode. A file that decoded as itself is never second-guessed.

        Raises
        ------
        ImportError
            Without the `diagnose` extra, only where a proposal is called for.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _, read, step = self.decoded(source=source, dialect=dialect)
        if step != EncodingStep.WINDOWS_1252 and not any(f.code == "encoding-replaced" for f in faults):
            return None
        detected = self.encoding.detect(data=source.read_bytes())
        if detected is None or detected[0] == read:
            return None
        return ProposalModel(setting="encoding", value=detected[0], evidence=detected[1])

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
            found = next(islice(self.patterns.LINE.finditer(text), line - 1, None), None)
            escaped = found is not None and f"\\{dialect.quoteChar}" in found.group()
            setting = "doubleQuote" if escaped else "quoteChar"
            advice = (
                "If a backslash escapes a quote there, declare `doubleQuote` as false."
                if escaped
                else "If a quote there is text, declare `quoteChar` as null."
            )
            raise ReadFault(
                f"`{source.name}` cannot be read from line {line}: {e}. {advice} [whyqd:csv-quote]",
                rows=[line],
                setting=setting,
            ) from e
        return rows, lines

    def to_grid(self, *, rows: list[list[str]]) -> tuple[pl.DataFrame, pl.DataFrame]:
        width = max((len(r) for r in rows), default=0)
        grid = pl.DataFrame(
            {f"column_{i}": [r[i] if i < len(r) and r[i] != "" else None for r in rows] for i in range(width)},
            schema={f"column_{i}": pl.String for i in range(width)},
        )
        return self.grids.trim(grid=grid)
