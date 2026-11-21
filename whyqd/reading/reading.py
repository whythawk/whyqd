# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import unicodedata
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import partial
from typing import ClassVar

import polars as pl

from whyqd.config.names import NameTables
from whyqd.config.patterns import PolarsPatterns
from whyqd.dtypes import CellType, FieldType, FindingKind, ReadingKind, ReadingWarning, RefusalReason, SerialDate
from whyqd.models import CellReadingModel, FindingModel, NumberFormatModel, PolicyModel, RulesModel


class ReadingParser:
    """Read a column's cells as the type its field declares: each a value, a blank, or a refusal with its reason.

    A cell reads by the declaration alone, never by another cell or the machine's locale, and a cell it cannot read is
    refused, never read another way. A workbook's stored cell is already a value, so a policy's text rules read only
    text cells. A cell without a type is text.

    Example:
      ```python
      from whyqd.reading.reading import ReadingParser

      policy = PolicyModel(format={"decimalChar": ",", "groupChar": "."}, rules={"currency": ["€"]})
      ReadingParser().read(cells=["1.234,50 €", "1,234.50", ""], dtype="number", policy=policy)
      ```
    """

    CELL: ClassVar[str] = "cell"
    NORMAL: ClassVar[str] = "NFKC"
    BIDI: ClassVar[str] = "‎‏؜"
    DECIMAL_MARK: ClassVar[str] = "."
    GROUP_MARK: ClassVar[str] = ","
    GROUP_SIZE: ClassVar[int] = 3
    # CLDR's two grouping shapes, each the last group's size and the size of those before it: `1,234,567`, `12,34,567`
    GROUP_SHAPES: ClassVar[list[tuple[int, int]]] = [(3, 3), (3, 2)]
    # What a number reads past with a warning where its field declares none of the kind
    UNDECLARED_NEGATIVE: ClassVar[list[str]] = ["(x)", "x-"]
    UNDECLARED_PERCENT: ClassVar[str] = "%"
    WARNINGS: ClassVar[list[str]] = [warning.value for warning in ReadingWarning]
    # A Float64 holds any 15 significant digits, so only a longer number can lose any
    FLOAT_DIGITS: ClassVar[int] = 15
    DECIMAL_PRECISION: ClassVar[int] = 38
    PERCENT: ClassVar[int] = 2
    PER_MILLE: ClassVar[int] = 3
    BOOLEANS: ClassVar[dict[str, bool]] = {"true": True, "1": True, "false": False, "0": False}
    # A type's canonical patterns, which also read a stored cell's rendering, as `CellType.describe` states it
    CANONICAL: ClassVar[dict[str, list[str]]] = {
        "date": ["yyyy-MM-dd"],
        "time": ["HH:mm:ss", "HH:mm:ss.S", "HH:mm"],
        "datetime": [
            "yyyy-MM-dd'T'HH:mm:ss",
            "yyyy-MM-dd'T'HH:mm:ss.S",
            "yyyy-MM-dd'T'HH:mm",
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd HH:mm:ss.S",
            "yyyy-MM-dd HH:mm",
        ],
        "month": ["yyyy-MM"],
        "quarter": ["yyyy-MM"],
        "year": ["yyyy"],
    }
    PERIODS: ClassVar[frozenset[str]] = frozenset(
        {FieldType.MONTH.value, FieldType.QUARTER.value, FieldType.YEAR.value}
    )
    # A period names no day, and a year no month, so its date is first read at the period's start
    DEFAULTS: ClassVar[dict[str, str]] = {"M": "1", "d": "1"}
    QUARTER_MONTHS: ClassVar[int] = 3
    HALF_DAY: ClassVar[int] = 12
    NO_HOUR: ClassVar[str] = "99"
    EPOCH_1900: ClassVar[datetime] = datetime(1899, 12, 30)
    EPOCH_1900_EARLY: ClassVar[datetime] = datetime(1899, 12, 31)
    EPOCH_1904: ClassVar[datetime] = datetime(1904, 1, 1)
    EPOCH_UNIX: ClassVar[datetime] = datetime(1970, 1, 1)
    # A time of day is no date, and a year's own number is a year, so neither reads a bare number as a serial undeclared
    NO_SERIAL: ClassVar[frozenset[str]] = frozenset({FieldType.TIME.value, FieldType.YEAR.value})
    PHANTOM_LEAP_DAY: ClassVar[int] = 60
    LAST_SERIAL_1900: ClassVar[int] = 2_958_465
    LAST_SERIAL_1904: ClassVar[int] = 2_957_003
    MILLISECONDS_A_DAY: ClassVar[int] = 86_400_000
    EARLY_YEAR: ClassVar[int] = 1000
    UTC: ClassVar[str] = "UTC"
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
        self.readers = {
            FieldType.NUMBER.value: self.read_number,
            FieldType.INTEGER.value: self.read_integer,
            FieldType.BOOLEAN.value: self.read_boolean,
            FieldType.STRING.value: self.read_string,
            FieldType.DATE.value: partial(self.read_temporal, dtype=FieldType.DATE.value),
            FieldType.TIME.value: partial(self.read_temporal, dtype=FieldType.TIME.value),
            FieldType.DATETIME.value: partial(self.read_temporal, dtype=FieldType.DATETIME.value),
            FieldType.MONTH.value: partial(self.read_temporal, dtype=FieldType.MONTH.value),
            FieldType.QUARTER.value: partial(self.read_temporal, dtype=FieldType.QUARTER.value),
            FieldType.YEAR.value: partial(self.read_temporal, dtype=FieldType.YEAR.value),
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
        if dtype == FieldType.USDATE.value:
            dtype, policy = FieldType.DATE.value, policy or PolicyModel(**PolicyModel.USDATE)
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

    def outcome(self, read: pl.DataFrame, value: pl.Series) -> pl.DataFrame:
        """The five columns of a reading, from each cell's reason and value, and a column of its own for each warning a
        reader found, so a value's warnings are a list and a refusal or a blank has none."""
        refused = pl.col("reason").is_not_null()
        blank = pl.col("blank") & (pl.col("type") == CellType.STRING.value)
        undeclared = pl.col("reason") == RefusalReason.UNDECLARED_CHARACTER.value
        detail = pl.when(undeclared).then("left") if "left" in read.columns else pl.lit(None, dtype=pl.String)
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

    def pattern_regex(
        self, pattern: str, rules: RulesModel, *, quantities: bool = False, tail: bool = False
    ) -> tuple[str, list[str]]:
        """A declared pattern as a regular expression capturing each field, and those fields in order. A number's width
        says nothing of its meaning, so `dd` reads `1`, unless digits run together, as in `yyyyMMdd`. On a duration the
        first field is a quantity of any length: `H:mm` reads `100:30`. With `tail`, a date's cell may also hold a time."""
        p, regex, fields = self.patterns, [], []
        written = PolicyModel.parts(self.normalised(pattern))
        for index, (is_field, text) in enumerate(written):
            if not is_field:
                regex.append(p.literal(text))
                continue
            beside = [written[i][0] for i in (index - 1, index + 1) if 0 <= i < len(written)]
            if text in ("MMM", "MMMM"):
                captured = p.names(list(self.month_names(rules)))
            elif text[0] == "E":
                captured = p.names(self.weekday_names(rules))
            elif text == "a":
                captured = p.names(list(self.day_period_names(rules)))
            elif (quantities and not fields) or text == "S":
                captured = "[0-9]+"
            elif any(beside):
                captured = f"[0-9]{{{4 if text[0] == 'y' and len(text) != 2 else len(text)}}}"
            else:
                low, high = PolicyModel.WIDTHS[text]
                captured = f"[0-9]{{{low},{high}}}"
            regex.append(f"({captured})")
            fields.append(text)
        return "^" + "".join(regex) + (p.TIME_TAIL if tail else "") + "$", fields

    def name_key(self, name: str) -> str:
        """A name as a cell's may be compared with it: without case or a closing `.`."""
        return self.normalised(name).lower().rstrip(".")

    def month_names(self, rules: RulesModel) -> dict[str, str]:
        """Every spelling a field reads for a month, with the month's number."""
        table = NameTables.language(rules.language) if rules.language else None
        names = {}
        for index, entries in enumerate(table["months"] if table else []):
            names |= {self.name_key(entry): f"{index + 1:02d}" for entry in entries}
        for index, entry in enumerate(rules.monthNames):
            names |= {
                self.name_key(name): f"{index + 1:02d}" for name in ([entry] if isinstance(entry, str) else entry)
            }
        return names

    def weekday_names(self, rules: RulesModel) -> list[str]:
        return [self.name_key(name) for name in NameTables.language(rules.language)["weekdays"]]

    def period_key(self, name: str) -> str:
        """A day period as a cell's may be compared with it: without case, dots, or spaces, so `p. m.` is `pm`."""
        return "".join(char for char in self.normalised(name).lower() if char != "." and not char.isspace())

    def day_period_names(self, rules: RulesModel) -> dict[str, bool]:
        """Every spelling a field reads for a day period, with whether it is the afternoon: `AM` and `PM` always."""
        table = NameTables.language(rules.language) if rules.language else None
        spelled = {"am": False, "a.m.": False, "pm": True, "p.m.": True}
        for afternoon, key in ((False, "morning"), (True, "afternoon")):
            spelled |= {self.normalised(name).lower(): afternoon for name in (table[key] if table else [])}
        for afternoon, entry in zip((False, True), rules.dayPeriods):
            spelled |= {
                self.normalised(name).lower(): afternoon for name in ([entry] if isinstance(entry, str) else entry)
            }
        return spelled | {self.period_key(name): afternoon for name, afternoon in spelled.items()}

    def pattern_value(
        self, *, text: pl.Series, pattern: str, rules: RulesModel, dtype: str, tail: bool = False
    ) -> tuple[pl.Series, pl.Series]:
        """Whether each cell fits `pattern`, and its value, null for a cell that fits and names no such date."""
        regex, fields = self.pattern_regex(pattern, rules, tail=tail)
        found = text.str.extract_groups(regex).struct.unnest()
        parts = {}
        for index, field in enumerate(fields):
            column = found[str(index + 1)].alias(self.CELL)
            if field in ("MMM", "MMMM"):
                keys = column.str.to_lowercase().str.replace(self.patterns.TRAILING_DOT, "")
                column = keys.replace_strict(self.month_names(rules), default=None, return_dtype=pl.String)
            if field == "yy":
                column = (rules.yearStart + ((column.cast(pl.Int64) - rules.yearStart) % 100)).cast(pl.String)
            parts[field[0]] = column
        if "Q" in parts:
            parts["M"] = (parts["Q"].cast(pl.Int64) * self.QUARTER_MONTHS - (self.QUARTER_MONTHS - 1)).cast(pl.String)
        if "h" in parts:
            parts["H"] = self.twenty_four_hour(hours=parts["h"], periods=parts["a"], rules=rules)
        written, letters, form = self.ISO[dtype]
        frame = pl.DataFrame(
            {
                letter: parts.get(letter, pl.repeat(self.DEFAULTS.get(letter, "0"), text.len(), eager=True))
                for letter in letters
            }
        )
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

    def twenty_four_hour(self, *, hours: pl.Series, periods: pl.Series, rules: RulesModel) -> pl.Series:
        """A 12-hour clock's hour and day period as a 24-hour hour; one outside 1 to 12 reads as no such time."""
        hour = hours.cast(pl.Int64)
        keys = periods.str.to_lowercase().str.replace_all(self.patterns.DOT_OR_SPACE, "")
        afternoon = keys.replace_strict(self.day_period_names(rules), default=False, return_dtype=pl.Boolean)
        written = (hour % self.HALF_DAY + afternoon.cast(pl.Int64) * self.HALF_DAY).cast(pl.String)
        valid = ((hour >= 1) & (hour <= self.HALF_DAY)).fill_null(False)
        return written.zip_with(valid, pl.repeat(self.NO_HOUR, hours.len(), eager=True))

    def period_end(self, value: pl.Series, dtype: str) -> pl.Series:
        """A month, quarter, or year as the date it ends on, as its `FieldType` states."""
        if dtype == FieldType.MONTH.value:
            return value.dt.month_end()
        every = {FieldType.QUARTER.value: "1q", FieldType.YEAR.value: "1y"}[dtype]
        return value.dt.truncate(every).dt.offset_by(every).dt.offset_by("-1d")

    def read_temporal(self, *, dtype: str, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A date, time, datetime, or period by its declared patterns, or with none its canonical form. A stored date
        cell is already a value, so it reads by its rendering, or by the pattern `rules.cellFormats` gives that
        rendering. A period reads as the date it ends on. A datetime's own offset is read wherever a cell has one, and
        `rules.zone` states the zone of a clock that has none. What is read with something worth checking warns."""
        rules = policy.rules or RulesModel()
        declared = [policy.format] * isinstance(policy.format, str) + rules.alternateFormats
        declared = [PolicyModel.standard_pattern(pattern, dtype) for pattern in declared]
        text, mixed = self.digits(self.steps(cells))
        offsets = None
        if dtype == FieldType.DATETIME.value:
            found = text.str.extract_groups(self.patterns.OFFSET).struct.unnest()
            stated = found["2"].alias(self.CELL)
            text = found["1"].alias(self.CELL).zip_with(stated.is_not_null(), text)
            offsets = stated if stated.is_not_null().any() or rules.zone else None
        period = dtype in self.PERIODS
        parsed = FieldType.DATE.value if period else dtype
        read = self.patterns_read(text=text, patterns=declared or self.CANONICAL[dtype], rules=rules, dtype=parsed)
        warned = {}
        if dtype == FieldType.DATE.value and not declared:
            read, warned = self.undeclared_dates(text=text, read=read, rules=rules)
        is_stored = types == CellType.DATE.value
        if is_stored.any():
            stored = rules.cellFormats.get(CellType.DATE)
            patterns = [PolicyModel.standard_pattern(stored, dtype)] if stored else self.stored_patterns(dtype)
            rendered = self.patterns_read(text=text, patterns=patterns, rules=rules, dtype=parsed)
            read = tuple(one.zip_with(is_stored, other) for one, other in zip(rendered, read))
            warned = {code: flag & ~is_stored for code, flag in warned.items()}
        fits, twice, value = read
        serial_time = pl.repeat(False, cells.len(), eager=True)
        # A pattern of digits alone, as `yyyyMMdd`, already says what a bare number is
        digits_only = any(all(is_field for is_field, _ in PolicyModel.parts(pattern)) for pattern in declared)
        if rules.serial or not (dtype in self.NO_SERIAL or digits_only):
            system = SerialDate(rules.serial or SerialDate.EXCEL_1900)
            fits, value, serial_time, types, serial = self.serials(
                text=text, types=types, fits=fits, value=value, system=system
            )
            if not rules.serial:
                warned[ReadingWarning.SERIAL] = serial
        no_zone = pl.repeat(False, cells.len(), eager=True)
        if dtype in (FieldType.DATE.value, FieldType.DATETIME.value) or period:
            warned[ReadingWarning.YEAR_BELOW_1000] = (value.dt.year() < self.EARLY_YEAR).fill_null(False)
        if dtype == FieldType.DATE.value:
            at_end = text.str.extract(self.patterns.TIME_AT_END, 1)
            warned[ReadingWarning.TIME_DROPPED] = (
                at_end.str.contains(self.patterns.NOT_ZERO).fill_null(False) | serial_time
            )
        if period:
            value = self.period_end(value, dtype).alias(self.CELL)
        if offsets is not None:
            value, warned[ReadingWarning.REPEATED_HOUR], no_zone = self.zoned(
                value=value, offsets=offsets, zone=rules.zone
            )
        frame = self.temporal_frame(
            cells=cells,
            types=types,
            mixed=mixed,
            fits=fits,
            twice=twice,
            named=value.is_not_null() | no_zone,
            no_zone=no_zone,
            warned=warned,
        )
        return self.outcome(frame, value)

    def undeclared_dates(
        self, *, text: pl.Series, read: tuple[pl.Series, pl.Series, pl.Series], rules: RulesModel
    ) -> tuple[tuple[pl.Series, pl.Series, pl.Series], dict[ReadingWarning, pl.Series]]:
        """Read, where a date field declares no pattern, each cell with one reading the canonical form did not: day and
        month as numbers in either order with one separator used twice, `yyyyMMdd`, or a day, a month's name, and a
        year. Two orders reading different days, or a name meaning different months, fit twice. A name reads by
        `rules.language` or `rules.monthNames` where declared, and otherwise wherever it means one month in every
        language whyqd holds."""
        p = self.patterns
        fits, twice, value = read
        order = text.str.extract_groups(p.DATE_ORDER).struct.unnest()
        same = (order["2"] == order["4"]).fill_null(False)
        day_first = self.iso_date(year=order["5"], month=order["3"], day=order["1"])
        month_first = self.iso_date(year=order["5"], month=order["1"], day=order["3"])
        two_days = (day_first != month_first).fill_null(False)
        ordered = day_first.fill_null(month_first)
        run = text.str.extract_groups(p.DATE_RUN).struct.unnest()
        joined = self.iso_date(year=run["1"], month=run["2"], day=run["3"])
        spaced = text.str.replace_all(p.COMMA, " ", literal=True)
        day_name = spaced.str.extract_groups(p.DAY_NAME).struct.unnest()
        name_day = spaced.str.extract_groups(p.NAME_DAY).struct.unnest()
        first = day_name["1"].is_not_null()
        name = day_name["2"].zip_with(first, name_day["1"]).str.to_lowercase().str.replace(p.TRAILING_DOT, "")
        day = day_name["1"].zip_with(first, name_day["2"])
        year = day_name["3"].zip_with(first, name_day["3"])
        declared = rules.language or rules.monthNames
        meanings = (
            {key: {int(month)} for key, month in self.month_names(rules).items()} if declared else NameTables.months()
        )
        present = name.drop_nulls().unique().to_list()
        months = {key: len(meanings.get(self.name_key(key), ())) for key in present}
        month = {key: str(next(iter(meanings[self.name_key(key)]))) for key, count in months.items() if count == 1}
        count = name.replace_strict(months, default=0, return_dtype=pl.Int64).fill_null(0)
        dated = self.iso_date(
            year=year, month=name.replace_strict(month, default=None, return_dtype=pl.String), day=day
        )
        shapes = (
            (order["1"].is_not_null() & same, two_days, ordered, ReadingWarning.DATE_ORDER),
            (run["1"].is_not_null(), None, joined, ReadingWarning.DATE_ORDER),
            (count > 0, count > 1, dated, ReadingWarning.MONTH_NAME),
        )
        nothing = pl.repeat(False, text.len(), eager=True)
        warned = {ReadingWarning.DATE_ORDER: nothing, ReadingWarning.MONTH_NAME: nothing}
        for matched, ambiguous, read_as, code in shapes:
            new = matched.fill_null(False) & ~fits
            if ambiguous is not None:
                twice = twice | (new & ambiguous)
            value = read_as.alias(self.CELL).zip_with(new, value)
            warned[code] = warned[code] | new
            fits = fits | new
        if declared:
            warned.pop(ReadingWarning.MONTH_NAME)
        return (fits, twice, value), warned

    def iso_date(self, *, year: pl.Series, month: pl.Series, day: pl.Series) -> pl.Series:
        """A date from its year, month, and day as text, null where no such day exists."""
        frame = pl.DataFrame({"y": year, "M": month, "d": day})
        written = frame.select(
            pl.format("{}-{}-{}", pl.col("y"), pl.col("M").str.zfill(2), pl.col("d").str.zfill(2)).alias(self.CELL)
        )[self.CELL]
        return written.str.to_date("%Y-%m-%d", strict=False)

    def serial_date(self, serial: str, system: SerialDate) -> datetime | None:
        """A date serial as a moment, or `None` for a serial its system has no date for. Excel's 1900 system counts a
        29 February 1900 that never happened, so serials after it are a day ahead of the calendar."""
        days = float(serial)
        whole = int(days)
        if system == SerialDate.UNIX:
            return self.EPOCH_UNIX + timedelta(seconds=days)
        if system == SerialDate.EXCEL_1904:
            epoch, last = self.EPOCH_1904, self.LAST_SERIAL_1904
        elif whole in (0, self.PHANTOM_LEAP_DAY):
            return None
        else:
            epoch, last = (
                (self.EPOCH_1900 if whole > self.PHANTOM_LEAP_DAY else self.EPOCH_1900_EARLY),
                self.LAST_SERIAL_1900,
            )
        if whole > last:
            return None
        return epoch + timedelta(days=whole, milliseconds=round((days - whole) * self.MILLISECONDS_A_DAY))

    def serials(
        self, *, text: pl.Series, types: pl.Series, fits: pl.Series, value: pl.Series, system: SerialDate
    ) -> tuple[pl.Series, pl.Series, pl.Series, pl.Series]:
        """Read each cell no pattern fitted that is a bare number as a serial, whether text or a stored number. Returns
        what fits, the values, whether a serial held a time, the cell types, a serial then being read, and which cells
        were serials."""
        readable = types.is_in([CellType.STRING.value, CellType.NUMBER.value])
        shape = self.patterns.UNIX_SERIAL if system == SerialDate.UNIX else self.patterns.SERIAL
        serial = (text.str.contains(shape).fill_null(False) & ~fits & readable).alias(self.CELL)
        if not serial.any():
            return fits, value, pl.repeat(False, text.len(), eager=True), types, serial
        moments = {cell: self.serial_date(cell, system) for cell in text.filter(serial).unique().to_list()}
        read = [moments.get(cell) for cell in text.to_list()]
        held_time = [moment is not None and (moment.hour or moment.minute or moment.second) for moment in read]
        written = pl.Series(self.CELL, read, dtype=pl.Datetime("us")).cast(value.dtype)
        tags = pl.repeat(CellType.STRING.value, text.len(), eager=True).zip_with(serial, types)
        held = pl.Series(self.CELL, [bool(held) for held in held_time], dtype=pl.Boolean) & serial
        return fits | serial, written.zip_with(serial, value), held, tags, serial

    def zoned(
        self, *, value: pl.Series, offsets: pl.Series, zone: str | None
    ) -> tuple[pl.Series, pl.Series, pl.Series]:
        """A datetime in its zone or, with none declared, UTC, from each cell's own offset or its declared clock. Returns
        whether the clocks repeated each time, read as the earlier, and whether a cell has neither offset nor zone."""
        target = zone or self.UTC
        stated = offsets.is_not_null()
        minutes = {cell: self.offset_minutes(cell) for cell in offsets.drop_nulls().unique().to_list()}
        shift = pl.Series(self.CELL, [minutes.get(o, 0) for o in offsets.to_list()], dtype=pl.Int64)
        utc = value.dt.replace_time_zone(self.UTC) - shift.cast(pl.Duration("us")) * self.MICROSECONDS["m"]
        from_offset = utc.dt.convert_time_zone(target).alias(self.CELL)
        if zone is None:
            nothing = pl.repeat(None, value.len(), eager=True, dtype=from_offset.dtype).alias(self.CELL)
            no_zone = ~stated & value.is_not_null()
            return from_offset.zip_with(stated, nothing), pl.repeat(False, value.len(), eager=True), no_zone
        earlier = value.dt.replace_time_zone(target, ambiguous="earliest", non_existent="null").alias(self.CELL)
        later = value.dt.replace_time_zone(target, ambiguous="latest", non_existent="null").alias(self.CELL)
        repeated = (~stated & (earlier != later)).fill_null(False)
        return from_offset.zip_with(stated, earlier), repeated, pl.repeat(False, value.len(), eager=True)

    def offset_minutes(self, offset: str) -> int:
        """A cell's offset from UTC, in minutes: `Z`, `+01`, `+0100`, or `-05:30`."""
        if offset == "Z":
            return 0
        digits = offset[1:].replace(":", "")
        minutes = int(digits[:2]) * 60 + int(digits[2:] or 0)
        return -minutes if offset[0] == "-" else minutes

    def temporal_frame(
        self,
        *,
        cells: pl.Series,
        types: pl.Series,
        mixed: pl.Series,
        fits: pl.Series,
        twice: pl.Series,
        named: pl.Series,
        no_zone: pl.Series | None = None,
        warned: dict[ReadingWarning, pl.Series] | None = None,
    ) -> pl.DataFrame:
        length = cells.len()
        frame = pl.DataFrame(
            {
                "blank": self.is_blank(cells),
                "type": types,
                "form": cells.str.contains(self.patterns.NUMBER_FORM).fill_null(False),
                "mixed": mixed,
                "fits": fits,
                "twice": twice,
                "named": named,
                "no_zone": pl.repeat(False, length, eager=True) if no_zone is None else no_zone,
                **{code.value: flag.fill_null(False) for code, flag in (warned or {}).items()},
            }
        )
        return frame.with_columns(self.temporal_reason())

    def stored_patterns(self, dtype: str) -> list[str]:
        """What a stored date cell's rendering may be, for a type: a datetime at midnight renders as a date, and a period
        is whichever date the cell holds."""
        if dtype in self.PERIODS:
            return [self.STORED_DATETIME_MIDNIGHT]
        canonical = self.CANONICAL[dtype]
        return [*canonical, self.STORED_DATETIME_MIDNIGHT] if dtype == FieldType.DATETIME.value else canonical

    def patterns_read(
        self, *, text: pl.Series, patterns: list[str], rules: RulesModel, dtype: str
    ) -> tuple[pl.Series, pl.Series, pl.Series]:
        """Whether each cell fits any pattern, whether two read it differently, and its value by the first that fits."""
        fits, twice, value = None, None, None
        for pattern in patterns:
            written = self.pattern_dtype(pattern, dtype)
            tail = dtype == FieldType.DATE.value
            fit, read = self.pattern_value(text=text, pattern=pattern, rules=rules, dtype=written, tail=tail)
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
        return (
            FieldType.DATE.value
            if pattern == self.STORED_DATETIME_MIDNIGHT and dtype != FieldType.DATE.value
            else dtype
        )

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
            (pl.col("no_zone"), RefusalReason.NO_ZONE),
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
                written = (
                    read
                    if written is None
                    else (
                        written[0] | read[0],
                        written[1].zip_with(written[0], read[1]),
                        written[2].zip_with(written[0], read[2]),
                    )
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

    def pattern_duration(
        self, *, text: pl.Series, pattern: str, rules: RulesModel
    ) -> tuple[pl.Series, pl.Series, pl.Series]:
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
