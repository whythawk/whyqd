# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import warnings

import polars as pl

from whyqd.config.patterns import PythonPatterns
from whyqd.config.settings import settings
from whyqd.dtypes import FindingKind, MimeType, SettingSource
from whyqd.models import DialectModel, FindingModel, ReportModel, SettingModel
from whyqd.parsers.table import TableParser


class DiagnosisParser:
    """How a file was read, and what was found there, for the wrangler to review before going on.

    It interprets nothing. A fault is a file that could not be read as written, or was read with a loss; a fact is
    something the file holds, with no claim of what it means, which the crosswalk may act on. Each finding's `code` is
    the one a refusal or warning for the same thing carries, and every number counts as the wrangler would look for it.
    The file's read and its dialect are left as they were.
    """

    # The dialect's settings the table reads, whatever the file's format
    TABLE = ("skipRows", "headerRowCount", "skipBlankRows", "trim", "rowsPerRecord")
    # Those a read can settle from the file where they are not declared
    SETTLED = ("encoding", "encodingStep", "cells", "sheet")
    ADDRESSED_BY = {
        "csv-character": "delimiter",
        "encoding-replaced": "encoding",
        "header-past-end": "skipRows",
        "pdf-pages": "pages",
        "record-overflow": "rowsPerRecord",
        "record-short": "rowsPerRecord",
        "sheet-unknown": "sheet",
    }

    def __init__(self) -> None:
        self.tables = TableParser()
        self.patterns = PythonPatterns()

    def report(
        self,
        *,
        source: Path,
        mime: MimeType,
        reader,
        given: DialectModel,
        sheet: str | None = None,
        hidden: bool = False,
    ) -> ReportModel:
        """The report on a file, or one sheet of a workbook.

        Parameters
        ----------
        source: Path
        mime: MimeType
        reader
            The reader of its format.
        given: DialectModel
            The dialect as the wrangler declared it.
        sheet: str | None, default None
            The sheet to read, where the wrangler did not name it.
        hidden: bool, default False
            Whether the workbook's publisher hid the sheet.
        """
        dialect = given.model_copy(update={"sheet": sheet}) if sheet else given
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                grid, types, lines, read = reader.grid(source=source, mime=mime, dialect=dialect)
            except ValueError as e:
                return self.refused(source=source, mime=mime, reader=reader, error=e, sheet=dialect.sheet)
        findings = [f for w in caught if (f := self.finding(error=str(w.message))) is not None]
        for w in caught:
            if not self.patterns.MESSAGE.match(str(w.message)):
                warnings.warn_explicit(w.message, w.category, w.filename, w.lineno)
        try:
            self.tables.table(grid=grid, lines=lines, dialect=read, place=reader.PLACE)
        except ValueError as e:
            findings.append(self.finding(error=e))
        widths = self.widths(grid=grid)
        findings += self.facts(
            source=source,
            reader=reader,
            sheet=read.sheet,
            grid=grid,
            types=types,
            lines=lines,
            widths=widths,
            hidden=hidden,
        )
        return ReportModel(
            path=str(source),
            mime=mime,
            sheet=read.sheet,
            place=reader.PLACE,
            settings=self.settings(given=given, read=read, names=(*reader.DIALECT, *self.TABLE)),
            height=grid.height,
            width=grid.width,
            rowWidths=dict(sorted(widths.value_counts().iter_rows())),
            findings=findings,
            preview=self.preview(grid=grid, lines=lines, place=reader.PLACE),
        )

    def refused(
        self, *, source: Path, mime: MimeType, reader, error: ValueError, sheet: str | None = None
    ) -> ReportModel:
        """The report on a file that could not be read: what failed and where, since no grid exists."""
        return ReportModel(
            path=str(source), mime=mime, sheet=sheet, place=reader.PLACE, findings=[self.finding(error=error)]
        )

    def finding(self, *, error: ValueError | str) -> FindingModel | None:
        """A refusal or warning as a fault. A message with no code is whyqd's own, not the file's: `None` for a warning,
        and an error is raised again, so a fault in the code is not reported as one in the file.
        """
        message = self.patterns.MESSAGE.match(str(error))
        if message is None:
            if isinstance(error, str):
                return None
            raise error
        code = message.group(2)
        return FindingModel(
            code=code,
            kind=FindingKind.FAULT,
            message=message.group(1),
            rows=getattr(error, "rows", []),
            setting=getattr(error, "setting", None) or self.ADDRESSED_BY.get(code),
        )

    def settings(self, *, given: DialectModel, read: DialectModel, names: tuple[str, ...]) -> list[SettingModel]:
        """Each setting the read used, and where its value came from. A byte-order mark overrides a declared encoding,
        so an encoding is declared only where the step that settled it says so."""
        models = []
        for name in names:
            declared = name in given.model_fields_set
            if name == "encoding":
                declared = read.encodingStep == "declared"
            if declared:
                source = SettingSource.DECLARED
            elif name in self.SETTLED and getattr(read, name) is not None:
                source = SettingSource.FILE
            else:
                source = SettingSource.DEFAULT
            models.append(SettingModel(name=name, value=getattr(read, name), source=source))
        return models

    def widths(self, *, grid: pl.DataFrame) -> pl.Series:
        """How far each of the grid's rows reaches: its last filled cell, counted from 1, so `0` is a blank row."""
        if grid.width == 0:
            return pl.Series("width", [], dtype=pl.Int64)
        reach = [pl.when(pl.col(c).is_not_null()).then(i + 1).otherwise(0) for i, c in enumerate(grid.columns)]
        return grid.select(pl.max_horizontal(reach).cast(pl.Int64).alias("width")).to_series()

    def facts(
        self,
        *,
        source: Path,
        reader,
        sheet: str | None,
        grid: pl.DataFrame,
        types: pl.DataFrame,
        lines: list[int],
        widths: pl.Series,
        hidden: bool,
    ) -> list[FindingModel]:
        """What the file holds: its blank rows and columns from the grid, and what only its reader can show."""
        findings = []
        blank = [lines[i] for i in widths.eq(0).arg_true().to_list()]
        if blank:
            place = reader.PLACE.capitalize()
            findings.append(
                self.fact(
                    code="blank-rows",
                    message=f"{place}{'s' if len(blank) > 1 else ''} {self.listed(blank)} {self.are(blank)} blank.",
                    rows=blank[: settings.REPORT_PLACES],
                )
            )
        empty = [i for i, c in enumerate(grid.columns) if grid.height and grid[c].null_count() == grid.height]
        if empty:
            findings.append(
                self.fact(
                    code="blank-columns",
                    message=f"Column{'s' if len(empty) > 1 else ''} {self.listed(empty)} {self.are(empty)} blank, "
                    "counted from 0.",
                    columns=empty[: settings.REPORT_PLACES],
                )
            )
        if hidden:
            findings.append(
                self.fact(
                    code="hidden-sheet", message=f"Sheet `{sheet}` is hidden by its publisher, and read like any other."
                )
            )
        if hasattr(reader, "facts"):
            cells = reader.facts(source=source, sheet=sheet, types=types)
            if merged := cells["merged"]:
                findings.append(
                    self.fact(
                        code="merged-range",
                        message=f"Cells {self.listed(merged)} are merged; the first of each holds its value, and the "
                        "rest read as empty.",
                        cells=merged[: settings.REPORT_PLACES],
                    )
                )
            if errors := cells["errors"]:
                findings.append(
                    self.fact(
                        code="error-cells",
                        message=f"Cell{'s' if len(errors) > 1 else ''} {self.listed(errors)} {self.are(errors)} error "
                        "cells, each read as its code.",
                        cells=errors[: settings.REPORT_PLACES],
                    )
                )
        return findings

    def fact(self, *, code: str, message: str, **where) -> FindingModel:
        return FindingModel(code=code, kind=FindingKind.FACT, message=message, **where)

    def listed(self, items: list) -> str:
        """Items in words, up to the number a report names: `2 and 3`; `1, 2, and 3`; `1, 2, and 98 more`."""
        limit = settings.REPORT_PLACES
        shown = [str(i) for i in items[:limit]]
        if len(items) > limit:
            return f"{', '.join(shown)}, and {len(items) - limit} more"
        if len(shown) < 3:
            return " and ".join(shown)
        return f"{', '.join(shown[:-1])}, and {shown[-1]}"

    def are(self, items: list) -> str:
        return "are" if len(items) > 1 else "is"

    def preview(self, *, grid: pl.DataFrame, lines: list[int], place: str) -> str:
        """A short text of the grid as read, from its top and its end, each row numbered as the wrangler would look for
        it, so the rows above a header can be seen, which leave the table. A row's trailing empty cells are left out, a
        line break in a cell shows as `\\n`, and each cell and line is cut to the length a report shows."""
        head, tail = settings.REPORT_PREVIEW_HEAD, settings.REPORT_PREVIEW_TAIL
        shown = (
            list(range(grid.height))
            if grid.height <= head + tail
            else [*range(head), *range(grid.height - tail, grid.height)]
        )
        text = []
        for previous, i in zip([-1, *shown], shown, strict=False):
            if i - previous > 1:
                text.append(f"... {i - previous - 1} {place}s not shown ...")
            row = list(grid.row(i))
            while row and row[-1] is None:
                row.pop()
            cells = " | ".join(self.shortened(value=c, width=settings.REPORT_CELL_WIDTH) for c in row)
            text.append(self.shortened(value=f"{place} {lines[i]}: {cells}", width=settings.REPORT_LINE_WIDTH))
        return "\n".join(text)

    def shortened(self, *, value: str | None, width: int) -> str:
        value = (value or "").replace("\r", "\\r").replace("\n", "\\n")
        return value if len(value) <= width else f"{value[: width - 1]}…"
