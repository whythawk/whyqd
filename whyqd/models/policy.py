# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Any, ClassVar, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from whyqd.config.names import NameTables
from whyqd.config.patterns import PythonPatterns
from whyqd.dtypes import CellType, FieldType, ReadingKind, ReadingWarning, RefusalReason


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
    TEMPORAL: ClassVar[frozenset[str]] = frozenset({"yearStart", "language", "monthNames", "dayPeriods", "zone"})
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
    language: Optional[str] = Field(
        None, description="The language of month and weekday names, by its tag, such as `de`: any spelling and any case."
    )
    monthNames: list[Union[str, list[str]]] = Field(
        [],
        description="Twelve entries from January, each a name or a list of names, read beside any of `language`'s.",
    )
    dayPeriods: list[Union[str, list[str]]] = Field(
        [], description="Two entries, morning first, each a name or a list, read beside `AM`, `PM`, and `language`'s."
    )
    zone: Optional[str] = Field(
        None,
        description="The IANA time zone of a datetime's clock where a cell states no offset, such as `Europe/London`.",
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

    @field_validator("language")
    @classmethod
    def known_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and NameTables.language(v) is None:
            raise ValueError(f"whyqd holds no names for `{v}`. Use a tag such as `de`, or `rules.monthNames`. [whyqd:policy-names]")
        return v

    @field_validator("monthNames", "dayPeriods")
    @classmethod
    def one_for_each(cls, v: list, info) -> list:
        wanted = cls.MONTHS if info.field_name == "monthNames" else cls.DAY_PERIODS
        spelled = [name.lower().rstrip(".") for entry in v for name in ([entry] if isinstance(entry, str) else entry)]
        if v and (len(v) != wanted or len(spelled) != len(set(spelled))):
            raise ValueError(
                f"`rules.{info.field_name}` needs {wanted} entries, in order, with no name in two of them. "
                "[whyqd:policy-names]"
            )
        return v

    @field_validator("zone")
    @classmethod
    def known_zone(cls, v: Optional[str]) -> Optional[str]:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            if v is not None:
                ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, OSError) as error:
            raise ValueError(f"`{v}` is no IANA time zone. Use a name such as `Europe/London`. [whyqd:policy-zone]") from error
        return v


