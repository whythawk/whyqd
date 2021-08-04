import whyqd as _w

schema = {}


class TestField:
    def test_create(self):
        f = {"name": "test_name", "type": "string"}
        f = _w.FieldModel(**f)
        assert f.name == "test_name"
        assert f.type_field == "string"

    def test_update_field(self):
        s = _w.Schema()
        schema: _w.SchemaModel = {
            "name": "test_schema",
        }
        s.set(schema)
        f = {"name": "test_name", "type": "string"}
        s.add_field(f)
        s.remove_field("test_name")
        s.add_field(f)
        f = {"name": "test_name", "type": "number"}
        s.set_field(f)
        assert s.get_field("test_name").type_field == "number"

    def test_constraints(self):
        s = _w.Schema()
        schema: _w.SchemaModel = {
            "name": "test_schema",
        }
        s.set(schema)
        f = {"name": "test_name", "type": "string"}
        s.add_field(f)
        c: _w.ConstraintModel = {"required": True}
        s.set_field_constraints("test_name", constraints=c)
        f = s.get_field("test_name")
        assert f.constraints.required
        category = [
            {"name": "dog", "description": "A type of mammal"},
            {"name": "cat", "description": "A different type of mammal"},
            {"name": "mouse", "description": "A small type of mammal"},
        ]
        c: _w.ConstraintModel = {"enum": category}
        s.set_field_constraints("test_name", c)
        f = s.get_field_constraints("test_name")
        assert f.category == category
