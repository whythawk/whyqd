from pathlib import Path

import whyqd
from whyqd.parsers import CoreScript

method_name_v1 = "/data/test_method_v1.json"
METHOD_FILE = "/data/test_method.json"
schema_name = "/data/test_schema.json"
SOURCE_DIRECTORY = str(Path(__file__).resolve().parent)
METHOD_SOURCE_V1 = SOURCE_DIRECTORY + method_name_v1
METHOD_SOURCE = SOURCE_DIRECTORY + METHOD_FILE
SCHEMA_SOURCE = SOURCE_DIRECTORY + schema_name
METHOD = CoreScript().load_json(METHOD_SOURCE)
SCHEMA = whyqd.Schema(source=SCHEMA_SOURCE)
INPUT_DATA = [
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_0.XLSX",
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_1.XLSX",
    SOURCE_DIRECTORY + "/data/raw_E06000044_014_2.XLSX",
]
INPUT_DATA_ONESHOT = SOURCE_DIRECTORY + "/data/working_test_data.xlsx"
RESTRUCTURED_DATA = SOURCE_DIRECTORY + "/data/restructured_test_data.xlsx"


class TestMethod:
    def test_create(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(DIRECTORY)
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
        method.set({"name": "test_method"})
        input_data = [{"path": d} for d in INPUT_DATA]
        method.add_data(source=input_data)
        method.save(created_by="Gavin Chait", hide_uuid=True)
        test_source = DIRECTORY + "test_method.json"
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA, method=CoreScript().load_json(test_source))
        assert METHOD["input_data"][0]["checksum"] == method.get.input_data[0].checksum
        assert METHOD["input_data"][1]["checksum"] == method.get.input_data[1].checksum
        assert METHOD["input_data"][2]["checksum"] == method.get.input_data[2].checksum

    def test_method_conversion_v1(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(DIRECTORY)
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
        method.set({"name": "test_method"})
        input_data = {"path": INPUT_DATA_ONESHOT}
        method.add_data(source=input_data)
        schema_scripts = whyqd.parsers.LegacyScript().parse_legacy_method(
            version="1", schema=SCHEMA, source_path=METHOD_SOURCE_V1
        )
        source_data = method.get.input_data[0]
        method.add_actions(schema_scripts, source_data.uuid.hex)
        method.transform(source_data)
        method.save(created_by="Gavin Chait", hide_uuid=True)

    def test_merge_and_build(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(DIRECTORY)
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA)
        method.set({"name": "test_method"})
        input_data = [{"path": d} for d in INPUT_DATA]
        method.add_data(source=input_data)
        # "MERGE < ['key_column'::'source_hex'::'sheet_name', ...]"
        merge_reference = [
            {"source_hex": method.get.input_data[2].uuid.hex, "key_column": "Property ref no"},
            {"source_hex": method.get.input_data[1].uuid.hex, "key_column": "Property Reference Number"},
            {"source_hex": method.get.input_data[0].uuid.hex, "key_column": "Property Reference Number"},
        ]
        merge_terms = ", ".join([f"'{m['key_column']}'::'{m['source_hex']}'" for m in merge_reference])
        merge_script = f"MERGE < [{merge_terms}]"
        method.merge(merge_script)
        schema_scripts = whyqd.parsers.LegacyScript().parse_legacy_method(
            version="1", schema=SCHEMA, source_path=METHOD_SOURCE_V1
        )
        source_data = method.get.working_data
        method.add_actions(schema_scripts, source_data.uuid.hex)
        method.build()
        method.save(created_by="Gavin Chait", hide_uuid=True)

    def test_validate(self, tmp_path):
        DIRECTORY = str(tmp_path) + "/"
        CoreScript().check_path(DIRECTORY)
        METHOD = CoreScript().load_json(SOURCE_DIRECTORY + METHOD_FILE)
        method = whyqd.Method(directory=DIRECTORY, schema=SCHEMA, method=METHOD)
        df = method._get_dataframe(method.get.restructured_data, RESTRUCTURED_DATA)
        checksum = CoreScript().get_data_checksum(df)
        assert method.get.restructured_data.checksum == checksum
        assert method.validate()
