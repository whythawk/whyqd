from pathlib import Path

import whyqd as _w
from whyqd.core import common as _c

filename = "/data/test_schema.json"
source = str(Path(__file__).resolve().parent) + filename
data = _c.load_json(source)


class TestSchema:
    def test_create(self):
        s = _w.Schema()
        field: _w.FieldModel = {
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
        schema: _w.SchemaModel = {
            "name": "test_schema",
        }
        s.set(schema)
        s.add_field(field)

    def test_load(self):
        s = _w.Schema(source=source)
        d = s.get.dict(by_alias=True, exclude_defaults=True, exclude_none=True)
        d.pop("uuid", None)
        assert d == data

    def test_build(self):
        s = _w.Schema()
        details = {"name": data["name"], "title": data["title"], "description": data["description"]}
        s.set(schema=details)
        for field in data["fields"]:
            s.add_field(field=field)
        d = s.get.dict(by_alias=True, exclude_defaults=True, exclude_none=True)
        d.pop("uuid", None)
        assert d == data
