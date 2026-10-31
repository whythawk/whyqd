# SPDX-License-Identifier: BSD-3-Clause
"""The header row, as the wrangler declares it, and the rows the table keeps.

Under the dialect, the header row and every row above it are not in the table: row 0 is the first row after the
header, or the file's first where there is none. A 1.x data source upgrades to the dialect that reads its rows as 1.x
did, so a stored crosswalk addresses the same rows: `header` N names the columns from row N and keeps every row as data,
which is a file with no header row and those names.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.parsers import DataSourceParser, RowKeyParser
from whyqd.parsers.v1 import V1ChecksumParser

DATA = Path(__file__).resolve().parent / "data"
LAYOUTS = DATA / "synthetic-layouts"
KEY = json.loads((LAYOUTS / "answer-key.json").read_text(encoding="utf-8"))["csv"]
WORLD_BANK = DATA / "working_test_world_bank_data.xlsx"
ROW = RowKeyParser.ROW


def table(datasource: qd.DataSourceDefinition, index: int | None = None):
    model = datasource.get if index is None else datasource.get[index]
    return DataSourceParser().get(source=model)


def cells(rows: list[list[str]]) -> list[list[str | None]]:
    # The key writes an empty cell as the file does; the table holds it as missing, as `CellParser.render` gives it
    return [[c if c != "" else None for c in row] for row in rows]


def values(df: pd.DataFrame) -> list[list[str | None]]:
    return [[None if pd.isna(c) else c for c in row] for row in df.values.tolist()]


def write(tmp_path: Path, text: str) -> Path:
    source = tmp_path / "source.csv"
    source.write_text(text, encoding="utf-8")
    return source


class TestHeader:
    def test_rows_above_the_header_leave_the_table(self):
        case = KEY["title-above.csv"]
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=LAYOUTS / "title-above.csv", mimetype="CSV", dialect=case["dialect"])
        df = table(datasource)
        assert [c.name for c in datasource.get.columns] == case["names"]
        assert df[ROW].tolist() == list(range(len(case["rows"])))
        assert values(df[case["names"]]) == cells(case["rows"])

    def test_each_sheet_takes_its_own_dialect(self):
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=WORLD_BANK, mimetype="XLSX", dialect=[{"skipRows": 3}, {}, {}])
        df = table(datasource, 0)
        assert datasource.get[0].index == 264
        assert df[ROW].tolist() == list(range(264))
        assert df["Country Name"].iloc[0] == "Aruba"
        assert "Country Name" not in df["Country Name"].tolist()

    def test_no_header_row_is_named_by_position(self, tmp_path):
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=write(tmp_path, "a,b\n1,2\n"), mimetype="CSV", dialect={"headerRowCount": 0})
        df = table(datasource)
        assert [c.name for c in datasource.get.columns] == ["column_0", "column_1"]
        assert df[ROW].tolist() == [0, 1]
        assert df[["column_0", "column_1"]].values.tolist() == [["a", "b"], ["1", "2"]]

    def test_no_header_row_takes_the_names_given(self, tmp_path):
        datasource = qd.DataSourceDefinition()
        source = write(tmp_path, "a,b\n1,2\n")
        datasource.derive_model(source=source, mimetype="CSV", dialect={"headerRowCount": 0}, names=["x", "y"])
        df = table(datasource)
        assert datasource.get.dialect.headerRowCount == 0
        assert df[["x", "y"]].values.tolist() == [["a", "b"], ["1", "2"]]

    def test_a_header_over_two_rows_takes_the_names_given(self, tmp_path):
        datasource = qd.DataSourceDefinition()
        source = write(tmp_path, "Rate,Rate\nfrom,to\n1,2\n")
        datasource.derive_model(source=source, mimetype="CSV", dialect={"headerRowCount": 2}, names=["start", "end"])
        df = table(datasource)
        assert df[ROW].tolist() == [0]
        assert df[["start", "end"]].values.tolist() == [["1", "2"]]

    def test_a_header_over_two_rows_without_names_is_refused(self, tmp_path):
        datasource = qd.DataSourceDefinition()
        source = write(tmp_path, "Rate,Rate\nfrom,to\n1,2\n")
        with pytest.raises(ValueError, match=r"(?s)headerRowCount.*\bnames\b"):
            datasource.derive_model(source=source, mimetype="CSV", dialect={"headerRowCount": 2})

    def test_an_unknown_setting_is_refused_naming_those_known(self, tmp_path):
        datasource = qd.DataSourceDefinition()
        with pytest.raises(ValueError, match="skipRows"):
            datasource.derive_model(source=write(tmp_path, "a\n1\n"), mimetype="CSV", dialect={"skiprows": 1})

    @pytest.mark.parametrize("setting", [{"header": 3}, {"quoting": 1}])
    def test_a_reader_keyword_is_refused_naming_the_dialect(self, tmp_path, setting):
        datasource = qd.DataSourceDefinition()
        with pytest.raises(TypeError, match="dialect"):
            datasource.derive_model(source=write(tmp_path, "a\n1\n2\n3\n4\n"), mimetype="CSV", **setting)


class TestHeader1x:
    """A 1.x data source reads the rows 1.x read, numbered as 1.x numbered them."""

    def test_a_header_below_row_0_keeps_every_row(self):
        model = qd.DataSourceDefinition(source=DATA / "test_world_bank_header_source.data").get
        model.path = str(WORLD_BANK)
        assert model.dialect is not None and model.dialect.headerRowCount == 0
        expected = V1ChecksumParser().read(source=model)
        df = DataSourceParser().get(source=model)
        assert df[ROW].tolist() == list(range(len(expected))) == list(range(268))
        assert values(df[["Country Name"]])[:5] == [["Data Source"], ["Last Updated Date"], [None], ["Country Name"], ["Aruba"]]
        assert df["Country Name"].fillna("").tolist() == expected["Country Name"].fillna("").tolist()

    def test_a_stored_crosswalk_gives_the_same_output(self):
        # Its `DELETE_ROWS < [0, 1, 2, 3]` removes the title rows and the header row, which 1.x kept as data
        source = qd.DataSourceDefinition(source=DATA / "test_world_bank_header_source.data")
        source.get.path = str(WORLD_BANK)
        crosswalk = qd.CrosswalkDefinition(crosswalk=DATA / "test_world_bank_header.crosswalk")
        transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=source.get)
        transform.process()
        expected = pd.read_parquet(DATA / "test_world_bank_header_output.parquet")
        pd.testing.assert_frame_equal(transform.data.reset_index(drop=True), expected)

    def test_no_header_row_with_names_keeps_them(self):
        model = qd.DataSourceDefinition(source=DATA / "test_cthulu_source.data").get
        model.path = str(DATA / Path(model.path).name)
        assert model.dialect is not None and model.dialect.headerRowCount == 0
        df = DataSourceParser().get(source=model)
        assert [c for c in df.columns if c != ROW] == model.names
        assert df[ROW].tolist() == list(range(model.index))
