# SPDX-License-Identifier: BSD-3-Clause
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import whyqd as qd
from whyqd.config.settings import settings

DIRECTORY = Path(__file__).resolve().parent / "data"
KINDS = {
    ".schema": (qd.SchemaDefinition, "source"),
    ".crosswalk": (qd.CrosswalkDefinition, "crosswalk"),
    ".data": (qd.DataSourceDefinition, "source"),
}
DEFINITIONS = sorted(p for p in DIRECTORY.iterdir() if p.suffix.lower() in KINDS)
DATA_SOURCES = [p for p in DEFINITIONS if p.suffix == ".data"]


def load(path: Path):
    kind, keyword = KINDS[path.suffix.lower()]
    return kind(**{keyword: path})


def as_json(output: str | list[str]) -> dict | list[dict]:
    return [json.loads(o) for o in output] if isinstance(output, list) else json.loads(output)


def as_written(original, written):
    """The original as 1.x writes it: empty slots left out unless kept, and UUIDs where the original hid them."""
    if isinstance(original, list):
        return [as_written(o, w) for o, w in zip(original, written, strict=True)]
    if not isinstance(original, dict):
        return original
    kept = {k: as_written(v, written.get(k)) for k, v in original.items() if k in written or v not in (None, [], {})}
    if "uuid" not in original and "uuid" in written:
        kept["uuid"] = written["uuid"]
    return kept


def checksum(value: str, content: str) -> dict:
    return {"algorithm": "BLAKE2b-512", "checksumValue": value, "content": content}


class TestFormatVersion:
    def test_known_formats(self):
        assert settings.FORMAT_VERSIONS == ("1.x", "2.0")

    @pytest.mark.parametrize("path", DEFINITIONS, ids=lambda p: p.name)
    def test_1x_saves_as_read(self, path):
        original = json.loads(path.read_text(encoding="utf-8"))
        written = as_json(load(path).get_json(format="1.x"))
        assert "formatVersion" not in written
        assert written == as_written(original, written)

    def test_1x_save_keeps_a_missing_header(self):
        # `header: 0` is the 1.x default, so a file without a header row must say so
        written = as_json(load(DIRECTORY / "test_cthulu_source.data").get_json(format="1.x"))
        assert written["header"] is None

    @pytest.mark.parametrize("path", DEFINITIONS, ids=lambda p: p.name)
    def test_saves_upgraded_by_default(self, path):
        written = as_json(load(path).get_json())
        for model in written if isinstance(written, list) else [written]:
            assert model["formatVersion"] == "2.0"

    @pytest.mark.parametrize("path", DATA_SOURCES, ids=lambda p: p.name)
    def test_1x_checksum_upgrades_as_table_1x(self, path):
        original = json.loads(path.read_text(encoding="utf-8"))
        written = as_json(load(path).get_json())
        assert "checksum" not in written
        assert written["checksums"] == [checksum(original["checksum"], "table-1x")]

    def test_embedded_schema_names_its_content(self):
        import rfc8785

        written = as_json(load(DIRECTORY / "test_crosswalk.crosswalk").get_json())
        for key in ["schemaSource", "schemaDestination"]:
            schema = written[key]
            assert "formatVersion" not in schema
            content = {k: v for k, v in schema.items() if k not in {"version", "checksums"}}
            value = hashlib.blake2b(rfc8785.dumps(content)).hexdigest()
            assert schema["checksums"] == [checksum(value, "definition")]

    @pytest.mark.parametrize("path", DEFINITIONS, ids=lambda p: p.name)
    def test_upgraded_reads_back(self, path, tmp_path):
        written = load(path).get_json()
        saved = tmp_path / path.name
        saved.write_text(json.dumps(as_json(written)), encoding="utf-8")
        assert as_json(load(saved).get_json()) == as_json(written)

    @pytest.mark.parametrize("version", ["2.1", "3.0"])
    def test_newer_format_refused(self, version):
        model = json.loads((DIRECTORY / "test_schema.schema").read_text(encoding="utf-8"))
        model["formatVersion"] = version
        with pytest.raises(ValueError, match=rf"{version}.*1\.x.*2\.0"):
            qd.SchemaDefinition(source=model)

    def test_unknown_format_on_save_refused(self):
        with pytest.raises(ValueError, match=r"1\.5.*1\.x.*2\.0"):
            load(DIRECTORY / "test_schema.schema").get_json(format="1.5")

    @pytest.mark.parametrize("path", DATA_SOURCES, ids=lambda p: p.name)
    def test_empty_attributes_left_out(self, path):
        assert "attributes" not in as_json(load(path).get_json())


def schema(fields: list[dict], format: str | None = None) -> qd.SchemaDefinition:
    definition = qd.SchemaDefinition()
    definition.set(schema={"name": "fields", "fields": fields} | ({"formatVersion": format} if format else {}))
    return definition


