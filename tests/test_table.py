# SPDX-License-Identifier: BSD-3-Clause
"""The table's `trim`: a cell trimmed of every character Python counts as whitespace, at the ends the dialect names,
and a cell left empty by it read as empty."""

import sys

import polars as pl
import pytest

from whyqd.dtypes import Place
from whyqd.models import DialectModel
from whyqd.sources.table import TableParser

WHITESPACE = [chr(c) for c in range(sys.maxunicode + 1) if chr(c).isspace()]
TRIMS = {True: str.strip, "start": str.lstrip, "end": str.rstrip}


def trimmed(cells: list[str | None], trim: bool | str) -> list[str | None]:
    grid = pl.DataFrame({"column_0": cells}, schema={"column_0": pl.String})
    dialect = DialectModel(headerRowCount=0, trim=trim)
    table, _ = TableParser().table(
        grid=grid, lines=list(range(1, len(cells) + 1)), dialect=dialect, source="t.csv", place=Place.LINE
    )
    return table["column_0"].to_list()


@pytest.mark.parametrize("trim", list(TRIMS))
def test_trim_strips_every_whitespace_character_as_python_does(trim):
    cells = [f"{c}a{c}" for c in WHITESPACE] + ["".join(WHITESPACE), " a b ", None]
    expected = [TRIMS[trim](c) or None if c is not None else None for c in cells]
    assert trimmed(cells, trim) == expected


def test_trim_strips_python_whitespace_exactly():
    assert sorted(TableParser.WHITESPACE) == WHITESPACE


def test_no_trim_keeps_each_cell_as_written():
    cells = [f"{c}a{c}" for c in WHITESPACE]
    assert trimmed(cells, False) == cells
