from pathlib import Path

import whyqd
from whyqd.transform.parsers import CoreScript

filename = "/data/test_schema.json"
source = str(Path(__file__).resolve().parent) + filename
data = CoreScript().load_json(source=source)


class TestSchema:
    def test_create(self):
        s = whyqd.Schema()
        field: whyqd.FieldModel = {
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
        schema: whyqd.SchemaModel = {
            "name": "test_schema",
        }
        s.set(schema=schema)
        s.add_field(field=field)

    def test_load(self):
        s = whyqd.Schema(source=source)
        d = s.get.dict(by_alias=True, exclude_defaults=True, exclude_none=True, exclude_unset=True)
        assert d == data

    def test_build(self):
        s = whyqd.Schema()
        details = {"name": data["name"], "title": data["title"], "description": data["description"]}
        s.set(schema=details)
        for field in data["fields"]:
            s.add_field(field=field)
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
        assert d == data
