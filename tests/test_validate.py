from pathlib import Path

import whyqd
from whyqd.transform.parsers import CoreScript


SOURCE_DIRECTORY = str(Path(__file__).resolve().parent)
METHOD_FILE = "/data/test_method.json"
METHOD_SOURCE = SOURCE_DIRECTORY + METHOD_FILE
METHOD = CoreScript().load_json(source=METHOD_SOURCE)
INPUT_DATA = [
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_0.XLSX",
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_1.XLSX",
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_2.XLSX",
]
RESTRUCTURED_DATA = SOURCE_DIRECTORY + "/data/restructured_test_data.xlsx"


class TestMethod:
    def test_validate_path(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        validate = whyqd.Validate(directory=DIRECTORY)
        validate.set(source=METHOD_SOURCE)
        validate.import_input_data(path=INPUT_DATA)
        validate.import_restructured_data(path=RESTRUCTURED_DATA)
        assert validate.validate()

    def test_validate_json(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(directory=DIRECTORY)
        validate = whyqd.Validate(directory=DIRECTORY)
        validate.set(method=METHOD)
        validate.import_input_data(path=INPUT_DATA)
        validate.import_restructured_data(path=RESTRUCTURED_DATA)
        assert validate.validate()