class PolicyModel(BaseModel):
    """How to read a field's text as its type: a CSV on the Web derived datatype
    ([Metadata Vocabulary for Tabular Data, section 5.11.2](https://www.w3.org/TR/tabular-metadata/#derived-datatypes)),
    `base` and `format`, with whyqd's own `rules` beside it.

    A date pattern may be written as Excel, Python's `strptime`, or [UAX 35](
    https://www.unicode.org/reports/tr35/tr35-dates.html#Date_Field_Symbol_Table) writes it. It is saved as UAX 35's,
    which is what CSV on the Web reads, so `dd/mm/yyyy` is saved as `dd/MM/yyyy`.

    A field without a policy is read as text.

    Example:
      ```python
      {"format": {"decimalChar": ",", "groupChar": "."}, "rules": {"currency": ["€"], "negative": ["x-"]}}
      {"format": "dd/mm/yy", "rules": {"yearStart": 1950}}
      {"format": "d MMMM yyyy", "rules": {"language": "de"}}
      {"format": "Y|N", "rules": {"alternateFormats": ["Yes|No"]}}
      ```
    """

    NUMBERS: ClassVar[frozenset[str]] = frozenset({FieldType.NUMBER.value, FieldType.INTEGER.value})
    UNREAD: ClassVar[frozenset[str]] = frozenset({FieldType.STRING.value, FieldType.ARRAY.value, FieldType.ANY.value})
    QUANTITIES: ClassVar[frozenset[str]] = frozenset({FieldType.TIME.value, FieldType.DURATION.value})
    EXACT: ClassVar[str] = "decimal"
    PAIR: ClassVar[str] = "|"
    YEAR_FIELDS: ClassVar[frozenset[str]] = frozenset({"y", "yy", "yyyy"})
    MONTH_FIELDS: ClassVar[frozenset[str]] = frozenset({"M", "MM", "MMM", "MMMM"})
    NAME_FIELDS: ClassVar[frozenset[str]] = frozenset({"MMM", "MMMM", "E", "EEE", "EEEE"})
    DATE_FIELDS: ClassVar[frozenset[str]] = YEAR_FIELDS | MONTH_FIELDS | {"d", "dd", "E", "EEE", "EEEE"}
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
    # How many digits or characters a field reads, a number's width saying nothing of its meaning: `dd` reads `1`
    WIDTHS: ClassVar[dict[str, tuple[int, int]]] = {
        "y": (1, 99),
        "yyyy": (4, 99),
        "yy": (2, 2),
        "Q": (1, 1),
        "M": (1, 2),
        "MM": (1, 2),
        "d": (1, 2),
        "dd": (1, 2),
        "H": (1, 2),
        "HH": (1, 2),
        "h": (1, 2),
        "hh": (1, 2),
        "m": (1, 2),
        "mm": (1, 2),
        "s": (1, 2),
        "ss": (1, 2),
    }
    STRPTIME: ClassVar[dict[str, str]] = {
        "d": "dd",
        "e": "d",
        "m": "MM",
        "Y": "yyyy",
        "y": "yy",
        "H": "HH",
        "I": "hh",
        "M": "mm",
        "S": "ss",
        "f": "S",
        "b": "MMM",
        "B": "MMMM",
        "a": "EEE",
        "A": "EEEE",
        "p": "a",
        "z": "X",
    }
    OFFSET_FIELDS: ClassVar[frozenset[str]] = frozenset("XxZO")

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
        """Save a date pattern in UAX 35's form, and refuse a policy that cannot read a field `name` of type `dtype`,
        when it is declared rather than at a read.

        Raises:
          ValueError: Naming what does not fit, with its code.
        """
        rules = self.rules or RulesModel()
        declared = rules.model_fields_set
        number, boolean = dtype in self.NUMBERS, dtype == FieldType.BOOLEAN.value
        temporal = not (number or boolean or dtype in self.UNREAD)
        if temporal:
            self.standardise(dtype=dtype, rules=rules)
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

    def standardise(self, *, dtype: str, rules: RulesModel) -> None:
        """Write each date pattern as UAX 35 does, however it was typed."""
        if isinstance(self.format, str):
            self.format = self.standard_pattern(self.format, dtype)
        if rules.alternateFormats:
            rules.alternateFormats = [self.standard_pattern(pattern, dtype) for pattern in rules.alternateFormats]
        if rules.cellFormats:
            rules.cellFormats = {tag: self.standard_pattern(p, dtype) for tag, p in rules.cellFormats.items()}

    @classmethod
    def standard_pattern(cls, typed: str, dtype: str) -> str:
        """A pattern as UAX 35 writes it, from Excel's or `strptime`'s spelling.

        A letter's case means nothing in Excel, so `DD` and `YYYY` read as day and year, as they were meant, and `m` is
        minutes beside an hour or a second and otherwise a month, by Excel's own rule. An offset is not part of a
        pattern, a datetime's cell reading one wherever it holds one.
        """
        p = PythonPatterns
        text = p.STRPTIME.sub(lambda match: cls.STRPTIME.get(match.group(1), match.group()), typed)
        text = p.EXCEL_DROPPED.sub("", text)
        text = p.EXCEL_ELAPSED.sub(lambda match: match.group(1), text)
        text = p.EXCEL_DAY_PERIOD.sub("a", text)
        text = p.EXCEL_QUOTED.sub(lambda match: f"'{match.group(1)}'", text)
        text = p.EXCEL_ESCAPED.sub(lambda match: f"'{match.group(1)}'", text)
        text = p.EXCEL_FRACTION.sub(".S", text)
        parts = cls.parts(text)
        fields = [part for is_field, part in parts if is_field]
        twelve_hour = any(field[0] in "aA" for field in fields)
        written = []
        for index, (is_field, part) in enumerate(parts):
            if not is_field:
                dropped = part == "Z" and dtype == FieldType.DATETIME.value
                written.append("" if dropped else f"'{part}'" if any(c.isalpha() for c in part) else part)
                continue
            before = next((f for is_f, f in reversed(parts[:index]) if is_f), "")
            after = next((f for is_f, f in parts[index + 1 :] if is_f), "")
            written.append(cls.standard_field(part, dtype, before, after, twelve_hour))
        return "".join(written).rstrip()

    @classmethod
    def standard_field(cls, field: str, dtype: str, before: str, after: str, twelve_hour: bool) -> str:
        letter, length = field[0], len(field)
        if letter in "yY":
            return "yy" if length == 2 else "yyyy" if length == 4 else "y"
        if letter in "dD":
            return {3: "EEE", 4: "EEEE"}.get(length, "d" * min(length, 2))
        if letter in "mM":
            if length > 2:
                return "M" * length
            minutes = before[:1] in tuple("hH") or after[:1] in tuple("sS") or (letter == "m" and dtype in cls.QUANTITIES)
            return ("m" if minutes else "M") * length
        if letter in "hH":
            return ("h" if twelve_hour else "H") * min(length, 2)
        if letter in "sS":
            return "S" if before[:1] in tuple("sS") else "s" * min(length, 2)
        if letter in "aA":
            return "a"
        if letter in "qQ":
            return "Q"
        if letter == "T":
            return "'T'"
        if letter in cls.OFFSET_FIELDS and dtype == FieldType.DATETIME.value:
            return ""
        return field

    @classmethod
    def parts(cls, pattern: str) -> list[tuple[bool, str]]:
        """A date pattern's parts in order, each `(is_field, text)`; a quoted literal without its quotes."""
        found = []
        for match in PythonPatterns.PATTERN_PART.finditer(pattern):
            text = match.group()
            found.append((bool(match.group(1)), text[1:-1] if text.startswith("'") else text))
        return found

    def check_patterns(self, *, name: str, dtype: str, patterns: list[str], rules: RulesModel) -> None:
        """Refuse a pattern whyqd cannot read, one that needs a rule not declared, and two patterns giving one cell
        different readings."""
        fields = [{text for is_field, text in self.parts(pattern) if is_field} for pattern in patterns]
        for pattern, held in zip(patterns, fields):
            needed = self.NEEDED.get(dtype, frozenset())
            letters = {field[0].replace("h", "H").replace("Q", "M") for field in held}
            if held - self.READABLE[dtype] or not needed <= letters or (dtype == FieldType.DURATION.value and not held):
                raise ValueError(
                    f"Field `{name}` is `{dtype}`, and its pattern `{pattern}` holds a field it cannot read, or lacks "
                    f"one it needs ({', '.join(sorted(needed)) or 'any'}). Correct the pattern, or keep the field as "
                    "`string`. [whyqd:policy-pattern]"
                )
        every = set().union(*fields) if fields else set()
        if ("yy" in every) != (rules.yearStart is not None):
            raise ValueError(
                f"Field `{name}` needs `rules.yearStart` with a `yy` pattern, and only then: `yy` does not say which "
                "century. Declare both, or neither. [whyqd:policy-year-start]"
            )
        if every & self.NAME_FIELDS and not rules.language and not (rules.monthNames and "E" not in str(every)):
            raise ValueError(
                f"Field `{name}` has names in its pattern, so it needs `rules.language`, such as `de`, to say which "
                "names they are. [whyqd:policy-names]"
            )
        if ("h" in every or "hh" in every) != ("a" in every):
            raise ValueError(
                f"Field `{name}`: a 12-hour `h` and a day period `a` go together. Declare both, or use `H`. "
                "[whyqd:policy-day-periods]"
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
                low_one, high_one = cls.WIDTHS.get(one, (1, 99))
                low_other, high_other = cls.WIDTHS.get(other, (1, 99))
                if max(low_one, low_other) > min(high_one, high_other):
                    return False
                meaning = [field if field == "yy" else field[0] for field in (one, other)]
                differs = differs or meaning[0] != meaning[1]
        return differs


class CellReadingModel(BaseModel):
    """What one cell read as under its field's declaration: a value, a blank, or a refusal with its reason, and a warning
    where a value was read with something worth checking."""

    kind: ReadingKind = Field(..., description="A value, a blank, or a refusal.")
    value: Any = Field(None, description="The value read, for a cell that held one.")
    reason: Optional[RefusalReason] = Field(None, description="Why the cell was refused.")
    detail: Optional[str] = Field(None, description="What in the cell was refused, such as the character it holds.")
    warning: Optional[ReadingWarning] = Field(None, description="What to check about a value that was read.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @model_validator(mode="after")
    def reason_refuses(self) -> CellReadingModel:
        if (self.kind == ReadingKind.REFUSED.value) != (self.reason is not None):
            raise ValueError("A refusal has a reason, and nothing else does.")
        if self.kind != ReadingKind.VALUE.value and self.value is not None:
            raise ValueError("Only a cell read as a value holds one.")
        return self
