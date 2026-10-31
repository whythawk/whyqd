# SPDX-License-Identifier: BSD-3-Clause
"""Records that span several rows, joined as the wrangler declares them in `rowsPerRecord`.

`[5, 1]` is five fields on a record's first row and one on its next, the header included. The join acts on rows as
read, so a quoted line break stays inside its cell, and the row key counts records. A row that does not fit the
declaration is refused, naming it, since every record after it would be misread.
"""

import csv
import json
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.parsers import DataSourceParser, RowKeyParser

DATA = Path(__file__).resolve().parent / "data"
LAYOUTS = DATA / "synthetic-layouts"
KEY = json.loads((LAYOUTS / "answer-key.json").read_text(encoding="utf-8"))["csv"]["two-line-records.csv"]
FENLAND = DATA / "sample" / "fenland" / "2026-10-25-Fenland District Council.csv"
ROW = RowKeyParser.ROW


def read(source: Path, dialect: dict) -> tuple[qd.models.DataSourceModel, pd.DataFrame]:
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(source=source, mimetype="CSV", dialect=dialect)
    return datasource.get, DataSourceParser().get(source=datasource.get)


def rows(df: pd.DataFrame, names: list[str]) -> list[list[str | None]]:
    return [[None if pd.isna(c) else c for c in row] for row in df[names].values.tolist()]


def cells(rows: list[list[str]]) -> list[list[str | None]]:
    # The key writes an empty cell as the file does; the table holds it as missing, as `CellParser.render` gives it
    return [[c if c != "" else None for c in row] for row in rows]


def write(tmp_path: Path, lines: list[list[str]]) -> Path:
    source = tmp_path / "records.csv"
    with source.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(lines)
    return source


PAIRS = [["a", "b", "c"], ["d", "", ""], ["p1", "q1", "r1"], ["s1", "", ""], ["p2", "q2", "r2"], ["s2", "", ""]]


class TestRowsPerRecord:
    def test_records_over_two_rows_join_to_the_key(self):
        model, df = read(LAYOUTS / "two-line-records.csv", KEY["dialect"])
        assert model.dialect.rowsPerRecord == KEY["dialect"]["rowsPerRecord"]
        assert [c.name for c in model.columns] == KEY["names"]
        assert df[ROW].tolist() == list(range(len(KEY["rows"])))
        assert rows(df, KEY["names"]) == cells(KEY["rows"])

    def test_fenland_joins_each_pair(self):
        # 47 fields, then one on the next row, header included
        with FENLAND.open(encoding="utf-8", newline="") as f:
            lines = list(csv.reader(f))
        joined = [first + second[:1] for first, second in zip(lines[0::2], lines[1::2], strict=True)]
        # Its header repeats `Disc %` and `MAND %`, each repeat renamed as any is
        names = RowKeyParser().deconflict(columns=joined[0])
        model, df = read(FENLAND, {"rowsPerRecord": [47, 1]})
        assert [c.name for c in model.columns] == names
        assert model.index == len(joined) - 1 == 50
        assert df[ROW].tolist() == list(range(50))
        assert rows(df, names) == cells(joined[1:])

    def test_a_quoted_line_break_stays_in_its_cell(self, tmp_path):
        lines = [*PAIRS[:2], ["p1", "two\nlines", "r1"], ["s1", "", ""]]
        model, df = read(write(tmp_path, lines), {"rowsPerRecord": [3, 1]})
        assert rows(df, ["a", "b", "c", "d"]) == [["p1", "two\nlines", "r1", "s1"]]


class TestBrokenRecords:
    """The message names the declaration and the line, as a text editor numbers it, where the file stops fitting it."""

    def test_a_continuation_with_values_past_its_fields_is_refused(self, tmp_path):
        # `p1` has lost its continuation, so `p2, q2, r2` on line 4 would be read as it
        lines = [*PAIRS[:3], *PAIRS[4:]]
        with pytest.raises(ValueError, match=r"(?s)rowsPerRecord.*\bline 4\b|\bline 4\b.*rowsPerRecord"):
            read(write(tmp_path, lines), {"rowsPerRecord": [3, 1]})

    def test_a_record_without_its_continuation_is_refused(self, tmp_path):
        # The file ends after `p2`'s first row, on line 5
        with pytest.raises(ValueError, match=r"(?s)rowsPerRecord.*\bline 5\b|\bline 5\b.*rowsPerRecord"):
            read(write(tmp_path, PAIRS[:-1]), {"rowsPerRecord": [3, 1]})
