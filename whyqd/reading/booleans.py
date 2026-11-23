# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar

import polars as pl

from whyqd.dtypes import CellType, ReadingWarning, RefusalReason
from whyqd.models import PolicyModel, RulesModel
from whyqd.reading.reader import BaseReadingParser


class BooleanParser(BaseReadingParser):
    """Read a `boolean` field's cells by its declared pairs, or with none its canonical form."""

    BOOLEANS: ClassVar[dict[str, bool]] = {BaseReadingParser.TRUE: True, "1": True, "false": False, "0": False}
    KNOWN: ClassVar[str] = "known"

    def read_boolean(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A declared pair exactly as written, or with none the canonical form in any case. A stored boolean is already
        a value, and a stored number reads 1 as `true` and 0 as `false`, with a warning, any other number refused."""
        terms = {}
        for pair in policy.declared_patterns():
            yes, no = (RulesModel.normalised(term) for term in pair.split(PolicyModel.PAIR))
            terms |= {yes: True, no: False}
        text = self.steps(cells)
        lower = text.str.to_lowercase()
        keys, table = (text, terms) if terms else (lower, self.BOOLEANS)
        stored = types == CellType.BOOLEAN.value
        number = types == CellType.NUMBER.value
        written = pl.Series(self.CELL, [table.get(key) for key in keys.to_list()], dtype=pl.Boolean)
        numbered = lower.replace_strict(self.BOOLEANS, default=None, return_dtype=pl.Boolean)
        value = lower.is_in([self.TRUE]).zip_with(stored, numbered.zip_with(number, written))
        read = pl.DataFrame(
            {
                self.BLANK: self.is_blank(cells),
                self.TYPE: types,
                self.KNOWN: value.is_not_null(),
                ReadingWarning.NUMBER_AS_BOOLEAN.value: number,
            }
        )
        return self.outcome(read.with_columns(self.boolean_reason()), value)

    def boolean_reason(self) -> pl.Expr:
        """Why a boolean cell is refused, the first of these that holds."""
        cell_type = pl.col(self.TYPE)
        return self.refusal(
            (
                (cell_type == CellType.ERROR.value, RefusalReason.ERROR_CELL),
                (cell_type == CellType.BOOLEAN.value, None),
                ((cell_type == CellType.NUMBER.value) & pl.col(self.KNOWN), None),
                (cell_type != CellType.STRING.value, RefusalReason.NOT_IN_FORMAT),
                (pl.col(self.BLANK) | pl.col(self.KNOWN), None),
                (pl.lit(True), RefusalReason.NOT_IN_FORMAT),
            )
        )
