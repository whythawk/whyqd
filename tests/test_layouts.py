# SPDX-License-Identifier: BSD-3-Clause
r"""Each CSV layout in the synthetic fixture read to its answer key, under the dialect the key declares.

Read with fixed defaults, a file loads as written: a blank line is a numbered row, a quoted line break stays in its
cell, `N/A` and its kind are text, and a trailing delimiter's empty last column is trimmed with the grid. Every line
end (`\r\n`, `\n`, `\r`) ends a row. The grid is as wide as its widest row: a column past the header is named by
position, and a short row's missing cells are empty. Where the default cannot read the file as meant (`;` between
cells, a quote that never closes, a quote escaped by a backslash), the key's dialect declares it.
The layouts read elsewhere: `title-above.csv` in `test_header.py`, `hostile-headers.csv` in `test_column_names.py`, and
`two-line-records.csv` in `test_records.py`.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.parsers import DataSourceParser, RowKeyParser

LAYOUTS = Path(__file__).resolve().parent / "data" / "synthetic-layouts"
KEY = json.loads((LAYOUTS / "answer-key.json").read_text(encoding="utf-8"))["csv"]
ROW = RowKeyParser.ROW
CASES = [
    "blank-line-inside.csv",
    "quoted-line-break.csv",
    "semicolon.csv",
    "stray-quote.csv",
    "trailing-delimiter.csv",
    "missing-like-text.csv",
    "backslash-escape.csv",
    "cr-line-ends.csv",
    "header-narrower.csv",
    "first-row-narrower.csv",
    "row-narrower.csv",
    "two-line-records-unpadded.csv",
]


@pytest.mark.parametrize("name", CASES)
def test_each_layout_reads_to_its_key(name):
    case = KEY[name]
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(
        source=LAYOUTS / name, mimetype="CSV", **({"dialect": case["dialect"]} if case["dialect"] else {})
    )
    assert datasource.get.dialect is not None
    df = DataSourceParser().get(source=datasource.get)
    assert [c.name for c in datasource.get.columns] == case["names"]
    assert df[ROW].tolist() == list(range(len(case["rows"])))
    # The key writes an empty cell as the file does; the table holds it as missing, as `CellParser.render` gives it
    expected = [[c if c != "" else None for c in row] for row in case["rows"]]
    assert [[None if pd.isna(c) else c for c in row] for row in df[case["names"]].values.tolist()] == expected


def test_a_1x_csv_with_a_blank_line_warns_that_its_rows_are_renumbered():
    # 1.x skipped the blank line, so it read one row fewer and numbered every row after it one lower
    model = qd.models.DataSourceModel(
        path=str(LAYOUTS / "blank-line-inside.csv"),
        mime="text/csv",
        columns=[{"name": n} for n in KEY["blank-line-inside.csv"]["names"]],
        # Its 1.x checksum is what marks it as read by 1.x; the value is never checked here
        checksums=[{"algorithm": "BLAKE2b-512", "checksumValue": "0", "content": "table-1x"}],
        index=len(KEY["blank-line-inside.csv"]["rows"]) - 1,
    )
    with pytest.warns(UserWarning, match="1.x read 6"):
        df = DataSourceParser().get(source=model)
    assert len(df) == 7
