# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import csv
import pandas as pd
from pydantic import AnyUrl

import whyqd as qd
from whyqd.parsers import CoreParser, DataSourceParser

DIRECTORY = Path(__file__).resolve().parent / "data"
BASE_DIRECTORY = f"{Path('__file__').resolve().parent}/"
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
        # Consistency
        d = datasource.exclude_uuid(model=datasource.get)
        d["checksums"] = [c for c in d["checksums"] if c["content"] == "table-1x"]
        D = datasource.exclude_uuid(model=MODEL["SINGLE"])
        # Using relative paths for test, so adjust accordingly
        d["path"] = d["path"].replace(BASE_DIRECTORY, "")
        D["path"] = D["path"].replace(BASE_DIRECTORY, "")
        # the MODEL doesn't have AnyURL set in the citation
        D["citation"]["url"] = AnyUrl(D["citation"]["url"])
        assert d == D

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
        datasource.derive_model(source=DATA["CTHULHU"], mimetype=MIMETYPE, header=None)
        datasource.validate()

    def test_attribute_variations(self):
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=DATA["CSV"], mimetype=CSVTYPE, quoting=csv.QUOTE_ALL)
        datasource.validate()

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
