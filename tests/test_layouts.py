# SPDX-License-Identifier: BSD-3-Clause
"""Each CSV layout in the synthetic fixture read to its answer key, under the dialect the key declares.

Read with fixed defaults, a file loads as written: a blank line is a numbered row, a quoted line break stays in its
cell, `N/A` and its kind are text, and a trailing delimiter's empty last column is trimmed with the grid. Where the
default cannot read the file as meant (`;` between cells, a quote that never closes), the key's dialect declares it.
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
]


@pytest.mark.parametrize("name", CASES)
@pytest.mark.xfail(strict=True, raises=(AssertionError, ValueError), reason="the reader takes no dialect")
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
