# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import unicodedata
from decimal import Decimal
from functools import partial
from typing import ClassVar

import polars as pl

from whyqd.config.patterns import PolarsPatterns
from whyqd.dtypes import CellType, FieldType, FindingKind, ReadingKind, RefusalReason
from whyqd.models import CellReadingModel, FindingModel, NumberFormatModel, PolicyModel, RulesModel


class ReadingParser:
    """Read a column's cells as the type its field declares: each a value, a blank, or a refusal with its reason.

    A cell reads by the declaration alone, never by another cell or the machine's locale, and a cell it cannot read is
    refused, never read another way. A workbook's stored cell is already a value, so a policy's text rules read only
    text cells. A cell without a type is text.

    Example:
      ```python
      from whyqd.parsers import ReadingParser

      policy = PolicyModel(format={"decimalChar": ",", "groupChar": "."}, rules={"currency": ["€"]})
      ReadingParser().read(cells=["1.234,50 €", "1,234.50", ""], dtype="number", policy=policy)
      ```
    """

    CELL: ClassVar[str] = "cell"
    NORMAL: ClassVar[str] = "NFKC"
    BIDI: ClassVar[str] = "‎‏؜"
    DECIMAL_MARK: ClassVar[str] = "."
    GROUP_SIZE: ClassVar[int] = 3
    # A Float64 holds any 15 significant digits, so only a longer number can lose any
    FLOAT_DIGITS: ClassVar[int] = 15
    DECIMAL_PRECISION: ClassVar[int] = 38
    PERCENT: ClassVar[int] = 2
    PER_MILLE: ClassVar[int] = 3
    BOOLEANS: ClassVar[dict[str, bool]] = {"true": True, "1": True, "false": False, "0": False}
    # A type's canonical patterns, which also read a stored cell's rendering, as `CellType.describe` states it
    CANONICAL: ClassVar[dict[str, list[str]]] = {
        "date": ["yyyy-MM-dd"],
        "time": ["HH:mm:ss", "HH:mm:ss.S"],
        "datetime": ["yyyy-MM-dd'T'HH:mm:ss", "yyyy-MM-dd'T'HH:mm:ss.S"],
    }
    STORED_DATETIME_MIDNIGHT: ClassVar[str] = "yyyy-MM-dd"
    # Each type's text for Polars to check, once the declared rules have read a cell: never Polars' own `%y` or `%b`,
    # which take a fixed century and the machine's month names
    ISO: ClassVar[dict[str, tuple[str, str, str]]] = {
        "date": ("{}-{}-{}", "yMd", "%Y-%m-%d"),
        "time": ("{}:{}:{}.{}", "HmsS", "%H:%M:%S%.f"),
        "datetime": ("{}-{}-{} {}:{}:{}.{}", "yMdHmsS", "%Y-%m-%d %H:%M:%S%.f"),
    }
    YEAR_WIDTH: ClassVar[int] = 4
    FIELD_WIDTH: ClassVar[int] = 2
    MICROSECONDS: ClassVar[dict[str, int]] = {"d": 86_400_000_000, "H": 3_600_000_000, "m": 60_000_000, "s": 1_000_000}
    BOUNDS: ClassVar[dict[str, int]] = {"H": 24, "m": 60, "s": 60}
    ADVICE: ClassVar[dict[str, tuple[str, str]]] = {
        "no-number": ("holds no number", "declare it in the schema's `missingValues`"),
        "two-numbers": ("holds two numbers", "split it with a crosswalk action"),
        "number-form-character": ("holds a character such as `¹` or `½`", "correct the file, or delete the row"),
        "mixed-digits": ("mixes digits of different scripts", "correct the file, or delete the row"),
        "undeclared-character": ("holds something undeclared", "declare it in `rules.currency` or `rules.marks`"),
        "undeclared-sign": ("has an undeclared negative form", "declare it in `rules.negative`"),
        "undeclared-exponent": ("has an undeclared exponent", "set `rules.exponent`, if it is a number"),
        "undeclared-non-finite": ("is `NaN` or `INF`", "set `rules.nonFinite`, or use `missingValues`"),
        "grouping-mismatch": ("does not fit the declared marks", "correct `format`'s `decimalChar` and `groupChar`"),
        "too-many-digits": ("has more digits than its type holds", "declare `base` as `decimal`"),
        "not-an-integer": ("holds a fraction", "change the field's type to `number`"),
        "not-in-format": ("does not fit the format", "correct `format`, or add to `rules.alternateFormats`"),
        "two-readings": ("fits two declared patterns differently", "keep the pattern the file uses"),
        "impossible-date": ("names no such date or time", "correct `format`, or delete the row"),
        "error-cell": ("is a workbook's error cell", "use `missingValues`, or delete the row"),
    }

    def __init__(self) -> None:
        self.patterns = PolarsPatterns()
        self.readers = {
            FieldType.NUMBER.value: self.read_number,
            FieldType.INTEGER.value: self.read_integer,
            FieldType.BOOLEAN.value: self.read_boolean,
            FieldType.STRING.value: self.read_string,
            FieldType.DATE.value: partial(self.read_temporal, dtype=FieldType.DATE.value),
            FieldType.TIME.value: partial(self.read_temporal, dtype=FieldType.TIME.value),
            FieldType.DATETIME.value: partial(self.read_temporal, dtype=FieldType.DATETIME.value),
            FieldType.DURATION.value: self.read_duration,
        }

    def read(
        self,
        *,
        cells: list[str | None],
        dtype: str,
        policy: PolicyModel | None = None,
        cell_types: list[str | None] | None = None,
    ) -> list[CellReadingModel]:
        """Each cell's reading as a model. A column's worth is quicker read with `column`."""
        types = None if cell_types is None else pl.Series(self.CELL, cell_types, dtype=pl.String)
        read = self.column(cells=pl.Series(self.CELL, cells, dtype=pl.String), dtype=dtype, policy=policy, types=types)
        return [CellReadingModel(**row) for row in read.iter_rows(named=True)]

    def column(
        self, *, cells: pl.Series, dtype: str, policy: PolicyModel | None = None, types: pl.Series | None = None
    ) -> pl.DataFrame:
        """A column's readings, one row to a cell, in `kind`, `value`, `reason`, and `detail`.

        Parameters:
          cells: Each cell's text as stored, null where empty.
          dtype: The field's type.
          policy: The field's declaration; with none, the type's canonical form.
          types: Each cell's `CellType` tag, for a file that stores them.

        Raises:
          AttributeError: For a type with no reader.
        """
        if dtype not in self.readers:
            raise AttributeError(f"`{dtype}` has no reader.")
        # A Series method runs as `col(series.name)`, so a source's column name must not reach it
        cells = cells.alias(self.CELL)
        types = pl.repeat(CellType.STRING.value, cells.len(), eager=True) if types is None else types
        types = types.alias(self.CELL).fill_null(CellType.STRING.value)
        return self.readers[dtype](cells=cells, types=types, policy=policy or PolicyModel())

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

    def number_format(self, policy: PolicyModel) -> tuple[str, str | None, tuple[int, int]]:
        """The decimal mark, group mark, and group sizes declared, each normalised as a cell is."""
        declared = policy.format if isinstance(policy.format, NumberFormatModel) else NumberFormatModel()
        decimal = self.normalised(declared.decimalChar or self.DECIMAL_MARK)
        group = self.normalised(declared.groupChar) if declared.groupChar else None
        sizes = (self.GROUP_SIZE, self.GROUP_SIZE)
        if declared.pattern and group:
            written = self.normalised(declared.pattern).split(decimal)[0].split(group)
            sizes = (len(written[-1]), len(written[-2]) if len(written) > 2 else len(written[-1]))
        return decimal, group, sizes

    def read_number(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        read = self.parts(cells=cells, types=types, policy=policy)
        finite = read["text"].str.contains(self.patterns.NON_FINITE).fill_null(False)
        if policy.base == PolicyModel.EXACT:
            return self.outcome(*self.as_decimal(read, finite=finite))
        digits = read["text"].str.replace("INF", "inf").str.to_lowercase().zip_with(finite, read["digits"])
        read = read.with_columns(digits.alias("digits"))
        scale = (10.0 ** read["shift"].cast(pl.Float64)).alias(self.CELL)
        return self.outcome(self.float_losses(read), read["digits"].cast(pl.Float64, strict=False) / scale)

    def read_integer(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        read = self.parts(cells=cells, types=types, policy=policy)
        written = read["digits"].to_list()
        if read["exponent"].is_not_null().any():
            written = [format(Decimal(t), "f") if t and "e" in t else t for t in written]
        digits = pl.Series(self.CELL, written, dtype=pl.String)
        fraction = digits.str.contains(self.patterns.NON_ZERO_FRACTION).fill_null(False)
        value = digits.str.replace(self.patterns.FRACTION, "").cast(pl.Int64, strict=False)
        read = read.with_columns(
            fraction.alias("fraction"),
            (value.is_null() & digits.is_not_null()).alias("lost"),
        ).with_columns(
            pl.when(pl.col("reason").is_not_null() | pl.col("blank"))
            .then(pl.col("reason"))
            .when("fraction")
            .then(pl.lit(RefusalReason.NOT_AN_INTEGER.value))
            .when("lost")
            .then(pl.lit(RefusalReason.TOO_MANY_DIGITS.value))
            .otherwise(pl.col("reason"))
            .alias("reason")
        )
        return self.outcome(read, value)

    def parts(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """Find the number in each cell, leaving its reason, or its canonical digits and how many places a percent or
        per mille moves its point."""
        p, rules = self.patterns, policy.rules or RulesModel()
        decimal, group, sizes = self.number_format(policy)
        text, mixed = self.digits(self.steps(cells))
        marks = [self.normalised(mark) for mark in [*rules.currency, *rules.marks]]
        if marks:
            text = text.str.replace_all(p.any_of(marks), "").str.strip_chars()
        shift = pl.repeat(0, cells.len(), eager=True, dtype=pl.Int64)
        for mark, places in ((rules.percent, self.PERCENT), (rules.perMille, self.PER_MILLE)):
            if mark:
                found = text.str.contains(self.normalised(mark), literal=True).fill_null(False)
                text = text.str.replace_all(self.normalised(mark), "", literal=True).str.strip_chars()
                shift = pl.repeat(places, cells.len(), eager=True, dtype=pl.Int64).zip_with(found, shift)
        negative = pl.repeat(False, cells.len(), eager=True)
        for form in rules.negative:
            prefix, suffix = (self.normalised(part).strip() for part in form.split(RulesModel.NUMBER_PLACE))
            around = p.around(prefix, suffix)
            found = text.str.contains(around).fill_null(False)
            negative = negative | found
            text = text.str.extract(around).zip_with(found, text)
        minus = text.str.contains(p.LEADING_MINUS).fill_null(False)
        core = text.str.replace(p.LEADING_MINUS, "")
        exponent = core.str.extract(p.exponent(decimal, group), 2)
        mantissa = core
        if rules.exponent:
            found = core.str.extract(p.exponent(decimal, group), 1)
            mantissa = found.zip_with(found.is_not_null(), core)
        digits = mantissa.str.replace_all(group, "", literal=True) if group else mantissa
        read = pl.DataFrame(
            {
                "cell": cells,
                "type": types,
                "blank": self.is_blank(cells),
                "form": cells.str.contains(p.NUMBER_FORM).fill_null(False),
                "mixed": mixed,
                "text": text,
                "core": core,
                "left": core.str.replace_all(p.beside_number(decimal, group), ""),
                "runs": mantissa.str.extract_all(p.number_run(decimal, group)).list.len(),
                "exponent": exponent,
                "fits": mantissa.str.contains(p.number(decimal, group, sizes)).fill_null(False),
                "digits": digits.str.replace(decimal, ".", literal=True),
                "shift": shift,
                "twice": negative & minus,
                "negative": negative | minus,
            }
        )
        return read.with_columns(self.number_reason(rules), self.canonical())

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
            (pl.col("exponent").is_not_null() & (not rules.exponent), RefusalReason.UNDECLARED_EXPONENT),
            (pl.col("exponent").is_null() & (pl.col("left") != ""), RefusalReason.UNDECLARED_CHARACTER),
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

    def float_losses(self, read: pl.DataFrame) -> pl.DataFrame:
        """Refuse a number with more digits than a `Float64` keeps, compared exactly, and only where it might."""
        significant = read["digits"].str.replace_all(self.patterns.SIGN_OR_POINT, "").str.strip_chars_start("0")
        possible = (read["reason"].is_null() & (significant.str.len_chars() > self.FLOAT_DIGITS)).fill_null(False)
        if not possible.any():
            return read
        lost = [
            text
            for text in read["digits"].filter(possible).unique().to_list()
            if Decimal(text) != Decimal(repr(float(text)))
        ]
        return read.with_columns(
            pl.when(pl.col("digits").is_in(lost) & pl.col("reason").is_null())
            .then(pl.lit(RefusalReason.TOO_MANY_DIGITS.value))
            .otherwise(pl.col("reason"))
            .alias("reason")
        )

    def as_decimal(self, read: pl.DataFrame, *, finite: pl.Series) -> tuple[pl.DataFrame, pl.Series]:
        """Exact values, in the scale the column's own cells need, so none rounds. A decimal has no `NaN` or `INF`, and
        a number too long for its precision is refused."""
        read = read.with_columns(finite.alias("finite")).with_columns(
            pl.when("finite").then(pl.lit(RefusalReason.UNDECLARED_NON_FINITE.value)).otherwise("reason").alias("reason")
        )
        kept = read.filter(pl.col("reason").is_null() & ~pl.col("blank")).select("digits", "shift").unique().rows()
        exact = {(text, shift): Decimal(text).scaleb(-shift) for text, shift in kept}
        scale = max((max(0, -value.as_tuple().exponent) for value in exact.values()), default=0)
        fits = {
            key: value
            for key, value in exact.items()
            if value.adjusted() + 1 + scale <= self.DECIMAL_PRECISION
        }
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

    def outcome(self, read: pl.DataFrame, value: pl.Series) -> pl.DataFrame:
        """The four columns of a reading, from each cell's reason and value."""
        refused = pl.col("reason").is_not_null()
        blank = pl.col("blank") & (pl.col("type") == CellType.STRING.value)
        undeclared = pl.col("reason") == RefusalReason.UNDECLARED_CHARACTER.value
        detail = pl.when(undeclared).then("left") if "left" in read.columns else pl.lit(None, dtype=pl.String)
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
        )

    def read_boolean(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A declared pair exactly as written, or with none the canonical form in any case. A stored boolean is already
        a value."""
        rules = policy.rules or RulesModel()
        terms = {}
        for pair in [policy.format] * isinstance(policy.format, str) + rules.alternateFormats:
            yes, no = (self.normalised(term) for term in pair.split(PolicyModel.PAIR))
            terms |= {yes: True, no: False}
        text = self.steps(cells)
        lower = text.str.to_lowercase()
        keys, table = (text, terms) if terms else (lower, self.BOOLEANS)
        stored = types == CellType.BOOLEAN.value
        written = pl.Series(self.CELL, [table.get(key) for key in keys.to_list()], dtype=pl.Boolean)
        value = lower.is_in(["true"]).zip_with(stored, written)
        read = pl.DataFrame({"blank": self.is_blank(cells), "type": types, "known": value.is_not_null()})
        return self.outcome(read.with_columns(self.boolean_reason()), value)

    def boolean_reason(self) -> pl.Expr:
        """Why a boolean cell is refused."""
        return (
            pl.when(pl.col("type") == CellType.ERROR.value)
            .then(pl.lit(RefusalReason.ERROR_CELL.value))
            .when(pl.col("type") == CellType.BOOLEAN.value)
            .then(pl.lit(None, dtype=pl.String))
            .when(pl.col("type") != CellType.STRING.value)
            .then(pl.lit(RefusalReason.NOT_IN_FORMAT.value))
            .when(pl.col("blank") | pl.col("known"))
            .then(pl.lit(None, dtype=pl.String))
            .otherwise(pl.lit(RefusalReason.NOT_IN_FORMAT.value))
            .alias("reason")
        )

    def read_string(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A text field keeps a cell exactly as written. A blank is a blank, and nothing can be refused."""
        read = pl.DataFrame({"blank": self.is_blank(cells) & (types == CellType.STRING.value), "type": types})
        return self.outcome(read.with_columns(pl.lit(None, dtype=pl.String).alias("reason")), cells)

    def pattern_regex(self, pattern: str, rules: RulesModel, *, quantities: bool = False) -> tuple[str, list[str]]:
        """A declared pattern as a regular expression capturing each field, and those fields in order. On a duration the
        first field is a quantity of any length: `H:mm` reads `100:30`."""
        p, regex, fields = self.patterns, [], []
        names = {"MMM": rules.monthAbbreviations, "MMMM": rules.monthNames}
        for is_field, text in PolicyModel.parts(self.normalised(pattern)):
            if not is_field:
                regex.append(p.literal(text))
                continue
            if text in names:
                captured = p.any_of([self.normalised(name) for name in names[text]])
            elif quantities and not fields:
                captured = "[0-9]+"
            elif text == "S":
                captured = "[0-9]+"
            else:
                low, high = PolicyModel.WIDTHS[text]
                captured = f"[0-9]{{{low},{high}}}"
            regex.append(f"({captured})")
            fields.append(text)
        return "^" + "".join(regex) + "$", fields

    def month_numbers(self, names: list[str]) -> dict[str, str]:
        return {self.normalised(name): f"{index + 1:02d}" for index, name in enumerate(names)}

    def pattern_value(
        self, *, text: pl.Series, pattern: str, rules: RulesModel, dtype: str
    ) -> tuple[pl.Series, pl.Series]:
        """Whether each cell fits `pattern`, and its value, null for a cell that fits and names no such date."""
        regex, fields = self.pattern_regex(pattern, rules)
        found = text.str.extract_groups(regex).struct.unnest()
        parts = {}
        for index, field in enumerate(fields):
            column = found[str(index + 1)].alias(self.CELL)
            if field in ("MMM", "MMMM"):
                names = rules.monthAbbreviations if field == "MMM" else rules.monthNames
                column = column.replace_strict(self.month_numbers(names), default=None, return_dtype=pl.String)
            if field == "yy":
                column = (rules.yearStart + ((column.cast(pl.Int64) - rules.yearStart) % 100)).cast(pl.String)
            parts[field[0]] = column
        written, letters, form = self.ISO[dtype]
        zero = pl.repeat("0", text.len(), eager=True, dtype=pl.String)
        frame = pl.DataFrame({letter: parts.get(letter, zero) for letter in letters})
        widths = {"y": self.YEAR_WIDTH, "S": 1}
        columns = [pl.col(letter).str.zfill(widths.get(letter, self.FIELD_WIDTH)) for letter in letters]
        joined = frame.select(pl.format(written, *columns).alias(self.CELL))[self.CELL]
        if dtype == FieldType.DATE.value:
            value = joined.str.to_date(form, strict=False)
        elif dtype == FieldType.TIME.value:
            value = joined.str.to_time(form, strict=False)
        else:
            value = joined.str.to_datetime(form, strict=False, time_unit="us")
        return found["1"].is_not_null().alias(self.CELL), value.alias(self.CELL)

    def read_temporal(self, *, dtype: str, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A date, time, or datetime by its declared patterns, or with none its canonical form. A stored date cell is
        already a value, so it reads by its rendering, or by the pattern `rules.cellFormats` gives that rendering."""
        rules = policy.rules or RulesModel()
        declared = [policy.format] * isinstance(policy.format, str) + rules.alternateFormats
        text, mixed = self.digits(self.steps(cells))
        read = self.patterns_read(text=text, patterns=declared or self.CANONICAL[dtype], rules=rules, dtype=dtype)
        is_stored = types == CellType.DATE.value
        if is_stored.any():
            stored = rules.cellFormats.get(CellType.DATE)
            patterns = [stored] if stored else self.stored_patterns(dtype)
            rendered = self.patterns_read(text=text, patterns=patterns, rules=rules, dtype=dtype)
            read = tuple(one.zip_with(is_stored, other) for one, other in zip(rendered, read))
        fits, twice, value = read
        frame = self.temporal_frame(cells=cells, types=types, mixed=mixed, fits=fits, twice=twice, named=value.is_not_null())
        return self.outcome(frame, value)

    def temporal_frame(
        self, *, cells: pl.Series, types: pl.Series, mixed: pl.Series, fits: pl.Series, twice: pl.Series, named: pl.Series
    ) -> pl.DataFrame:
        frame = pl.DataFrame(
            {
                "blank": self.is_blank(cells),
                "type": types,
                "form": cells.str.contains(self.patterns.NUMBER_FORM).fill_null(False),
                "mixed": mixed,
                "fits": fits,
                "twice": twice,
                "named": named,
            }
        )
        return frame.with_columns(self.temporal_reason())

    def stored_patterns(self, dtype: str) -> list[str]:
        """What a stored date cell's rendering may be, for a type: a datetime at midnight renders as a date."""
        canonical = self.CANONICAL[dtype]
        return [*canonical, self.STORED_DATETIME_MIDNIGHT] if dtype == FieldType.DATETIME.value else canonical

    def patterns_read(
        self, *, text: pl.Series, patterns: list[str], rules: RulesModel, dtype: str
    ) -> tuple[pl.Series, pl.Series, pl.Series]:
        """Whether each cell fits any pattern, whether two read it differently, and its value by the first that fits."""
        fits, twice, value = None, None, None
        for pattern in patterns:
            written = self.pattern_dtype(pattern, dtype)
            fit, read = self.pattern_value(text=text, pattern=pattern, rules=rules, dtype=written)
            read = read if written == dtype else read.cast(pl.Datetime("us")).alias(self.CELL)
            if fits is None:
                fits, twice, value = fit, pl.repeat(False, text.len(), eager=True).alias(self.CELL), read
                continue
            twice = twice | (fits & fit & (value != read).fill_null(False))
            value = value.zip_with(fits, read)
            fits = fits | fit
        return fits, twice, value

    def pattern_dtype(self, pattern: str, dtype: str) -> str:
        """The type a pattern alone can state: a datetime's stored midnight states only a date."""
        return FieldType.DATE.value if pattern == self.STORED_DATETIME_MIDNIGHT and dtype != FieldType.DATE.value else dtype

    def temporal_reason(self) -> pl.Expr:
        """Why a date, time, or duration cell is refused, the first of these that holds."""
        refusals = (
            (pl.col("type") == CellType.ERROR.value, RefusalReason.ERROR_CELL),
            (~pl.col("type").is_in([CellType.STRING.value, CellType.DATE.value]), RefusalReason.NOT_IN_FORMAT),
            (pl.col("blank"), None),
            (pl.col("form"), RefusalReason.NUMBER_FORM),
            (pl.col("mixed"), RefusalReason.MIXED_DIGITS),
            (~pl.col("fits"), RefusalReason.NOT_IN_FORMAT),
            (pl.col("twice"), RefusalReason.TWO_READINGS),
            (~pl.col("named"), RefusalReason.IMPOSSIBLE_DATE),
        )
        reason = pl.lit(None, dtype=pl.String)
        for condition, refusal in reversed(refusals):
            refused = pl.lit(None, dtype=pl.String) if refusal is None else pl.lit(refusal.value)
            reason = pl.when(condition).then(refused).otherwise(reason)
        return reason.alias("reason")

    def read_duration(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """ISO 8601 days, hours, minutes, and seconds, or a declared pattern's quantities: `H:mm` reads `1:30`, and
        `m' min'` reads `25 min`. Years and months have no fixed length, so neither can be read. A stored duration reads
        by its rendering."""
        rules = policy.rules or RulesModel()
        declared = [policy.format] * isinstance(policy.format, str) + rules.alternateFormats
        text, mixed = self.digits(self.steps(cells))
        fits, within, value = self.iso_durations(text)
        if declared:
            written = None
            for pattern in declared:
                read = self.pattern_duration(text=text, pattern=pattern, rules=rules)
                written = read if written is None else (
                    written[0] | read[0],
                    written[1].zip_with(written[0], read[1]),
                    written[2].zip_with(written[0], read[2]),
                )
            is_stored = types == CellType.DATE.value
            fits, within, value = (one.zip_with(is_stored, other) for one, other in zip((fits, within, value), written))
        twice = pl.repeat(False, cells.len(), eager=True)
        frame = self.temporal_frame(cells=cells, types=types, mixed=mixed, fits=fits, twice=twice, named=within)
        return self.outcome(frame, value.cast(pl.Duration("us")))

    def iso_durations(self, text: pl.Series) -> tuple[pl.Series, pl.Series, pl.Series]:
        """Whether each cell is an ISO 8601 duration, that it is always in range, and its microseconds."""
        found = text.str.extract_groups(self.patterns.DURATION).struct.unnest()
        amounts = {
            letter: found[str(index + 2)].cast(pl.Float64).fill_null(0.0).alias(self.CELL)
            for index, letter in enumerate("dHms")
        }
        any_part = pl.DataFrame({str(i): found[str(i)] for i in range(2, 6)}).select(
            pl.any_horizontal(pl.all().is_not_null()).alias(self.CELL)
        )[self.CELL]
        total = sum(amounts[letter] * float(self.MICROSECONDS[letter]) for letter in "dHms")
        negative = found["1"].is_not_null().alias(self.CELL)
        signed = (total * -1.0).zip_with(negative, total).round().cast(pl.Int64).alias(self.CELL)
        return any_part, pl.repeat(True, text.len(), eager=True).alias(self.CELL), signed

    def pattern_duration(self, *, text: pl.Series, pattern: str, rules: RulesModel) -> tuple[pl.Series, pl.Series, pl.Series]:
        """Whether each cell fits a duration's pattern, that every field after the first is in range, and its
        microseconds. A fraction `S` is of a second."""
        regex, fields = self.pattern_regex(pattern, rules, quantities=True)
        found = text.str.extract_groups(regex).struct.unnest()
        total = pl.repeat(0.0, text.len(), eager=True, dtype=pl.Float64).alias(self.CELL)
        within = pl.repeat(True, text.len(), eager=True).alias(self.CELL)
        for index, field in enumerate(fields):
            column = found[str(index + 1)].alias(self.CELL)
            if field == "S":
                total = total + ("0." + column).cast(pl.Float64).fill_null(0.0) * float(self.MICROSECONDS["s"])
                continue
            amount = column.cast(pl.Float64).fill_null(0.0)
            total = total + amount * float(self.MICROSECONDS[field[0]])
            if index and field[0] in self.BOUNDS:
                within = within & (amount < self.BOUNDS[field[0]])
        return found["1"].is_not_null().alias(self.CELL), within, total.round().cast(pl.Int64).alias(self.CELL)

    def stored_types(self, types: pl.Series) -> dict[str, int]:
        """How many of a text field's cells a workbook stored as another type, which Excel may have converted on
        opening. Only what is stored can be shown, since the original is gone."""
        found = types.alias(self.CELL).drop_nulls().value_counts().iter_rows()
        return {tag: count for tag, count in found if tag not in (CellType.STRING.value, CellType.ERROR.value)}

    def currencies(self, *, cells: pl.Series, policy: PolicyModel) -> dict[str, int]:
        """Each declared currency mark's count, where a field declares more than one, since a number read loses which
        currency it was in. `¬£` is counted apart from the `£` inside it."""
        declared = (policy.rules or RulesModel()).currency
        if len(declared) < 2:
            return {}
        text = self.steps(cells.alias(self.CELL))
        found = text.str.extract_all(self.patterns.any_of([self.normalised(mark) for mark in declared])).explode()
        counts = dict(found.alias(self.CELL).drop_nulls().value_counts().iter_rows())
        return {mark: counts.get(self.normalised(mark), 0) for mark in declared}

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

    def finding(self, *, field: str, reason: str, shape: str, count: int, first: int, detail: str | None) -> FindingModel:
        says, does = self.ADVICE[reason]
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