class TestFieldTypesAndBounds:
    def test_1x_time_is_a_duration(self):
        written = as_json(schema([{"name": "a", "type": "time"}]).get_json())
        assert written["fields"][0]["type"] == "duration"

    def test_1x_string_bounds_are_lengths(self):
        fields = [
            {"name": "a", "type": "string", "constraints": {"minimum": 2, "maximum": 9}},
            {"name": "b", "type": "number", "constraints": {"minimum": 0, "maximum": 9}},
        ]
        written = as_json(schema(fields).get_json())
        assert written["fields"][0]["constraints"] == {"minLength": 2, "maxLength": 9}
        assert written["fields"][1]["constraints"] == {"minimum": 0, "maximum": 9}

    def test_1x_save_writes_them_back(self):
        fields = [
            {"name": "a", "type": "time"},
            {"name": "b", "type": "string", "constraints": {"minimum": 2, "maximum": 9}},
        ]
        written = as_json(schema(fields).get_json(format="1.x"))
        assert [{k: f[k] for k in f if k != "uuid"} for f in written["fields"]] == fields

    def test_time_of_day_reads(self):
        written = as_json(schema([{"name": "a", "type": "time"}], format="2.0").get_json())
        assert written["fields"][0]["type"] == "time"

    @pytest.mark.parametrize(
        "field, refusal",
        [
            ({"name": "a", "type": "time"}, "time of day"),
            ({"name": "a", "type": "number", "constraints": {"minLength": 1}}, "length of a `number`"),
            ({"name": "a", "type": "string", "constraints": {"minLength": 1, "maximum": 3}}, "value and its length"),
        ],
        ids=["time of day", "length of a number", "value and length"],
    )
    def test_1x_save_refuses_what_it_cannot_hold(self, field, refusal):
        with pytest.raises(ValueError, match=refusal):
            schema([field], format="2.0").get_json(format="1.x")

    def test_length_bounds_ordered(self):
        with pytest.raises(ValueError, match="maxLength"):
            schema([{"name": "a", "type": "string", "constraints": {"minLength": 5, "maxLength": 2}}], format="2.0")


class TestVerify1x:
    @pytest.mark.parametrize("path", DATA_SOURCES, ids=lambda p: p.name)
    def test_verifies_and_adds_byte_hash(self, path):
        original = json.loads(path.read_text(encoding="utf-8"))
        datasource = load(path)
        assert datasource.validate()
        file_hash = hashlib.blake2b(Path(original["path"]).read_bytes()).hexdigest()
        assert as_json(datasource.get_json())["checksums"] == [
            checksum(original["checksum"], "table-1x"),
            checksum(file_hash, "bytes"),
        ]

    def test_1x_save_after_verifying_keeps_table_1x(self):
        path = DIRECTORY / "test_portsmouth_source.data"
        original = json.loads(path.read_text(encoding="utf-8"))
        datasource = load(path)
        datasource.validate()
        written = as_json(datasource.get_json(format="1.x"))
        assert written["checksum"] == original["checksum"]
        assert "checksums" not in written

    def test_1x_save_refused_without_table_1x(self):
        model = json.loads((DIRECTORY / "test_portsmouth_source.data").read_text(encoding="utf-8"))
        del model["checksum"]
        file_hash = hashlib.blake2b(Path(model["path"]).read_bytes()).hexdigest()
        model |= {"formatVersion": "2.0", "checksums": [checksum(file_hash, "bytes")]}
        with pytest.raises(ValueError, match="checksums"):
            qd.DataSourceDefinition(source=model).get_json(format="1.x")

    def test_without_extra_names_it(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "whyqd.parsers.v1", None)
        with pytest.raises(ImportError, match=r"whyqd\[verify-1x\]"):
            load(DIRECTORY / "test_portsmouth_source.data").validate()


class TestDefinitionsOnly:
    def test_loading_definitions_imports_no_pandas(self, tmp_path):
        crosswalk = load(DIRECTORY / "test_crosswalk.crosswalk")
        datasource = load(DIRECTORY / "test_portsmouth_source.data")
        transform = qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get)
        saved = tmp_path / "test.transform"
        saved.write_text(transform.get_json(), encoding="utf-8")
        script = (
            "import sys, whyqd as qd\n"
            f"qd.SchemaDefinition(source={str(DIRECTORY / 'test_schema.schema')!r})\n"
            f"qd.CrosswalkDefinition(crosswalk={str(DIRECTORY / 'test_crosswalk.crosswalk')!r})\n"
            f"qd.DataSourceDefinition(source={str(DIRECTORY / 'test_portsmouth_source.data')!r})\n"
            f"qd.TransformDefinition(transform={str(saved)!r})\n"
            "print(sorted(m for m in ('pandas', 'numpy', 'pyarrow') if m in sys.modules))\n"
        )
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
        assert result.stdout.strip() == "[]"
