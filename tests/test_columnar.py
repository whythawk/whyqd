# SPDX-License-Identifier: BSD-3-Clause
"""Parquet and Feather read to the same grid as every other format: each typed value in whyqd's own text.

A columnar file stores types, not text, so each value is rendered as `CellParser.render` gives it: a whole number
without `.0` (a column of integers with a missing value included), a date as its ISO date, a boolean as `TRUE` or
`FALSE`. The same table written as a CSV reads the same.
"""

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.parsers import DataSourceParser, RowKeyParser

ROW = RowKeyParser.ROW
NAMES = ["Reference", "UPRN", "Amount", "Paid", "Start Date", "Updated", "Code"]
ROWS = [
    ["769705120", "37019199", "12.5", "TRUE", "2024-04-01", "2024-04-01T09:30:00", "0012"],
    ["918400640", None, "1000", "FALSE", "2024-12-25", "2024-12-25", None],
]


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Reference": pd.Series([769705120, 918400640], dtype="int64"),
            "UPRN": pd.Series([37019199, None], dtype="Int64"),
            "Amount": [12.5, 1000.0],
            "Paid": [True, False],
            "Start Date": [date(2024, 4, 1), date(2024, 12, 25)],
            "Updated": [datetime(2024, 4, 1, 9, 30), datetime(2024, 12, 25)],
            "Code": ["0012", None],
        }
    )


def read(source: Path, mimetype: str) -> tuple[qd.models.DataSourceModel, pd.DataFrame]:
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(source=source, mimetype=mimetype)
    df = DataSourceParser().get(source=datasource.get)
    assert df[ROW].tolist() == list(range(len(df)))
    return datasource.get, df


def rows(df: pd.DataFrame, names: list[str]) -> list[list[str | None]]:
    return [[None if pd.isna(c) else c for c in row] for row in df[names].values.tolist()]


class TestColumnar:
    @pytest.mark.parametrize("mimetype", ["PARQUET", "FEATHER"])
    @pytest.mark.xfail(strict=True, raises=(AssertionError, KeyError), reason="the reader keeps pandas' types")
    def test_each_value_reads_as_whyqds_text(self, tmp_path, frame, mimetype):
        source = tmp_path / f"table.{mimetype.lower()}"
        frame.to_parquet(source) if mimetype == "PARQUET" else frame.to_feather(source)
        model, df = read(source, mimetype)
        assert [c.name for c in model.columns] == NAMES
        assert rows(df, NAMES) == ROWS

    @pytest.mark.xfail(strict=True, raises=(AssertionError, KeyError), reason="the reader keeps pandas' types")
    def test_a_parquet_file_reads_as_its_csv_does(self, tmp_path, frame):
        frame.to_parquet(tmp_path / "table.parquet")
        (tmp_path / "table.csv").write_text(
            ",".join(NAMES) + "\n" + "".join(",".join(c or "" for c in r) + "\n" for r in ROWS), encoding="utf-8"
        )
        _, parquet = read(tmp_path / "table.parquet", "PARQUET")
        _, text = read(tmp_path / "table.csv", "CSV")
        assert rows(parquet, NAMES) == rows(text, NAMES)

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="a column named for the row key is not renamed")
    def test_a_column_named_for_the_row_key_is_renamed(self, tmp_path):
        source = tmp_path / "keyed.parquet"
        pd.DataFrame({ROW: ["a", "b"], "x": ["1", "2"]}).to_parquet(source)
        model, df = read(source, "PARQUET")
        assert [c.name for c in model.columns] == [f"{ROW}.1", "x"]
        assert df[f"{ROW}.1"].tolist() == ["a", "b"]
