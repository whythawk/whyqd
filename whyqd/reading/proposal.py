# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar

import polars as pl

from whyqd.config.names import NameTables
from whyqd.dtypes import CellType, FieldType, FindingKind, ReadingKind, ReadingWarning, RefusalReason, SerialDate
from whyqd.models import FindingModel, PolicyModel, ProposalModel, RulesModel
from whyqd.reading.reading import ReadingParser


class ProposalParser:
    """What a wrangler could declare for a typed column, found by trying declarations rather than guessing one.

    A few candidate policies are built from what the column's cells show, and each is read by the field's own reader.
    A candidate is kept where it refuses no cell. Where the kept candidates read the column alike, the one leaving the
    fewest warnings, and declaring the least, is proposed; where they read it differently, the reading cannot be known
    from the data, so they are shown and nothing is proposed; where none is kept, no one declaration reads the column,
    and that is shown. No cell is ever read by another: each candidate is judged on the whole column. Nothing is
    applied.

    Examples:
      ```python
      import polars as pl

      from whyqd.reading.proposal import ProposalParser

      cells = pl.Series(["31.12.2024", "04.01.1997", "13.04.2024"])
      ProposalParser().propose(field="start", cells=cells, types=None, dtype="date").value.format   # dd.MM.yyyy
      ```
    """

    DAY_FIRST: ClassVar[str] = "dd{0}MM{0}{1}"
    MONTH_FIRST: ClassVar[str] = "MM{0}dd{0}{1}"
    YEAR_FIRST: ClassVar[tuple[str, ...]] = ("yyyy{0}MM{0}dd", "yyyy{0}dd{0}MM")
    RUN: ClassVar[str] = "yyyyMMdd"
    FULL_YEAR: ClassVar[str] = "yyyy"
    SHORT_YEAR: ClassVar[str] = "yy"
    # No cell says which century a two-digit year is in, so two are tried, which read differently
    CENTURIES: ClassVar[tuple[int, ...]] = (1900, 2000)
    DAY_NAMES: ClassVar[tuple[str, ...]] = ("d MMM yyyy", "d MMMM yyyy")
    NAME_DAYS: ClassVar[tuple[str, ...]] = ("MMM d, yyyy", "MMMM d, yyyy", "MMM d yyyy", "MMMM d yyyy")
    INDIAN: ClassVar[str] = "#,##,##0"
    # Each word beside a number doubles the candidates; more than this many words are markers, not one currency
    WORDS: ClassVar[int] = 2

    def __init__(self) -> None:
        self.reader = ReadingParser()
        self.candidates = {
            FieldType.DATE.value: self.date_candidates,
            FieldType.NUMBER.value: self.number_candidates,
            FieldType.INTEGER.value: self.number_candidates,
            FieldType.BOOLEAN.value: self.boolean_candidates,
        }
        # The languages each month-name candidate stands for, as the last column's date candidates found them
        self.speakers: dict[str, list[str]] = {}

    def propose(
        self, *, field: str, cells: pl.Series, types: pl.Series | None, dtype: str
    ) -> ProposalModel | FindingModel | None:
        """A policy to propose for a column read as `dtype`, a fact saying why none can be, or `None` where the column
        reads with nothing to confirm.

        Parameters:
          field: The column's field, named in what is returned.
          cells: Each cell's text as stored, null where empty.
          types: Each cell's `CellType` tag, for a file that stores them.
          dtype: The type the column is read as.

        Returns:
          A `ProposalModel` of the field's whole policy; a fact, `policy-ambiguous` or `policy-mixed`; or `None`.
        """
        if dtype not in self.candidates:
            return None
        cold = self.reader.column(cells=cells, dtype=dtype, types=types)
        troubled = self.troubled(cold)
        if troubled == 0:
            return None
        read_cold = cold[self.reader.KIND] == ReadingKind.VALUE.value
        cold_values = cold[self.reader.VALUE].cast(pl.String)
        kept = []
        for policy in self.candidates[dtype](cells=cells, types=types, cold=cold):
            readings = self.reader.column(cells=cells, dtype=dtype, policy=policy, types=types)
            refuses = readings[self.reader.REASON].is_not_null().any()
            contradicts = (readings[self.reader.VALUE].cast(pl.String) != cold_values).fill_null(True) & read_cold
            if not (refuses or contradicts.any()):
                kept.append((policy, readings))
        if not kept:
            return self.fact(field=field, code="policy-mixed", says="no one declaration reads every cell")
        readings = {}
        for policy, read in kept:
            # A mark and a currency read a cell alike and mean different things, so they never read as one
            marks = tuple(policy.rules.marks) if policy.rules and policy.rules.marks else ()
            key = (tuple(read[self.reader.VALUE].cast(pl.String).to_list()), marks)
            readings.setdefault(key, []).append((policy, read))
        if len(readings) > 1:
            tried = ", ".join(f"`{self.described(group[0][0])}`" for group in readings.values())
            return self.fact(
                field=field, code="policy-ambiguous", says=f"each of {tried} reads every cell, but differently"
            )
        alike = next(iter(readings.values()))
        policy, read = min(alike, key=lambda kept: self.weight(*kept))
        if policy.rules and policy.rules.language:
            speakers = sorted({tag for kept, _ in alike for tag in self.speakers.get(kept.rules.language, [])})
            return self.fact(
                field=field,
                code="policy-language",
                says=f"`{policy.format}` reads every cell by the month names of {self.listed(speakers)}, and no cell "
                "says which language the publisher wrote",
            )
        if self.troubled(read) >= troubled:
            return None
        blank = int((read[self.reader.KIND] == ReadingKind.BLANK.value).sum())
        return ProposalModel(
            setting="policy",
            field=field,
            value=policy,
            evidence=f"Reads all {read.height - blank} cells as `{dtype}`; undeclared, "
            f"{int(cold[self.reader.REASON].is_not_null().sum())} were refused and {self.warned(cold)} warned.",
        )

    def date_candidates(self, *, cells: pl.Series, types: pl.Series | None, cold: pl.DataFrame) -> list[PolicyModel]:
        """The date patterns a column's text cells show, each order its numbers allow; for month names, each language
        whose names they all are; and `rules.serial` beside them where the column held a serial."""
        p = self.reader.patterns
        text, _ = self.reader.prepared(cells)
        is_text = pl.repeat(True, cells.len(), eager=True) if types is None else types == CellType.STRING.value
        text = text.filter(is_text.fill_null(True))
        parts = text.str.extract_groups(p.DATE_PARTS).struct.unnest()
        patterns = []
        for first, separator, second, last in (
            parts.drop_nulls()
            .select(pl.col("1").str.len_chars(), "2", pl.col("4"), pl.col("5").str.len_chars())
            .unique(maintain_order=True)
            .iter_rows()
        ):
            if separator != second:
                continue
            if first == len(self.FULL_YEAR):
                patterns += [(pattern.format(separator), ()) for pattern in self.YEAR_FIRST]
            elif last == len(self.FULL_YEAR):
                patterns += [
                    (order.format(separator, self.FULL_YEAR), ()) for order in (self.DAY_FIRST, self.MONTH_FIRST)
                ]
            elif last == len(self.SHORT_YEAR):
                patterns += [
                    (order.format(separator, self.SHORT_YEAR), (("yearStart", century),))
                    for order in (self.DAY_FIRST, self.MONTH_FIRST)
                    for century in self.CENTURIES
                ]
        if text.str.contains(p.DATE_RUN).any():
            patterns.append((self.RUN, ()))
        spaced = text.str.replace_all(p.COMMA, " ", literal=True)
        day_name = spaced.str.extract_groups(p.DAY_NAME).struct.unnest()["2"]
        name_day = spaced.str.extract_groups(p.NAME_DAY).struct.unnest()["1"]
        shapes = [
            *(self.DAY_NAMES if day_name.is_not_null().any() else ()),
            *(self.NAME_DAYS if name_day.is_not_null().any() else ()),
        ]
        names = set(self.reader.dates.name_keys(pl.concat([day_name, name_day]).drop_nulls()).to_list())
        self.speakers = self.languages_reading(names) if shapes else {}
        for language in self.speakers:
            patterns += [(pattern, (("language", language),)) for pattern in shapes]
        serial = ReadingWarning.SERIAL.value in self.warnings(cold)
        found = []
        for pattern, rules in dict.fromkeys(patterns):
            rules = dict(rules)
            if serial:
                found.append(PolicyModel(format=pattern, rules=rules | {"serial": SerialDate.EXCEL_1900.value}))
            found.append(PolicyModel(format=pattern, rules=rules or None))
        if serial:
            found.append(PolicyModel(rules={"serial": SerialDate.EXCEL_1900.value}))
        return found

    def languages_reading(self, names: set[str]) -> dict[str, list[str]]:
        """The languages that hold every one of a column's month names, grouped by the months they read them as, each
        group under its first language: languages reading the names alike need reading only once."""
        groups = {}
        for language in NameTables.languages():
            table = self.reader.dates.month_names(RulesModel(language=language))
            if names <= table.keys():
                groups.setdefault(tuple(sorted((name, table[name]) for name in names)), []).append(language)
        return {languages[0]: languages for languages in groups.values()}

    def number_candidates(self, *, cells: pl.Series, types: pl.Series | None, cold: pl.DataFrame) -> list[PolicyModel]:
        """The marks a column's cells show, as decimal and group, with Indian grouping where a cell has it; and what
        the cold read read past with a warning, declared. A word beside a number is tried as a currency and as a mark,
        which read alike and mean different things."""
        p = self.reader.patterns
        text, _ = self.reader.prepared(cells)
        between = set(text.str.extract_all(p.MARK_BETWEEN).explode().drop_nulls().str.slice(1, 1).to_list())
        indian = text.str.contains(p.INDIAN_GROUPS).fill_null(False).any()
        formats = []
        numbers = self.reader.numbers
        for decimal in dict.fromkeys([numbers.DECIMAL_MARK, numbers.GROUP_MARK, *sorted(between)]):
            for group in [None, *sorted(between - {decimal})]:
                written = {"decimalChar": decimal} | ({} if group is None else {"groupChar": group})
                formats.append(written)
                if group is not None and indian:
                    formats.append(written | {"pattern": self.INDIAN})
        warned = self.warnings(cold)
        rules = {}
        if self.reader.MARKS in cold.columns:
            if currency := sorted({mark for marks in cold[self.reader.MARKS].to_list() if marks for mark in marks}):
                rules["currency"] = currency
        if ReadingWarning.SIGN.value in warned:
            stepped = self.reader.steps(cells)
            rules["negative"] = [
                form
                for form in numbers.UNDECLARED_NEGATIVE
                if stepped.str.contains(p.around(*form.split(RulesModel.NUMBER_PLACE))).any()
            ]
        if ReadingWarning.PERCENT.value in warned:
            rules["percent"] = numbers.UNDECLARED_PERCENT
        if ReadingWarning.EXPONENT.value in warned:
            rules["exponent"] = True
        words = cold.filter(pl.col(self.reader.REASON) == RefusalReason.UNDECLARED_CHARACTER.value)[self.reader.DETAIL]
        variants = [rules]
        found = sorted({word.strip() for word in words.drop_nulls().to_list() if word.strip()})
        for word in found if len(found) <= self.WORDS else []:
            variants = [
                *[variant | {"currency": [*variant.get("currency", []), word]} for variant in variants],
                *[variant | {"marks": [*variant.get("marks", []), word]} for variant in variants],
            ]
        return [PolicyModel(format=written, rules=variant or None) for written in formats for variant in variants]

    def boolean_candidates(self, *, cells: pl.Series, types: pl.Series | None, cold: pl.DataFrame) -> list[PolicyModel]:
        """Both orders of a column's two values: which of a pair is true, no cell says."""
        text = self.reader.steps(cells)
        values = sorted(set(text.filter(~self.reader.is_blank(cells)).to_list()))
        if len(values) != 2:
            return []
        first, second = values
        return [PolicyModel(format=f"{first}|{second}"), PolicyModel(format=f"{second}|{first}")]

    def warnings(self, readings: pl.DataFrame) -> set[str]:
        """Every warning a reading gave."""
        return {code for codes in readings[self.reader.WARNINGS].to_list() for code in codes}

    def troubled(self, readings: pl.DataFrame) -> int:
        """How many cells a reading refused or warned on."""
        return int(readings[self.reader.REASON].is_not_null().sum()) + self.warned(readings)

    def warned(self, readings: pl.DataFrame) -> int:
        """How many cells a reading warned on."""
        return int((readings[self.reader.WARNINGS].list.len() > 0).sum())

    def weight(self, policy: PolicyModel, readings: pl.DataFrame) -> tuple[int, int]:
        """What makes one of several alike readings the one to propose: fewer warnings, then less declared."""
        declared = policy.model_dump(exclude_none=True)
        return self.warned(readings), len(declared.get("rules", {})) + ("format" in declared)

    def listed(self, tags: list[str]) -> str:
        """Language tags in words: `` `da` and `en` ``; `` `bs`, `da`, and `en` ``."""
        quoted = [f"`{tag}`" for tag in tags]
        return " and ".join(quoted) if len(quoted) < 3 else f"{', '.join(quoted[:-1])}, and {quoted[-1]}"

    def described(self, policy: PolicyModel) -> str:
        """A policy in a few words: its format, then its rules."""
        declared = policy.model_dump(exclude_none=True)
        rules = ", ".join(f"{name} {value}" for name, value in declared.get("rules", {}).items())
        return " ".join(part for part in (str(declared.get("format", "")), rules) if part)

    def fact(self, *, field: str, code: str, says: str) -> FindingModel:
        """Why nothing is proposed for a field, and the one thing to do."""
        return FindingModel(
            code=code,
            kind=FindingKind.FACT,
            message=f"Field `{field}`: {says}. Next, declare the field's `policy` as the publisher wrote it.",
            field=field,
        )
