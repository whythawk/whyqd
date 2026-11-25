# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar

import polars as pl

from whyqd.dtypes import CellType, FieldType, FindingKind, ReadingKind, ReadingWarning, SerialDate
from whyqd.models import FindingModel, PolicyModel, ProposalModel
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

    def __init__(self) -> None:
        self.reader = ReadingParser()
        self.candidates = {FieldType.DATE.value: self.date_candidates}

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
        kept = []
        for policy in self.candidates[dtype](cells=cells, types=types, cold=cold):
            readings = self.reader.column(cells=cells, dtype=dtype, policy=policy, types=types)
            if not (readings[self.reader.REASON].is_not_null()).any():
                kept.append((policy, readings))
        if not kept:
            return self.fact(field=field, code="policy-mixed", says="no one declaration reads every cell")
        readings = {}
        for policy, read in kept:
            readings.setdefault(tuple(read[self.reader.VALUE].cast(pl.String).to_list()), []).append((policy, read))
        if len(readings) > 1:
            tried = ", ".join(f"`{self.described(group[0][0])}`" for group in readings.values())
            return self.fact(
                field=field, code="policy-ambiguous", says=f"each of {tried} reads every cell, but differently"
            )
        policy, read = min(next(iter(readings.values())), key=lambda kept: self.weight(*kept))
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
        """The date patterns a column's text cells show, each order its numbers allow, and `rules.serial` beside them
        where the column held a serial."""
        text, _ = self.reader.prepared(cells)
        is_text = pl.repeat(True, cells.len(), eager=True) if types is None else types == CellType.STRING.value
        parts = text.filter(is_text.fill_null(True)).str.extract_groups(self.reader.patterns.DATE_PARTS).struct.unnest()
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
                patterns += [(pattern.format(separator), None) for pattern in self.YEAR_FIRST]
            elif last == len(self.FULL_YEAR):
                patterns += [
                    (order.format(separator, self.FULL_YEAR), None) for order in (self.DAY_FIRST, self.MONTH_FIRST)
                ]
            elif last == len(self.SHORT_YEAR):
                patterns += [
                    (order.format(separator, self.SHORT_YEAR), century)
                    for order in (self.DAY_FIRST, self.MONTH_FIRST)
                    for century in self.CENTURIES
                ]
        if text.filter(is_text.fill_null(True)).str.contains(self.reader.patterns.DATE_RUN).any():
            patterns.append((self.RUN, None))
        serial = ReadingWarning.SERIAL.value in {
            code for codes in cold[self.reader.WARNINGS].to_list() for code in codes
        }
        found = []
        for pattern, century in dict.fromkeys(patterns):
            rules = {} if century is None else {"yearStart": century}
            if serial:
                found.append(PolicyModel(format=pattern, rules=rules | {"serial": SerialDate.EXCEL_1900.value}))
            found.append(PolicyModel(format=pattern, rules=rules or None))
        if serial:
            found.append(PolicyModel(rules={"serial": SerialDate.EXCEL_1900.value}))
        return found

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
