import whyqd as _w

class TestField:

	def test_create(self):
		f = _w.Field("test_name", "string")
		assert f.name == "test_name"
		assert f.type == "string"
		assert f.validates

	def test_constraints(self):
		f = _w.Field("test_name", "string")
		f.set_constraint("required", True)
		assert f.validates
		assert f.required
		category = [
			{
				"name": "dog",
				"description": "A type of mammal"
			},
			{
				"name": "cat",
				"description": "A different type of mammal"
			},
			{
				"name": "mouse",
				"description": "A small type of mammal"
			}
		]
		f.set_constraint("category", category)
		assert f.constraints["category"] == category

	def test_filters(self):
		f = _w.Field("test_name", "date")
		assert f.validates
		filters = {
			"modifiers": ["LATEST", "AFTER"]
		}
		f.set_constraint("filters", filters)
		filters["field"] = True
		assert f.constraints["filters"] == filters

	def test_all(self):
		settings = {
			"constraints": {
				"required": True,
				"category": [
					{
						"name": "dog",
						"description": "A type of mammal"
					},
					{
						"name": "cat",
						"description": "A different type of mammal"
					},
					{
						"name": "mouse",
						"description": "A small type of mammal"
					}
				]
			}
		}
		f = _w.Field("test_name", "string", **settings)
		assert f.validates
		settings["name"] = "test_name"
		settings["type"] = "string"
		assert f.settings == settings
		settings = {
			"constraints": {
				"filters": {
					"field": True,
					"modifiers": ["LATEST", "AFTER"]
				}
			}
		}
		f = _w.Field("test_name", "date", **settings)
		assert f.validates
		settings["name"] = "test_name"
		settings["type"] = "date"
		assert f.settings == settings
