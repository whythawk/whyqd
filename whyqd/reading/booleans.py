# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar

import polars as pl

from whyqd.dtypes import CellType, RefusalReason
from whyqd.models import PolicyModel
from whyqd.reading.reader import BaseReadingParser


class BooleanParser(BaseReadingParser):
    """Read a `boolean` field's cells by its declared pairs, or with none its canonical form."""

    BOOLEANS: ClassVar[dict[str, bool]] = {"true": True, "1": True, "false": False, "0": False}

    def read_boolean(self, *, cells: pl.Series, types: pl.Series, policy: PolicyModel) -> pl.DataFrame:
        """A declared pair exactly as written, or with none the canonical form in any case. A stored boolean is already
        a value."""
        terms = {}
        for pair in policy.declared_patterns():
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
        """Why a boolean cell is refused, the first of these that holds."""
        return self.refusal(
            (
                (pl.col("type") == CellType.ERROR.value, RefusalReason.ERROR_CELL),
                (pl.col("type") == CellType.BOOLEAN.value, None),
                (pl.col("type") != CellType.STRING.value, RefusalReason.NOT_IN_FORMAT),
                (pl.col("blank") | pl.col("known"), None),
                (pl.lit(True), RefusalReason.NOT_IN_FORMAT),
            )
        )
