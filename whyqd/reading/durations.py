# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar

import polars as pl

from whyqd.dtypes import CellType
from whyqd.models import PolicyModel, RulesModel
from whyqd.reading.dates import DateParser
from whyqd.reading.reader import BaseReadingParser


class DurationParser(BaseReadingParser):
    """Read a `duration` field's cells as ISO 8601, or by a declared pattern's quantities, sharing a date's pattern
    grammar."""

    BOUNDS: ClassVar[dict[str, int]] = {"H": 24, "m": 60, "s": 60}

    def __init__(self) -> None:
        super().__init__()
        self.dates = DateParser()

    def read_duration(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """ISO 8601 days, hours, minutes, and seconds, or a declared pattern's quantities: `H:mm` reads `1:30`, and
        `m' min'` reads `25 min`. Years and months have no fixed length, so neither can be read. A stored duration reads
        by its rendering."""
        rules = policy.declared_rules()
        declared = policy.declared_patterns()
        text, mixed = self.prepared(cells)
        fits, value = self.iso_durations(text)
        within = pl.repeat(True, cells.len(), eager=True).alias(self.CELL)
        if declared:
            readings = [self.pattern_duration(text=text, pattern=pattern, rules=rules) for pattern in declared]
            matched, bounded, total = readings[0]
            for fit, inside, amount in readings[1:]:
                bounded = bounded.zip_with(matched, inside)
                total = total.zip_with(matched, amount)
                matched = matched | fit
            is_stored = types == CellType.DATE.value
            fits = fits.zip_with(is_stored, matched)
            within = within.zip_with(is_stored, bounded)
            value = value.zip_with(is_stored, total)
        twice = pl.repeat(False, cells.len(), eager=True)
        frame = self.dates.temporal_frame(cells=cells, types=types, mixed=mixed, fits=fits, twice=twice, named=within)
        return self.outcome(frame, value.cast(pl.Duration(self.dates.TIME_UNIT)))

    def iso_durations(self, text: pl.Series) -> tuple[pl.Series, pl.Series]:
        """Whether each cell is an ISO 8601 duration, holding at least one unit, and its microseconds."""
        found = text.str.extract_groups(self.patterns.DURATION).struct.unnest()
        units = self.dates.MICROSECONDS
        groups = {letter: str(index + 2) for index, letter in enumerate(units)}
        amounts = {letter: found[group].cast(pl.Float64).fill_null(0.0) for letter, group in groups.items()}
        any_part = found.select(pl.any_horizontal(pl.col(group).is_not_null() for group in groups.values()))
        total = sum(amounts[letter] * float(units[letter]) for letter in units)
        negative = found["1"].is_not_null()
        signed = (total * -1.0).zip_with(negative, total).round().cast(pl.Int64).alias(self.CELL)
        return any_part.to_series().alias(self.CELL), signed

    def pattern_duration(
        self, *, text: pl.Series, pattern: str, rules: RulesModel
    ) -> tuple[pl.Series, pl.Series, pl.Series]:
        """Whether each cell fits a duration's pattern, that every field after the first is in range, and its
        microseconds. A fraction `S` is of a second."""
        regex, fields = self.dates.pattern_regex(pattern, rules, quantities=True)
        found = text.str.extract_groups(regex).struct.unnest()
        total = pl.repeat(0.0, text.len(), eager=True, dtype=pl.Float64).alias(self.CELL)
        within = pl.repeat(True, text.len(), eager=True).alias(self.CELL)
        for index, field in enumerate(fields):
            column = found[str(index + 1)].alias(self.CELL)
            if field == "S":
                total = total + ("0." + column).cast(pl.Float64).fill_null(0.0) * float(self.dates.MICROSECONDS["s"])
                continue
            amount = column.cast(pl.Float64).fill_null(0.0)
            total = total + amount * float(self.dates.MICROSECONDS[field[0]])
            if index and field[0] in self.BOUNDS:
                within = within & (amount < self.BOUNDS[field[0]])
        return found["1"].is_not_null().alias(self.CELL), within, total.round().cast(pl.Int64).alias(self.CELL)
