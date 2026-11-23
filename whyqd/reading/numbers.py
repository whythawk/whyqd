# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar

import polars as pl

from whyqd.dtypes import CellType, ReadingWarning, RefusalReason
from whyqd.models import NumberFormatModel, PolicyModel, RulesModel
from whyqd.reading.reader import BaseReadingParser


class NumberParser(BaseReadingParser):
    """Read a `number` or `integer` field's cells, finding the number in each and what it read past."""

    DECIMAL_MARK: ClassVar[str] = "."
    GROUP_MARK: ClassVar[str] = ","
    GROUP_SIZE: ClassVar[int] = 3
    # CLDR's two grouping shapes, each the last group's size and the size of those before it: `1,234,567`, `12,34,567`
    GROUP_SHAPES: ClassVar[list[tuple[int, int]]] = [(3, 3), (3, 2)]
    # What a number reads past with a warning where its field declares none of the kind
    UNDECLARED_NEGATIVE: ClassVar[list[str]] = ["(x)", "x-"]
    UNDECLARED_PERCENT: ClassVar[str] = "%"
    # A Float64 holds any 15 significant digits, so only a longer number can lose any
    FLOAT_DIGITS: ClassVar[int] = 15
    DECIMAL_PRECISION: ClassVar[int] = 38
    PERCENT: ClassVar[int] = 2
    PER_MILLE: ClassVar[int] = 3

    def number_format(self, policy: PolicyModel) -> tuple[str, str | None, list[tuple[int, int]]] | None:
        """The decimal mark, group mark, and group sizes declared, each normalised as a cell is, or `None` where the
        field declares no format, each cell's marks then settling its own reading."""
        declared = policy.format if isinstance(policy.format, NumberFormatModel) else None
        if declared is None or not declared.model_fields_set:
            return None
        decimal = self.normalised(declared.decimalChar or self.DECIMAL_MARK)
        group = self.normalised(declared.groupChar) if declared.groupChar else None
        sizes = (self.GROUP_SIZE, self.GROUP_SIZE)
        if declared.pattern and group:
            written = self.normalised(declared.pattern).split(decimal)[0].split(group)
            sizes = (len(written[-1]), len(written[-2]) if len(written) > 2 else len(written[-1]))
        return decimal, group, [sizes]

    def read_number(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A number as `Float64`, or as exact decimals where `base` is `decimal` or a cell holds more digits than a
        `Float64` keeps, the column then reading as decimals with that cell warning."""
        read = self.parts(cells=cells, types=types, policy=policy)
        finite = read["text"].str.contains(self.patterns.NON_FINITE).fill_null(False)
        if policy.base == PolicyModel.EXACT:
            return self.outcome(*self.as_decimal(read, finite=finite))
        lost = self.float_losses(read)
        if lost.any():
            return self.outcome(*self.as_decimal(read.with_columns(lost), finite=finite))
        digits = read["text"].str.replace("INF", "inf").str.to_lowercase().zip_with(finite, read["digits"])
        read = read.with_columns(digits.alias("digits"))
        scale = (10.0 ** read["shift"].cast(pl.Float64)).alias(self.CELL)
        return self.outcome(read, read["digits"].cast(pl.Float64, strict=False) / scale)

    def read_integer(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A whole number, a fraction rounded half away from zero, as Excel's `ROUND` does, with a warning."""
        read = self.parts(cells=cells, types=types, policy=policy)
        whole = read["digits"].str.contains(self.patterns.WHOLE).fill_null(False) & (read["shift"] == 0)
        value = read["digits"].str.replace(self.patterns.FRACTION, "").cast(pl.Int64, strict=False)
        rounded = pl.repeat(False, cells.len(), eager=True)
        others = read.filter(~whole & pl.col("reason").is_null() & ~pl.col("blank")).select("digits", "shift").unique()
        if others.height:
            exact = {(text, shift): Decimal(text).scaleb(-shift) for text, shift in others.rows()}
            near = {key: number.to_integral_value(rounding=ROUND_HALF_UP) for key, number in exact.items()}
            keys = read.select("digits", "shift").rows()
            changed = pl.Series(self.CELL, [key in near and near[key] != exact[key] for key in keys], dtype=pl.Boolean)
            written = pl.Series(self.CELL, [str(near[key]) if key in near else None for key in keys], dtype=pl.String)
            value = value.zip_with(whole, written.cast(pl.Int64, strict=False))
            rounded = changed
        lost = value.is_null() & read["digits"].is_not_null() & read["reason"].is_null() & ~read["blank"]
        read = read.with_columns(
            rounded.alias(ReadingWarning.ROUNDED.value),
            pl.when(lost).then(pl.lit(RefusalReason.TOO_MANY_DIGITS.value)).otherwise("reason").alias("reason"),
        )
        return self.outcome(read, value)

    def parts(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """Find the number in each cell, leaving its reason, or its canonical digits, how many places a percent or per
        mille moves its point, and what it read past with a warning, each warning a column of its own.

        What has one sensible reading reads, with a warning, where the field declares nothing of its kind: a currency
        mark of Unicode's category `Sc`, `(x)` and `x-`, `%`, an exponent, and the marks `.` and `,`. Declaring one
        confirms it, and tightens it, so another of its kind refuses."""
        p, rules = self.patterns, policy.rules or RulesModel()
        length = cells.len()
        declared = self.number_format(policy)
        text, mixed = self.digits(self.steps(cells))
        warned = {}
        marks = [self.normalised(mark) for mark in [*rules.currency, *rules.marks]]
        if marks:
            text = text.str.replace_all(p.any_of(marks), "").str.strip_chars()
        if not rules.currency:
            warned[ReadingWarning.CURRENCY] = text.str.contains(p.CURRENCY)
            text = text.str.replace_all(p.CURRENCY, "").str.strip_chars()
        shift = pl.repeat(0, length, eager=True, dtype=pl.Int64)
        percent = (rules.percent or self.UNDECLARED_PERCENT, self.PERCENT, rules.percent is None)
        for mark, places, warns in (percent, (rules.perMille, self.PER_MILLE, False)):
            if mark:
                found = text.str.contains(self.normalised(mark), literal=True).fill_null(False)
                text = text.str.replace_all(self.normalised(mark), "", literal=True).str.strip_chars()
                shift = pl.repeat(places, length, eager=True, dtype=pl.Int64).zip_with(found, shift)
                if warns:
                    warned[ReadingWarning.PERCENT] = found
        negative = pl.repeat(False, length, eager=True)
        for form in rules.negative or self.UNDECLARED_NEGATIVE:
            prefix, suffix = (self.normalised(part).strip() for part in form.split(RulesModel.NUMBER_PLACE))
            around = p.around(prefix, suffix)
            found = text.str.contains(around).fill_null(False)
            negative = negative | found
            text = text.str.extract(around).zip_with(found, text)
        if not rules.negative:
            warned[ReadingWarning.SIGN] = negative
        minus = text.str.contains(p.LEADING_MINUS).fill_null(False)
        core = text.str.replace(p.LEADING_MINUS, "")
        decimal, group, shapes = declared or (self.DECIMAL_MARK, self.GROUP_MARK, self.GROUP_SHAPES)
        exponent = core.str.extract(p.exponent(decimal, group), 2)
        mantissa = core
        if rules.exponent is not False:
            found = core.str.extract(p.exponent(decimal, group), 1)
            mantissa = found.zip_with(found.is_not_null(), core)
            if rules.exponent is None:
                warned[ReadingWarning.EXPONENT] = exponent.is_not_null()
        if declared:
            fits = mantissa.str.contains(p.number(decimal, group, shapes))
            digits = mantissa.str.replace_all(group, "", literal=True) if group else mantissa
            digits = digits.str.replace(decimal, ".", literal=True)
            either = pl.repeat(False, length, eager=True)
        else:
            fits, digits, either, warned[ReadingWarning.MARKS] = self.undeclared_marks(mantissa)
        # A space between digits may group them or part two numbers, so it is undeclared unless it is the group mark
        spaced = mantissa.str.contains(p.SPACED).fill_null(False)
        if group and group.isspace():
            spaced = pl.repeat(False, length, eager=True)
        left = core.str.replace_all(p.beside_number(decimal, group), "")
        space = pl.repeat(" ", length, eager=True, dtype=pl.String)
        detail = mantissa.str.extract(p.LAST_MARK, 1).zip_with(either, space.zip_with(spaced & (left == ""), left))
        read = pl.DataFrame(
            {
                "cell": cells,
                "type": types,
                "blank": self.is_blank(cells),
                "form": cells.str.contains(p.NUMBER_FORM).fill_null(False),
                "mixed": mixed,
                "text": text,
                "core": core,
                "left": left,
                "either": either.fill_null(False),
                "spaced": spaced.fill_null(False),
                "runs": mantissa.str.extract_all(p.number_run(decimal, group)).list.len(),
                "exponent": exponent,
                "fits": fits.fill_null(False),
                "digits": digits,
                "shift": shift,
                "twice": negative & minus,
                "negative": negative | minus,
                **{code.value: flag.fill_null(False) for code, flag in warned.items()},
            }
        )
        return read.with_columns(self.number_reason(rules), self.canonical()).with_columns(left=detail)

    def undeclared_marks(self, mantissa: pl.Series) -> tuple[pl.Series, pl.Series, pl.Series, pl.Series]:
        """Read `.` and `,` wherever only one reading fits: of two marks the last is the decimal; a repeated mark
        groups; and a lone mark is a decimal unless it could be either, a group of three after one to three digits, as
        `1,234`, since every CLDR locale's last group has three digits. Groups take either of CLDR's two shapes.
        Returns whether each cell fits, its canonical digits, whether it could be either, and whether its marks warn."""
        p = self.patterns
        point, comma = self.DECIMAL_MARK, self.GROUP_MARK
        dots = mantissa.str.count_matches(point, literal=True).fill_null(0)
        commas = mantissa.str.count_matches(comma, literal=True).fill_null(0)
        last = mantissa.str.extract(p.LAST_MARK, 1)
        decimal_comma = (
            ((dots > 0) & (commas > 0) & (last == comma)) | ((dots > 1) & (commas == 0)) | ((commas == 1) & (dots == 0))
        ).fill_null(False)
        fits = mantissa.str.contains(p.number(comma, point, self.GROUP_SHAPES)).zip_with(
            decimal_comma, mantissa.str.contains(p.number(point, comma, self.GROUP_SHAPES))
        )
        as_comma = mantissa.str.replace_all(point, "", literal=True).str.replace(comma, point, literal=True)
        digits = as_comma.zip_with(decimal_comma, mantissa.str.replace_all(comma, "", literal=True))
        either = mantissa.str.contains(p.EITHER_MARK).fill_null(False)
        return fits, digits, either, (commas > 0) | (dots > 1)

    def number_reason(self, rules: RulesModel) -> pl.Expr:
        """Why a cell is refused, the first of these that holds. A stored cell is decided by its type alone."""
        p = self.patterns
        finite = pl.col("text").str.contains(p.NON_FINITE).fill_null(False)
        signed = pl.col("text").str.contains(p.BRACKETED) | pl.col("text").str.contains(p.TRAILING_MINUS)
        refusals = (
            (pl.col("type") == CellType.ERROR.value, RefusalReason.ERROR_CELL),
            (pl.col("type") == CellType.NUMBER.value, None),
            (pl.col("type") != CellType.STRING.value, RefusalReason.NOT_IN_FORMAT),
            (pl.col("blank"), None),
            (pl.col("form"), RefusalReason.NUMBER_FORM),
            (pl.col("mixed"), RefusalReason.MIXED_DIGITS),
            (finite & (not rules.nonFinite), RefusalReason.UNDECLARED_NON_FINITE),
            (finite, None),
            (pl.col("core") == "", RefusalReason.NO_NUMBER),
            (signed.fill_null(False) | pl.col("twice"), RefusalReason.UNDECLARED_SIGN),
            (pl.col("exponent").is_not_null() & (rules.exponent is False), RefusalReason.UNDECLARED_EXPONENT),
            (pl.col("exponent").is_null() & (pl.col("left") != ""), RefusalReason.UNDECLARED_CHARACTER),
            (pl.col("either") | pl.col("spaced"), RefusalReason.UNDECLARED_CHARACTER),
            (pl.col("runs") > 1, RefusalReason.TWO_NUMBERS),
            (~pl.col("fits"), RefusalReason.GROUPING),
        )
        reason = pl.lit(None, dtype=pl.String)
        for condition, refusal in reversed(refusals):
            refused = pl.lit(None, dtype=pl.String) if refusal is None else pl.lit(refusal.value)
            reason = pl.when(condition).then(refused).otherwise(reason)
        return reason.alias("reason")

    def canonical(self) -> pl.Expr:
        """Each number as canonical text, with its sign and exponent; a stored number is its own rendering."""
        written = pl.col("digits") + pl.when(pl.col("exponent").is_not_null()).then(
            pl.lit("e") + pl.col("exponent")
        ).otherwise(pl.lit(""))
        return (
            pl.when(pl.col("type") == CellType.NUMBER.value)
            .then(pl.col("cell"))
            .when(pl.col("negative"))
            .then(pl.lit("-") + written)
            .otherwise(written)
            .alias("digits")
        )

    def float_losses(self, read: pl.DataFrame) -> pl.Series:
        """Whether each number has more digits than a `Float64` keeps, compared exactly, and only where it might."""
        significant = read["digits"].str.replace_all(self.patterns.SIGN_OR_POINT, "").str.strip_chars_start("0")
        possible = (read["reason"].is_null() & (significant.str.len_chars() > self.FLOAT_DIGITS)).fill_null(False)
        lost = [
            text
            for text in read["digits"].filter(possible).unique().to_list()
            if Decimal(text) != Decimal(repr(float(text)))
        ]
        return (read["digits"].is_in(lost) & possible).alias(ReadingWarning.EXACT_DECIMAL.value)

    def as_decimal(self, read: pl.DataFrame, *, finite: pl.Series) -> tuple[pl.DataFrame, pl.Series]:
        """Exact values, in the scale the column's own cells need, so none rounds. A decimal has no `NaN` or `INF`, and
        a number too long for its precision is refused."""
        read = read.with_columns(finite.alias("finite")).with_columns(
            pl.when("finite")
            .then(pl.lit(RefusalReason.UNDECLARED_NON_FINITE.value))
            .otherwise("reason")
            .alias("reason")
        )
        kept = read.filter(pl.col("reason").is_null() & ~pl.col("blank")).select("digits", "shift").unique().rows()
        exact = {(text, shift): Decimal(text).scaleb(-shift) for text, shift in kept}
        scale = max((max(0, -value.as_tuple().exponent) for value in exact.values()), default=0)
        fits = {key: value for key, value in exact.items() if value.adjusted() + 1 + scale <= self.DECIMAL_PRECISION}
        written = [fits.get(key) for key in read.select("digits", "shift").rows()]
        value = pl.Series(self.CELL, written, dtype=pl.Decimal(self.DECIMAL_PRECISION, scale))
        too_long = [key[0] for key in exact if key not in fits]
        read = read.with_columns(
            pl.when(pl.col("digits").is_in(too_long))
            .then(pl.lit(RefusalReason.TOO_MANY_DIGITS.value))
            .otherwise("reason")
            .alias("reason")
        )
        return read, value

    def currencies(self, *, cells: pl.Series, policy: PolicyModel) -> dict[str, int]:
        """Each currency mark's count, since a number read loses which currency it was in: each declared mark, where a
        field declares more than one, or with none declared each mark read. `¬£` is counted apart from the `£` inside
        it."""
        declared = (policy.rules or RulesModel()).currency
        if len(declared) == 1:
            return {}
        marks = (
            self.patterns.any_of([self.normalised(mark) for mark in declared]) if declared else self.patterns.CURRENCY
        )
        found = self.steps(cells.alias(self.CELL)).str.extract_all(marks).explode()
        counts = dict(found.alias(self.CELL).drop_nulls().value_counts().iter_rows())
        if not declared:
            return counts
        return {mark: counts.get(self.normalised(mark), 0) for mark in declared}
