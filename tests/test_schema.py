from pathlib import Path
import json

import whyqd as qd
from whyqd.parsers import CoreParser

DIRECTORY = Path(__file__).resolve().parent / "data"
DATA_MODEL = {"SINGLE": CoreParser().load_json(source=DIRECTORY / "raw_E06000044_014_0.data")}
SCHEMA_SOURCE = DIRECTORY / "test_schema.schema"
SCHEMA_DATA = {
    "SOURCE": CoreParser().load_json(source=SCHEMA_SOURCE),
    "DERIVED": CoreParser().load_json(source=DIRECTORY / "test_derived_schema.schema"),
}


class TestSchema:
    def test_create(self):
        s = qd.SchemaDefinition()
        field: qd.models.FieldModel = {
            "name": "test_field",
            "type": "string",
            "constraints": {
                "required": True,
                "category": [
                    {"name": "dog", "description": "A type of mammal"},
                    {"name": "cat", "description": "A different type of mammal"},
                    {"name": "mouse", "description": "A small type of mammal"},
                ],
            },
        }
        schema: qd.models.SchemaModel = {
            "name": "test_schema",
        }
        s.set(schema=schema)
        s.fields.add(term=field)

    def test_load(self):
        s = qd.SchemaDefinition(source=SCHEMA_SOURCE)
        d = s.exclude_uuid(model=s.get)
        D = s.exclude_uuid(model=SCHEMA_DATA["SOURCE"])
        d.pop("version", None)
        D.pop("version", None)
        assert json.dumps(d) == json.dumps(D)

    def test_build(self):
        s = qd.SchemaDefinition()
        details = {
            "name": SCHEMA_DATA["SOURCE"]["name"],
            "title": SCHEMA_DATA["SOURCE"]["title"],
            "description": SCHEMA_DATA["SOURCE"]["description"],
        }
        s.set(schema=details)
        s.fields.add_multi(terms=SCHEMA_DATA["SOURCE"]["fields"])
        # also this https://github.com/samuelcolvin/pydantic/issues/1283#issuecomment-594041870
        # foo_excludes = {idx: {"id"} for idx in range(len(my_bar.foos))}
        # my_bar.dict(exclude={"foos": foo_excludes})
        # https://pydantic-docs.helpmanual.io/usage/exporting_models/#advanced-include-and-exclude
        schema_exclude = {
            f_idx: (
                {
                    "uuid": ...,
                    "constraints": {"category": {c_idx: {"uuid"} for c_idx in range(len(f.constraints.category))}},
                }
                if f.constraints
                else {"uuid"}
            )
            for f_idx, f in enumerate(s.get.fields)
        }
        d = s.get.dict(
            by_alias=True, exclude_defaults=True, exclude_none=True, exclude={"uuid": ..., "fields": schema_exclude}
        )
        # d = s.exclude_uuid(model=s.get)
        D = s.exclude_uuid(model=SCHEMA_DATA["SOURCE"])
        d.pop("version", None)
        D.pop("version", None)
        assert json.dumps(d) == json.dumps(D)

    def test_derive(self):
        s = qd.SchemaDefinition()
        s.derive_model(data=DATA_MODEL["SINGLE"])
        d = s.get_json(hide_uuid=True)
        D = s.exclude_uuid(model=SCHEMA_DATA["DERIVED"])
        D["name"] = s.get.name
        D.pop("version", None)
        assert d == json.dumps(D)
