# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Any, ClassVar, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from whyqd.config.patterns import PythonPatterns
from whyqd.dtypes import CellType, FieldType, ReadingKind, RefusalReason


class NumberFormatModel(BaseModel):
    """How a number is written: the number format of a CSV on the Web derived datatype
    ([Metadata Vocabulary for Tabular Data, section 5.11.2](https://www.w3.org/TR/tabular-metadata/#derived-datatypes))."""

    decimalChar: Optional[str] = Field(None, description="The decimal mark, such as `.` or `,`.")
    groupChar: Optional[str] = Field(None, description="The grouping mark, such as `,` in `1,000`.")
    pattern: Optional[str] = Field(
        None,
        description="A number pattern in the declared marks, such as `#,##0.00`. Its commas give the group sizes, so "
        "`#,##,##0` reads lakh grouping.",
    )
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class RulesModel(BaseModel):
    """What a reading needs that a CSV on the Web derived datatype cannot say. Each is for the wrangler to declare, so
    nothing here is assumed of a file, and a rule whyqd does not know is refused rather than ignored."""

    NUMBER: ClassVar[frozenset[str]] = frozenset(
        {"currency", "marks", "negative", "percent", "perMille", "exponent", "nonFinite"}
    )
    UNWHOLE: ClassVar[frozenset[str]] = frozenset({"percent", "perMille", "nonFinite"})
    TEMPORAL: ClassVar[frozenset[str]] = frozenset(
        {"yearStart", "monthNames", "monthAbbreviations", "dayPeriods", "zone"}
    )
    PATTERNED: ClassVar[frozenset[str]] = frozenset({"alternateFormats"})
    MONTHS: ClassVar[int] = 12
    DAY_PERIODS: ClassVar[int] = 2
    NUMBER_PLACE: ClassVar[str] = "x"

    currency: list[str] = Field([], description="Currency marks a number may carry, such as `£`, `CHF`, or `¬£`.")
    marks: list[str] = Field([], description="Other marks a number may carry, such as `#`, each with no meaning.")
    negative: list[str] = Field(
        [],
        description="Forms of a negative beyond a leading `-`, with `x` for the number: `(x)`, `x-`, or `x CR`. A form "
        "not declared refuses, and never reads as positive.",
    )
    percent: Optional[str] = Field(None, description="The mark of a percent, such as `%`. `5%` reads as 0.05.")
    perMille: Optional[str] = Field(None, description="The mark of a per mille, such as `‰`. `5‰` reads as 0.005.")
    exponent: bool = Field(False, description="Whether a number may have an exponent, such as `1E3`.")
    nonFinite: bool = Field(False, description="Whether `NaN`, `INF`, and `-INF` read as numbers.")
    alternateFormats: list[str] = Field(
        [],
        description="Further date patterns or boolean pairs, where no cell could match two: `yyyy-MM-dd` beside "
        "`dd/MM/yyyy`, or `Yes|No` beside `Y|N`.",
    )
    yearStart: Optional[int] = Field(
        None,
        ge=1000,
        le=9999,
        description="The first year of the 100 years a `yy` pattern reads: `1950` reads `49` as 2049 and `50` as 1950.",
    )
    monthNames: list[str] = Field([], description="The twelve names `MMMM` reads, from January.")
    monthAbbreviations: list[str] = Field([], description="The twelve names `MMM` reads, from January.")
    dayPeriods: list[str] = Field([], description="The two names `a` reads, morning first, such as `AM` and `PM`.")
    zone: Optional[str] = Field(
        None,
        description="The IANA time zone a datetime's clock is in, such as `UTC` or `Europe/London`. With none, a "
        "datetime stays without a zone. A `Z` in the cell is a quoted literal in its pattern, beside `UTC` here.",
    )
    cellFormats: dict[CellType, str] = Field(
        {},
        description="By a workbook's stored cell type, a pattern reading that cell's rendering, where it differs from "
        "its text: `{'d': 'yyyy-dd-MM'}` for a column of date cells whose day and month Excel swapped.",
    )
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @field_validator("negative")
    @classmethod
    def holds_the_number(cls, v: list[str]) -> list[str]:
        for form in v:
            if form.count(cls.NUMBER_PLACE) != 1:
                raise ValueError(
                    f"The negative form `{form}` has no single `x` for its number. Write it as `(x)` or `x CR`. "
                    "[whyqd:policy-negative-form]"
                )
        return v

    @field_validator("dayPeriods")
    @classmethod
    def two_periods(cls, v: list[str]) -> list[str]:
        if v and (len(v) != cls.DAY_PERIODS or len(set(v)) != cls.DAY_PERIODS):
            raise ValueError(
                f"{len(v)} day periods are declared, and a 12-hour clock needs two different ones, morning first. "
                "[whyqd:policy-day-periods]"
            )
        return v

    @field_validator("zone")
    @classmethod
    def known_zone(cls, v: Optional[str]) -> Optional[str]:
        try:
            if v is not None:
                ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, OSError) as error:
            raise ValueError(f"`{v}` is no IANA time zone. Use a name such as `Europe/London`. [whyqd:policy-zone]") from error
        return v

    @field_validator("monthNames", "monthAbbreviations")
    @classmethod
    def twelve_months(cls, v: list[str]) -> list[str]:
        if v and (len(v) != cls.MONTHS or len(set(v)) != cls.MONTHS):
            raise ValueError(
                f"{len(v)} month names are declared, and a date's month needs twelve different ones, from January. "
                "[whyqd:policy-month-names]"
            )
        return v


