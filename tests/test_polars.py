# SPDX-License-Identifier: BSD-3-Clause
r"""What the read relies on Polars for, and what it does not.

The grid is held in Polars and handed on as pandas, so every name and cell must cross between the two unchanged, in
either direction, including a table Polars' own reader could not have opened.

Polars' CSV reader is not used, since it does not read every file as written: a quote escaped by a backslash, `\r`
line ends, rows wider than the first, and a row's own width, which `rowsPerRecord` reads. Each is a strict `xfail` below, so a Polars release that reads it fails the
test, and the choice can be weighed again.
"""

import csv
import json
from pathlib import Path

import pandas as pd
import polars as pl
import pytest

LAYOUTS = Path(__file__).resolve().parent / "data" / "synthetic-layouts"
KEY = json.loads((LAYOUTS / "answer-key.json").read_text(encoding="utf-8"))["csv"]

HOSTILE = [
    ["a", 'Some column \\"with\\" escapes', "one\rtwo", "two\nlines", "", None],
    [" hard space", "​zero-width", "﻿inner mark", "ctrl\x01\x1f", "é beside é", "１２"],
    ["  spaced  ", "\t", "N/A", "null", "x" * 100_000, "\x00nul"],
]
NAMES = ["Unnamed: 0", "__row__.1", "Rate [2026]", "Code, Local", " lead", "trail "]


def cells(df: pd.DataFrame) -> list[list[str | None]]:
    return [[None if pd.isna(c) else c for c in row] for row in df.values.tolist()]


def lines(name: str) -> list[list[str]]:
    # A lone empty value is written as a blank line, which reads as no fields
    return [[] if line == [""] else line for line in KEY[name]["lines"]]


def polars_lines(name: str, **settings) -> list[list[str]]:
    # Each row as read: a field the row lacks is null, an empty field empty text
    df = pl.read_csv(
        LAYOUTS / name, has_header=False, infer_schema=False, empty_string_is_null=False, **settings
    )
    read = []
    for row in df.rows():
        row = list(row)
        while row and row[-1] is None:
            row.pop()
        read.append(row)
    return read


class TestHandover:
    @pytest.mark.parametrize("dtype", ["object", "string"])
    def test_pandas_to_polars_and_back(self, dtype):
        df = pd.DataFrame(HOSTILE, columns=NAMES).astype(dtype)
        back = pl.from_pandas(df).to_pandas()
        assert list(back.columns) == NAMES
        assert cells(back) == HOSTILE

    def test_polars_to_pandas(self):
        grid = pl.DataFrame([dict(zip(NAMES, row, strict=True)) for row in HOSTILE], schema={n: pl.String for n in NAMES})
        df = grid.to_pandas()
        assert list(df.columns) == NAMES
        assert cells(df) == HOSTILE
        assert df.iloc[0, 4] == "" and pd.isna(df.iloc[0, 5])

    @pytest.mark.parametrize("name", ["backslash-escape.csv", "cr-line-ends.csv", "header-narrower.csv"])
    def test_a_table_polars_cannot_open_crosses_unchanged(self, name):
        settings = {"doublequote": False, "escapechar": "\\"} if name == "backslash-escape.csv" else {}
        with (LAYOUTS / name).open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f, **settings))
        width = max(len(r) for r in rows)
        df = pd.DataFrame([r + [None] * (width - len(r)) for r in rows], columns=[f"c{i}" for i in range(width)])
        assert cells(pl.from_pandas(df).to_pandas()) == cells(df)


class TestPolarsReader:
    def test_a_quoted_line_break(self):
        assert polars_lines("quoted-line-break.csv") == lines("quoted-line-break.csv")

    @pytest.mark.parametrize("name", ["blank-line-inside.csv", "row-narrower.csv", "two-line-records-unpadded.csv"])
    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="a short row is padded, so its own width is lost")
    def test_rows_narrower_than_the_first(self, name):
        assert polars_lines(name) == lines(name)

    @pytest.mark.xfail(strict=True, reason="a backslash ends the quoted cell, and no setting escapes it")
    def test_a_quote_escaped_by_a_backslash(self):
        assert polars_lines("backslash-escape.csv") == lines("backslash-escape.csv")

    @pytest.mark.xfail(strict=True, reason="`\\r` alone does not end a row")
    def test_cr_line_ends(self):
        assert polars_lines("cr-line-ends.csv") == lines("cr-line-ends.csv")

    @pytest.mark.parametrize("name", ["header-narrower.csv", "first-row-narrower.csv"])
    @pytest.mark.xfail(strict=True, raises=pl.exceptions.ComputeError, reason="the first row fixes the width")
    def test_rows_wider_than_the_first(self, name):
        assert polars_lines(name) == lines(name)
