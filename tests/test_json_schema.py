# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import whyqd as qd
from whyqd.config.settings import settings
from whyqd.parsers.format import FormatParser

from tests import test_definition_slots as slots

DIRECTORY = Path(__file__).resolve().parent / "data"
FORMATS = FormatParser()
KINDS = {
    ".schema": ("schema", qd.SchemaDefinition, "source"),
    ".crosswalk": ("crosswalk", qd.CrosswalkDefinition, "crosswalk"),
    ".data": ("datasource", qd.DataSourceDefinition, "source"),
}
DEFINITIONS = sorted(p for p in DIRECTORY.iterdir() if p.suffix.lower() in KINDS)


def validator(kind: str, format: str | None = None) -> Draft202012Validator:
    schema = FORMATS.json_schema(kind=kind, format=format)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def errors(kind: str, definition: dict, format: str | None = None) -> list[str]:
    return [f"{e.json_path}: {e.message}" for e in validator(kind, format).iter_errors(definition)]


def as_list(definition: dict | list[dict]) -> list[dict]:
    return definition if isinstance(definition, list) else [definition]


class TestJsonSchemas:
    @pytest.mark.parametrize("kind", list(FORMATS.KINDS))
    def test_current_in_step_with_the_models(self, kind):
        assert FORMATS.json_schema(kind=kind) == FORMATS.generate_json_schema(kind=kind), (
            "The models changed: regenerate with `FormatParser().save_json_schemas()` and review the difference."
        )

    @pytest.mark.parametrize("format", settings.FORMAT_VERSIONS)
    @pytest.mark.parametrize("kind", list(FORMATS.KINDS))
    def test_valid_and_identified(self, kind, format):
        schema = FORMATS.json_schema(kind=kind, format=format)
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://w3id.org/whyqd/formats/{format}/{kind}.json"

    def test_unknown_kind_refused(self):
        with pytest.raises(ValueError, match="`method` is not a kind"):
            FORMATS.json_schema(kind="method")

    def test_unknown_format_refused(self):
        with pytest.raises(ValueError, match="`1.5`"):
            FORMATS.json_schema(kind="schema", format="1.5")


class TestStoredDefinitions:
    @pytest.mark.parametrize("path", DEFINITIONS, ids=lambda p: p.name)
    def test_1x_as_stored(self, path):
        kind = KINDS[path.suffix.lower()][0]
        for definition in as_list(json.loads(path.read_text(encoding="utf-8"))):
            assert errors(kind, definition, "1.x") == []

    @pytest.mark.parametrize("path", DEFINITIONS, ids=lambda p: p.name)
    def test_saved_as_2_0(self, path):
        kind, definition, keyword = KINDS[path.suffix.lower()]
        for written in as_list(json.loads(definition(**{keyword: path}).get_json())):
            assert errors(kind, written) == []

    @pytest.mark.parametrize("path", DEFINITIONS, ids=lambda p: p.name)
    def test_saved_as_1x(self, path):
        kind, definition, keyword = KINDS[path.suffix.lower()]
        for written in as_list(json.loads(definition(**{keyword: path}).get_json(format="1.x"))):
            assert errors(kind, written, "1.x") == []

    def test_run_transform_as_2_0(self):
        transform = qd.TransformDefinition(
            crosswalk=DIRECTORY / "test_crosswalk.crosswalk", data_source=DIRECTORY / "raw_E06000044_014_0.data"
        )
        transform.process()
        assert errors("transform", json.loads(transform.get_json())) == []

    def test_every_new_part_as_2_0(self):
        source = slots.data_source(dialect=slots.DIALECT, profile=slots.PROFILE)
        assert errors("datasource", json.loads(qd.DataSourceDefinition(source=source).get_json())) == []
        steps = {slots.RENAME: {"reason": slots.REASON}, slots.CATEGORISE: {"correspondence": slots.REFERENCE}}
        crosswalk = slots.crosswalk(steps=steps, termList=slots.REFERENCE, code="EPR")
        crosswalk["schemaSource"]["fields"][0]["policy"] = slots.POLICIES[0]
        assert errors("crosswalk", json.loads(qd.CrosswalkDefinition(crosswalk=crosswalk).get_json())) == []

    def test_wrong_format_version_fails(self):
        written = json.loads(qd.SchemaDefinition(source=DIRECTORY / "test_schema.schema").get_json())
        assert errors("schema", written | {"formatVersion": "3.0"})
        written.pop("formatVersion")
        assert errors("schema", written)
