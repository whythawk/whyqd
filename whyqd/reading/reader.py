# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import unicodedata
from typing import ClassVar

import polars as pl

from whyqd.config.patterns import PolarsPatterns
from whyqd.dtypes import CellType, FindingKind, ReadingKind, ReadingWarning, RefusalReason
from whyqd.models import FindingModel, PolicyModel


class BaseReadingParser:
    """What every type's reader shares: a cell's fixed steps, its digits, a reading's five columns, and how refusals
    are reported. Each type's reader inherits it."""

    CELL: ClassVar[str] = "cell"
    NORMAL: ClassVar[str] = "NFKC"
    BIDI: ClassVar[str] = "‎‏؜"
    WARNINGS: ClassVar[list[str]] = [warning.value for warning in ReadingWarning]
    ADVICE: ClassVar[dict[str, tuple[str, str]]] = {
        "no-number": ("holds no number", "declare it in the schema's `missingValues`"),
        "two-numbers": ("holds two numbers", "split it with a crosswalk action"),
        "number-form-character": ("holds a character such as `¹` or `½`", "correct the file, or delete the row"),
        "mixed-digits": ("mixes digits of different scripts", "correct the file, or delete the row"),
        "undeclared-character": (
            "holds something undeclared",
            "declare it in `format`, `rules.currency`, or `rules.marks`, or if it means nothing in `missingValues`",
        ),
        "undeclared-sign": ("has an undeclared negative form", "declare it in `rules.negative`"),
        "undeclared-exponent": ("has an undeclared exponent", "set `rules.exponent`, if it is a number"),
        "undeclared-non-finite": ("is `NaN` or `INF`", "set `rules.nonFinite`, or use `missingValues`"),
        "grouping-mismatch": (
            "does not fit the declared marks",
            "correct `format`'s `decimalChar` and `groupChar`, or if it means nothing use `missingValues`",
        ),
        "too-many-digits": ("has more digits than its type holds", "use a `string` field"),
        "not-in-format": (
            "does not fit the format",
            "correct `format`, add to `rules.alternateFormats`, or if it means nothing use `missingValues`",
        ),
        "two-readings": (
            "could be read two ways",
            "declare `format`, or `rules.language` for a month's name, or keep the pattern the file uses",
        ),
        "no-zone": ("states no offset, beside cells that do", "declare `rules.zone`"),
        "impossible-date": ("names no such date or time", "correct `format`, or delete the row"),
        "error-cell": ("is a workbook's error cell", "use `missingValues`, or delete the row"),
    }

    def __init__(self) -> None:
        self.patterns = PolarsPatterns()

    def is_blank(self, cells: pl.Series) -> pl.Series:
        """Empty or only whitespace, by load's one definition."""
        return (cells.is_null() | cells.str.contains(self.patterns.WHITESPACE) | (cells == "")).fill_null(True)

    def normalised(self, text: str) -> str:
        """A declaration as a cell's fixed steps leave it, so a declared U+202F or `￥` finds its cell."""
        return unicodedata.normalize(self.NORMAL, text.translate({ord(mark): None for mark in self.BIDI}))

    def steps(self, cells: pl.Series) -> pl.Series:
        """A cell's fixed steps, whatever the field declares: bidirectional marks, NFKC, minus-like characters, ends."""
        p = self.patterns
        text = cells.str.replace_all(p.BIDI, "").str.normalize(self.NORMAL)
        return text.str.replace_all(p.MINUS, "-").str.strip_chars()

    def prepared(self, cells: pl.Series) -> tuple[pl.Series, pl.Series]:
        """A cell's text after its fixed steps, with other scripts' digits as `0` to `9`, and whether each mixed
        scripts."""
        return self.digits(self.steps(cells))

    def latin_digits(self, text: str) -> str | None:
        """A digit of any script as its value from Unicode's data, or `None` for a cell mixing scripts."""
        zeros = set()
        written = []
        for char in text:
            value = unicodedata.decimal(char, None)
            if value is not None:
                zeros.add(ord(char) - value)
            written.append(char if value is None else str(value))
        return "".join(written) if len(zeros) < 2 else None

    def digits(self, text: pl.Series) -> tuple[pl.Series, pl.Series]:
        """Other scripts' digits read as `0` to `9`, and whether each cell mixed scripts. Few cells hold any."""
        other = text.str.contains(self.patterns.OTHER_DIGIT).fill_null(False)
        if not other.any():
            return text, pl.repeat(False, text.len(), eager=True)
        latin = {cell: self.latin_digits(cell) for cell in text.filter(other).unique().to_list()}
        written = pl.Series(self.CELL, [latin.get(cell, cell) for cell in text.to_list()], dtype=pl.String)
        return written.fill_null(""), written.is_null() & text.is_not_null()

    def refusal(self, refusals: tuple[tuple[pl.Expr, RefusalReason | None], ...]) -> pl.Expr:
        """Why a cell is refused: the reason of the first condition that holds, `None` meaning it reads."""
        reason = pl.lit(None, dtype=pl.String)
        for condition, refused in reversed(refusals):
            written = pl.lit(None, dtype=pl.String) if refused is None else pl.lit(refused.value)
            reason = pl.when(condition).then(written).otherwise(reason)
        return reason.alias("reason")

    def outcome(self, read: pl.DataFrame, value: pl.Series) -> pl.DataFrame:
        """The five columns of a reading, from each cell's reason and value, and a column of its own for each warning a
        reader found, so a value's warnings are a list and a refusal or a blank has none."""
        refused = pl.col("reason").is_not_null()
        blank = pl.col("blank") & (pl.col("type") == CellType.STRING.value)
        undeclared = pl.col("reason") == RefusalReason.UNDECLARED_CHARACTER.value
        detail = pl.when(undeclared).then("detail") if "detail" in read.columns else pl.lit(None, dtype=pl.String)
        found = [pl.when(pl.col(code)).then(pl.lit(code)) for code in self.WARNINGS if code in read.columns]
        warnings = pl.concat_list([pl.lit(None, dtype=pl.String), *found]).list.drop_nulls()
        warnings = pl.when(refused | blank).then(pl.lit([], dtype=pl.List(pl.String))).otherwise(warnings)
        return read.with_columns(value.alias("value")).select(
            pl.when(refused)
            .then(pl.lit(ReadingKind.REFUSED.value))
            .when(blank)
            .then(pl.lit(ReadingKind.BLANK.value))
            .otherwise(pl.lit(ReadingKind.VALUE.value))
            .alias("kind"),
            pl.when(refused | blank).then(None).otherwise("value").alias("value"),
            pl.col("reason"),
            detail.alias("detail"),
            warnings.alias("warnings"),
        )

    def read_string(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A text field keeps a cell exactly as written. A blank is a blank, and nothing can be refused."""
        read = pl.DataFrame({"blank": self.is_blank(cells) & (types == CellType.STRING.value), "type": types})
        return self.outcome(read.with_columns(pl.lit(None, dtype=pl.String).alias("reason")), cells)

    def stored_types(self, types: pl.Series) -> dict[str, int]:
        """How many of a text field's cells a workbook stored as another type, which Excel may have converted on
        opening. Only what is stored can be shown, since the original is gone."""
        found = types.alias(self.CELL).drop_nulls().value_counts().iter_rows()
        return {tag: count for tag, count in found if tag not in (CellType.STRING.value, CellType.ERROR.value)}

    def findings(
        self, *, field: str, cells: pl.Series, readings: pl.DataFrame, rows: pl.Series | None = None
    ) -> list[FindingModel]:
        """A column's refusals grouped by reason and shape, digits written as `9`, so ten thousand exceptions become a
        handful of decisions: `#-9999.99`, 365 cells, first at row 12."""
        rows = pl.int_range(1, cells.len() + 1, eager=True) if rows is None else rows
        refused = pl.DataFrame(
            {
                "shape": cells.alias(self.CELL).str.replace_all(self.patterns.ANY_DIGIT, "9"),
                "reason": readings["reason"],
                "detail": readings["detail"],
                "row": rows.alias(self.CELL),
            }
        ).filter(pl.col("reason").is_not_null())
        grouped = refused.group_by("reason", "shape").agg(
            pl.len().alias("count"), pl.col("row").min().alias("first"), pl.col("detail").first()
        )
        ordered = grouped.sort("count", "reason", "shape", descending=[True, False, False])
        return [self.finding(field=field, **row) for row in ordered.iter_rows(named=True)]

    def finding(
        self, *, field: str, reason: str, shape: str, count: int, first: int, detail: str | None
    ) -> FindingModel:
        says, does = self.ADVICE[reason]
        if reason == RefusalReason.NOT_IN_FORMAT.value and not shape.strip("9."):
            does = f"{does}, or if these are Excel date serials set `rules.serial`"
        cells = "1 cell" if count == 1 else f"{count} cells"
        named = f" (`{detail}`)" if detail else ""
        return FindingModel(
            code=reason,
            kind=FindingKind.FAULT,
            message=f"Field `{field}`: {cells} shaped `{shape}`, first at row {first}, {says}{named}. Next, {does}.",
            rows=[first],
            field=field,
            shape=shape,
            count=count,
            setting=f"policy of `{field}`",
        )
