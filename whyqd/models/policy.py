# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

from whyqd.config.names import NameTables
from whyqd.dtypes import CellType, FieldFamilies, FieldType, SerialDate
from whyqd.reading.pattern import PatternParser


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
        {"yearStart", "language", "monthNames", "dayPeriods", "zone", "serial"}
    )
    PATTERNED: ClassVar[frozenset[str]] = frozenset({"alternateFormats"})
    MONTHS: ClassVar[int] = 12
    DAY_PERIODS: ClassVar[int] = 2
    NUMBER_PLACE: ClassVar[str] = "x"

    currency: list[str] = Field(
        [],
        description="Currency marks a number may carry, such as `£`, `CHF`, or `¬£`. With none declared, a mark of "
        "Unicode's currency category, or `¬£`, reads with a warning; with any declared, another refuses.",
    )
    marks: list[str] = Field([], description="Other marks a number may carry, such as `#`, each with no meaning.")
    negative: list[str] = Field(
        [],
        description="Forms of a negative beyond a leading `-`, with `x` for the number: `(x)`, `x-`, or `x CR`. With "
        "none declared, `(x)` and `x-` read with a warning; with any declared, another refuses, never reading as "
        "positive.",
    )
    percent: Optional[str] = Field(
        None,
        description="The mark of a percent, such as `٪`. `5%` reads as 0.05, with a warning where none is declared.",
    )
    perMille: Optional[str] = Field(None, description="The mark of a per mille, such as `‰`. `5‰` reads as 0.005.")
    exponent: Optional[bool] = Field(
        None,
        description="Whether a number may have an exponent, such as `1E3`: unset, it reads with a warning; `false` "
        "refuses it, so a reference such as `12E4` stays one.",
    )
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
        None,
        description="The language of month and weekday names, by its tag, such as `de`: any spelling and any case.",
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
    serial: Optional[SerialDate] = Field(
        None,
        description="Read a bare number as a date serial, in Excel's `excel-1900` or `excel-1904` system, or as `unix` "
        "seconds, beside any patterns: `45295` reads as 2024-01-04 under `excel-1900`. Unset, a bare number reads by "
        "`excel-1900` with a warning.",
    )
    cellFormats: dict[CellType, str] = Field(
        {},
        description="For a date, time, or period field, the pattern a workbook's stored date cells (`d`) are read by, "
        "where it differs from their text: `{'d': 'yyyy-dd-MM'}` for a column of date cells whose day and month Excel "
        "swapped.",
    )
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    @staticmethod
    def spellings(entry: str | list[str]) -> list[str]:
        """A name's entry in `monthNames` or `dayPeriods` as its list of spellings."""
        return [entry] if isinstance(entry, str) else entry

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
            raise ValueError(
                f"whyqd holds no names for `{v}`. Use a tag such as `de`, or `rules.monthNames`. [whyqd:policy-names]"
            )
        return v

    @field_validator("monthNames", "dayPeriods")
    @classmethod
    def one_for_each(cls, v: list, info) -> list:
        wanted = cls.MONTHS if info.field_name == "monthNames" else cls.DAY_PERIODS
        spelled = [name.lower().rstrip(".") for entry in v for name in cls.spellings(entry)]
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
            raise ValueError(
                f"`{v}` is no IANA time zone. Use a name such as `Europe/London`. [whyqd:policy-zone]"
            ) from error
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

    EXACT: ClassVar[str] = "decimal"
    PAIR: ClassVar[str] = "|"
    # What a 1.x `usdate` stated: month first, with any of its separators
    USDATE: ClassVar[dict] = {"format": "MM/dd/yyyy", "rules": {"alternateFormats": ["MM-dd-yyyy", "MM.dd.yyyy"]}}
    PATTERN: ClassVar[PatternParser] = PatternParser()

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

    def declared_rules(self) -> RulesModel:
        """The rules declared, or with none an empty set of them."""
        return self.rules or RulesModel()

    def declared_patterns(self) -> list[str]:
        """A date's patterns or a boolean's pairs: `format`, then `rules.alternateFormats`."""
        return [self.format] * isinstance(self.format, str) + self.declared_rules().alternateFormats

    def check(self, *, name: str, dtype: str) -> None:
        """Save a date pattern in UAX 35's form, and refuse a policy that cannot read a field `name` of type `dtype`,
        when it is declared rather than at a read.

        Raises:
          ValueError: Naming what does not fit, with its code.
        """
        rules = self.declared_rules()
        declared = rules.model_fields_set
        number, boolean = dtype in FieldFamilies.NUMBERS, dtype == FieldType.BOOLEAN.value
        temporal = not (number or boolean or dtype in FieldFamilies.NO_POLICY)
        if temporal:
            self.standardise(dtype=dtype, rules=rules)
        exact = number and self.base == self.EXACT and dtype == FieldType.NUMBER.value
        unfit = [f"`base` {self.base}"] if self.base not in (None, dtype) and not exact else []
        if dtype in FieldFamilies.NO_POLICY and (self.format is not None or declared):
            unfit.append("`format` or `rules`")
        if isinstance(self.format, NumberFormatModel) != number and self.format is not None:
            unfit.append(f"`format` {self.format}")
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.NUMBER if not number]
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.UNWHOLE if dtype == FieldType.INTEGER.value]
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.TEMPORAL if not temporal]
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.PATTERNED if number]
        if "zone" in declared and dtype != FieldType.DATETIME.value:
            unfit.append("`rules.zone`")
        if "serial" in declared and dtype in FieldFamilies.QUANTITIES:
            unfit.append("`rules.serial`")
        if "cellFormats" in declared and (not temporal or dtype == FieldType.DURATION.value):
            unfit.append("`rules.cellFormats`")
        elif "cellFormats" in declared:
            unfit += [
                f"`rules.cellFormats` for `{tag.value}` cells" for tag in rules.cellFormats if tag != CellType.DATE
            ]
        patterns = self.declared_patterns()
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
        pattern = self.PATTERN
        if isinstance(self.format, str):
            self.format = pattern.standard_pattern(self.format, dtype)
        if rules.alternateFormats:
            rules.alternateFormats = [pattern.standard_pattern(typed, dtype) for typed in rules.alternateFormats]
        if rules.cellFormats:
            rules.cellFormats = {tag: pattern.standard_pattern(p, dtype) for tag, p in rules.cellFormats.items()}

    def check_patterns(self, *, name: str, dtype: str, patterns: list[str], rules: RulesModel) -> None:
        """Refuse a pattern whyqd cannot read, one that needs a rule not declared, and two patterns giving one cell
        different readings."""
        grammar = self.PATTERN
        fields = [{text for is_field, text in grammar.parts(pattern) if is_field} for pattern in patterns]
        for pattern, held in zip(patterns, fields, strict=True):
            needed = grammar.NEEDED.get(dtype, frozenset())
            letters = {field[0].replace("h", "H").replace("Q", "M") for field in held}
            if (
                held - grammar.READABLE[dtype]
                or not needed <= letters
                or (dtype == FieldType.DURATION.value and not held)
            ):
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
        if every & grammar.NAME_FIELDS and not rules.language and not (rules.monthNames and "E" not in str(every)):
            raise ValueError(
                f"Field `{name}` has names in its pattern, so it needs `rules.language`, such as `de`, to say which "
                "names they are. [whyqd:policy-names]"
            )
        for index, first in enumerate(patterns):
            for second in patterns[index + 1 :]:
                if grammar.two_readings(first, second):
                    raise ValueError(
                        f"Field `{name}`: a cell could fit both `{first}` and `{second}`, and read differently. Keep "
                        "the one the file uses. [whyqd:policy-two-readings]"
                    )
