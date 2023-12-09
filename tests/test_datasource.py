from pathlib import Path
import csv

import whyqd as qd
from whyqd.parsers import CoreParser

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
        # Consistency
        d = datasource.exclude_uuid(model=datasource.get)
        D = datasource.exclude_uuid(model=MODEL["SINGLE"])
        # Using relative paths for test, so adjust accordingly
        d["path"] = d["path"].replace(BASE_DIRECTORY, "")
        D["path"] = D["path"].replace(BASE_DIRECTORY, "")
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
