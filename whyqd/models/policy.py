# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Any, ClassVar, Optional, Union
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
    TEMPORAL: ClassVar[frozenset[str]] = frozenset({"yearStart", "monthNames", "monthAbbreviations"})
    PATTERNED: ClassVar[frozenset[str]] = frozenset({"alternateFormats"})
    MONTHS: ClassVar[int] = 12
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
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.TEMPORAL if not temporal]
        unfit += [f"`rules.{rule}`" for rule in declared & RulesModel.PATTERNED if number]
        patterns = [self.format] * isinstance(self.format, str) + rules.alternateFormats
        if boolean:
            unfit += [f"`{pair}`, not one `true|false` pair" for pair in patterns if pair.count(self.PAIR) != 1]
        if unfit:
            raise ValueError(
                f"Field `{name}` is `{dtype}`, so its policy cannot hold {', '.join(unfit)}. Change the field's type "
                "or remove them. [whyqd:policy-conflict]"
            )
        if temporal:
            self.check_patterns(name=name, patterns=patterns, rules=rules)

    def check_patterns(self, *, name: str, patterns: list[str], rules: RulesModel) -> None:
        """Refuse a date pattern that needs a rule not declared, and a rule no pattern needs. A quoted literal, such as
        `'de'`, is no part of a pattern."""
        written = [PythonPatterns.PATTERN_LITERAL.sub("", pattern) for pattern in patterns]
        two_digit = any(PythonPatterns.PATTERN_TWO_DIGIT_YEAR.search(pattern) for pattern in written)
        if two_digit != (rules.yearStart is not None):
            raise ValueError(
                f"Field `{name}` needs `rules.yearStart` with a `yy` pattern, and only then: `yy` does not say which "
                "century. Declare both, or neither. [whyqd:policy-year-start]"
            )
        for names, search in (
            (rules.monthNames, PythonPatterns.PATTERN_MONTH_NAME),
            (rules.monthAbbreviations, PythonPatterns.PATTERN_MONTH_ABBREVIATION),
        ):
            if bool(names) != any(search.search(pattern) for pattern in written):
                raise ValueError(
                    f"Field `{name}` needs `rules.monthNames` with an `MMMM` pattern and `rules.monthAbbreviations` "
                    "with an `MMM` one, and only then. Declare both sides. [whyqd:policy-month-names]"
                )


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