class PolicyModel(BaseModel):
    """How to read a field's text as its type: a CSV on the Web derived datatype
    ([Metadata Vocabulary for Tabular Data, section 5.11.2](https://www.w3.org/TR/tabular-metadata/#derived-datatypes)),
    `base` and `format`, with whyqd's own `rules` beside it.

    A field without a policy is read as text.

    Example:
      ```python
      {"format": {"decimalChar": ",", "groupChar": "."}, "rules": {"currency": ["€"], "negative": ["x-"]}}
      {"format": "dd.MM.yy", "rules": {"yearStart": 1950}}
      {"format": "Y|N", "rules": {"alternateFormats": ["Yes|No"]}}
      ```
    """

    NUMBERS: ClassVar[frozenset[str]] = frozenset({FieldType.NUMBER.value, FieldType.INTEGER.value})
    UNREAD: ClassVar[frozenset[str]] = frozenset({FieldType.STRING.value, FieldType.ARRAY.value, FieldType.ANY.value})
    EXACT: ClassVar[str] = "decimal"
    PAIR: ClassVar[str] = "|"
    # Fields whyqd reads, from UAX 35's date patterns. Each is exact where its length says so, and `y` is four digits,
    # since a reader taking fewer would read `01/04/24` as the year 24. On a duration each is a quantity, not a clock.
    YEAR_FIELDS: ClassVar[frozenset[str]] = frozenset({"y", "yy", "yyy", "yyyy"})
    MONTH_FIELDS: ClassVar[frozenset[str]] = frozenset({"M", "MM", "MMM", "MMMM"})
    DATE_FIELDS: ClassVar[frozenset[str]] = YEAR_FIELDS | MONTH_FIELDS | {"d", "dd"}
    TIME_FIELDS: ClassVar[frozenset[str]] = frozenset({"H", "HH", "h", "hh", "a", "m", "mm", "s", "ss", "S"})
    READABLE: ClassVar[dict[str, frozenset[str]]] = {
        FieldType.DATE.value: DATE_FIELDS,
        FieldType.TIME.value: TIME_FIELDS,
        FieldType.DATETIME.value: DATE_FIELDS | TIME_FIELDS,
        FieldType.MONTH.value: YEAR_FIELDS | MONTH_FIELDS,
        FieldType.QUARTER.value: YEAR_FIELDS | MONTH_FIELDS | {"Q"},
        FieldType.YEAR.value: YEAR_FIELDS,
        FieldType.DURATION.value: frozenset({"d", "dd", "H", "HH", "m", "mm", "s", "ss", "S"}),
    }
    NEEDED: ClassVar[dict[str, frozenset[str]]] = {
        FieldType.DATE.value: frozenset("yMd"),
        FieldType.TIME.value: frozenset("H"),
        FieldType.DATETIME.value: frozenset("yMdH"),
        FieldType.MONTH.value: frozenset("yM"),
        FieldType.QUARTER.value: frozenset("yM"),
        FieldType.YEAR.value: frozenset("y"),
    }
    WIDTHS: ClassVar[dict[str, tuple[int, int]]] = {
        "y": (4, 4),
        "yyyy": (4, 4),
        "yy": (2, 2),
        "yyy": (3, 3),
        "Q": (1, 1),
        "h": (1, 2),
        "hh": (2, 2),
        "a": (1, 99),
        "M": (1, 2),
        "MM": (2, 2),
        "MMM": (1, 99),
        "MMMM": (1, 99),
        "d": (1, 2),
        "dd": (2, 2),
        "H": (1, 2),
        "HH": (2, 2),
        "m": (1, 2),
        "mm": (2, 2),
        "s": (1, 2),
        "ss": (2, 2),
    }

    base: Optional[str] = Field(
        None, description="The datatype the text is read as: the field's type, or `decimal` for an exact number."
    )
    format: Optional[Union[str, NumberFormatModel]] = Field(
        None,
        description="How the text is written: a number's format; a boolean's `true|false` pair, such as `Y|N`; or a "
        "date's pattern, such as `dd.MM.yyyy`.",
    )
    rules: Optional[RulesModel] = Field(None, description="whyqd's own reading rules, beyond `base` and `format`.")
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    def check(self, *, name: str, dtype: str) -> None:
        """Refuse a policy that cannot read a field `name` of type `dtype`, when it is declared rather than at a read.

        Raises:
          ValueError: Naming what does not fit, with its code.
        """
        rules = self.rules or RulesModel()
        declared = rules.model_fields_set
        number, boolean = dtype in self.NUMBERS, dtype == FieldType.BOOLEAN.value
        temporal = not (number or boolean or dtype in self.UNREAD)
        exact = number and self.base == self.EXACT and dtype == FieldType.NUMBER.value
        unfit = [f"`base` {self.base}"] if self.base not in (None, dtype) and not exact else []
        if dtype in self.UNREAD and (self.format is not None or declared):
            unfit.append("`format` or `rules`")
        if isinstance(self.format, NumberFormatModel) != number and self.format is not None:
            unfit.append(f"`format` {self.format}")
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.NUMBER if not number]
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.UNWHOLE if dtype == FieldType.INTEGER.value]
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.TEMPORAL if not temporal]
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.PATTERNED if number]
        if "zone" in declared and dtype != FieldType.DATETIME.value:
            unfit.append("`rules.zone`")
        patterns = [self.format] * isinstance(self.format, str) + rules.alternateFormats
        if boolean:
            unfit += [f"`{pair}`, not one `true|false` pair" for pair in patterns if pair.count(self.PAIR) != 1]
        if unfit:
            raise ValueError(
                f"Field `{name}` is `{dtype}`, so its policy cannot hold {', '.join(unfit)}. Change the field's type "
                "or remove them. [whyqd:policy-conflict]"
            )
        if temporal:
            self.check_patterns(name=name, dtype=dtype, patterns=patterns, rules=rules)

    @classmethod
    def parts(cls, pattern: str) -> list[tuple[bool, str]]:
        """A date pattern's parts in order, each `(is_field, text)`; a quoted literal without its quotes."""
        found = []
        for match in PythonPatterns.PATTERN_PART.finditer(pattern):
            text = match.group()
            quoted = text.startswith("'")
            found.append((bool(match.group(1)), text[1:-1] if quoted else text))
        return found

    def check_patterns(self, *, name: str, dtype: str, patterns: list[str], rules: RulesModel) -> None:
        """Refuse a pattern whyqd cannot read, one that needs a rule not declared, a rule no pattern needs, and two
        patterns giving one cell different readings."""
        fields = [{text for is_field, text in self.parts(pattern) if is_field} for pattern in patterns]
        for pattern, held in zip(patterns, fields):
            allowed = self.READABLE.get(dtype, self.READABLE[FieldType.DATE.value])
            needed = self.NEEDED.get(dtype, frozenset())
            letters = {field[0].replace("h", "H").replace("Q", "M") for field in held}
            if held - allowed or not needed <= letters or (dtype == FieldType.DURATION.value and not held):
                raise ValueError(
                    f"Field `{name}` is `{dtype}`, and its pattern `{pattern}` holds a field it cannot read, or lacks "
                    f"one it needs ({', '.join(sorted(needed)) or 'any'}). Correct the pattern. [whyqd:policy-pattern]"
                )
        every = set().union(*fields) if fields else set()
        if ("yy" in every) != (rules.yearStart is not None):
            raise ValueError(
                f"Field `{name}` needs `rules.yearStart` with a `yy` pattern, and only then: `yy` does not say which "
                "century. Declare both, or neither. [whyqd:policy-year-start]"
            )
        if bool(rules.monthNames) != ("MMMM" in every) or bool(rules.monthAbbreviations) != ("MMM" in every):
            raise ValueError(
                f"Field `{name}` needs `rules.monthNames` with an `MMMM` pattern and `rules.monthAbbreviations` "
                "with an `MMM` one, and only then. Declare both sides. [whyqd:policy-month-names]"
            )
        twelve_hour = {field[0] for field in every} & {"h", "a"}
        if bool(rules.dayPeriods) != bool(twelve_hour) or twelve_hour not in (set(), {"h", "a"}):
            raise ValueError(
                f"Field `{name}` needs `h` and `a` and `rules.dayPeriods` together, for a 12-hour clock, and only then. "
                "Declare all three, or none. [whyqd:policy-day-periods]"
            )
        for index, first in enumerate(patterns):
            for second in patterns[index + 1 :]:
                if self.two_readings(first, second):
                    raise ValueError(
                        f"Field `{name}`: a cell could fit both `{first}` and `{second}`, and read differently. Keep "
                        "the one the file uses. [whyqd:policy-two-readings]"
                    )

    @classmethod
    def two_readings(cls, first: str, second: str) -> bool:
        """Whether one cell could fit both patterns and read differently: the same literals, widths that meet, and a
        position that means something else. `d/M/yyyy` and `dd/MM/yyyy` read alike, and `MM/dd/yyyy` does not."""
        ones, others = cls.parts(first), cls.parts(second)
        if len(ones) != len(others):
            return False
        differs = False
        for (one_field, one), (other_field, other) in zip(ones, others):
            if one_field != other_field or (not one_field and one != other):
                return False
            if one_field:
                low_one, high_one = cls.WIDTHS.get(one, (0, 0))
                low_other, high_other = cls.WIDTHS.get(other, (0, 0))
                if max(low_one, low_other) > min(high_one, high_other):
                    return False
                differs = differs or one[0] != other[0]
        return differs


class CellReadingModel(BaseModel):
    """What one cell read as under its field's declaration: a value, a blank, or a refusal with its reason."""

    kind: ReadingKind = Field(..., description="A value, a blank, or a refusal.")
    value: Any = Field(None, description="The value read, for a cell that held one.")
    reason: Optional[RefusalReason] = Field(None, description="Why the cell was refused.")
    detail: Optional[str] = Field(None, description="What in the cell was refused, such as the character it holds.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @model_validator(mode="after")
    def reason_refuses(self) -> CellReadingModel:
        if (self.kind == ReadingKind.REFUSED.value) != (self.reason is not None):
            raise ValueError("A refusal has a reason, and nothing else does.")
        if self.kind != ReadingKind.VALUE.value and self.value is not None:
            raise ValueError("Only a cell read as a value holds one.")
        return self
