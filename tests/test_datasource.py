# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import pandas as pd
import pytest
from pydantic import AnyUrl

import whyqd as qd
from whyqd.parsers import CoreParser, DataSourceParser

DIRECTORY = Path(__file__).resolve().parent / "data"
DATA = {
    "SINGLE": DIRECTORY / "raw_E06000044_014_0.XLSX",
    "MULTI": DIRECTORY / "raw_multi_E06000044_014.xlsx",
    "CTHULHU": DIRECTORY / "HDR-2007-2008-Table-03.xlsx",
    "CSV": DIRECTORY / "test_data.csv",
}
MIMETYPE = "XLSX"
CSVTYPE = "CSV"
MODEL = {"SINGLE": CoreParser().load_json(source=DIRECTORY / "raw_E06000044_014_0.data")}


class TestDataSource:
    def test_single(self, tmp_path):
        # Create
        TEST_DIRECTORY = str(tmp_path) + "/"
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=DATA["SINGLE"], mimetype=MIMETYPE)
        citation = {
            "author": "Gavin Chait",
            "month": "feb",
            "year": 2020,
            "title": "Portsmouth City Council normalised database of commercial ratepayers",
            "url": "https://github.com/whythawk/whyqd/tree/master/tests/data",
        }
        datasource.set_citation(citation=citation)
        datasource.save(directory=TEST_DIRECTORY)
        datasource.validate()
        assert datasource.get.get_checksum("bytes")
        # The read finds the columns and rows 1.x found; its types and checksum are 2.0's, every cell text
        stored = qd.DataSourceDefinition(source=MODEL["SINGLE"]).get
        assert [c.name for c in datasource.get.columns] == [c.name for c in stored.columns]
        assert datasource.get.index == stored.index
        assert datasource.get.citation.url == AnyUrl(MODEL["SINGLE"]["citation"]["url"])

    def test_load_single(self):
        datasource = qd.DataSourceDefinition(source=MODEL["SINGLE"])
        datasource.validate()

    def test_multi(self):
        # Create
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=DATA["MULTI"], mimetype=MIMETYPE)
        assert isinstance(datasource.model, list)
        for i in range(len(datasource.model)):
            citation = {
                "author": "Gavin Chait",
                "month": "feb",
                "year": 2020 + i,
                "title": "Portsmouth City Council normalised database of commercial ratepayers",
                "url": "https://github.com/whythawk/whyqd/tree/master/tests/data",
            }
            datasource.set_citation(citation=citation, index=i)
        datasource.validate()

    def test_cthulhu(self):
        # Create
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=DATA["CTHULHU"], mimetype=MIMETYPE, dialect={"headerRowCount": 0})
        datasource.validate()

    def test_csv_verifies_by_its_bytes_else_its_cells(self, tmp_path):
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=DATA["CSV"], mimetype=CSVTYPE)
        assert datasource.get.get_checksum("table-1x") is None
        assert datasource.validate()
        # A trailing blank line changes the bytes, not a cell
        resaved = tmp_path / "resaved.csv"
        resaved.write_bytes(DATA["CSV"].read_bytes() + b"\n")
        datasource.get.path = str(resaved)
        with pytest.warns(UserWarning, match="saved again"):
            assert datasource.validate()
        changed = tmp_path / "changed.csv"
        changed.write_bytes(DATA["CSV"].read_bytes() + b"x\n")
        datasource.get.path = str(changed)
        with pytest.raises(AssertionError):
            datasource.validate()

    def test_get_data_is_the_table_the_derive_read(self, tmp_path):
        source = tmp_path / "source.csv"
        source.write_bytes(DATA["CSV"].read_bytes())
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=source, mimetype=CSVTYPE)
        expected = DataSourceParser().get(source=datasource.get)
        # Gone, so the data can only be the derive's
        source.unlink()
        pd.testing.assert_frame_equal(datasource.get_data(), expected)
        # A second derive replaces it
        other = tmp_path / "other.csv"
        other.write_text("Code\n1\n", encoding="utf-8")
        datasource.derive_model(source=other, mimetype=CSVTYPE)
        assert datasource.get_data()["Code"].tolist() == ["1"]

    def test_coerce_keeps_rows_on_any_index(self):
        # Actions can leave a frame indexed by labels rather than 0..n; coercion must keep every value in its row
        schema = qd.SchemaDefinition()
        schema.set(schema={"name": "coercion"})
        schema.fields.add_multi(
            terms=[{"name": "amount", "type": "number"}, {"name": "reliefs", "type": "array"}]
        )
        df = pd.DataFrame(
            {"amount": ["80.0", "88.5"], "reliefs": [["80.0", None], ["88.5", "12.0"]]},
            index=["7", "3"],
        )
        df = DataSourceParser().coerce_to_schema(df=df, schema=schema)
        assert df["amount"].tolist() == [80.0, 88.5]
        assert df["reliefs"].tolist() == [["80.0", None], ["88.5", "12.0"]]

    def test_a_frames_columns_are_typed_as_1x_typed_them(self):
        # A date column is recorded as `string`, as 1.x recorded it; typing records dates
        df = pd.DataFrame({"a": [1.5], "b": pd.array([1], dtype="Int64"), "c": pd.to_datetime(["2024-01-04"]), "d": ["x"]})
        columns = DataSourceParser().get_header_columns(df=df)
        assert [c.dtype for c in columns] == ["number", "number", "string", "string"]

    def test_a_column_takes_whyqds_types_only(self):
        with pytest.raises(ValueError):
            qd.models.ColumnModel(name="a", type="float64")
