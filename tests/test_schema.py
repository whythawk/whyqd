from pathlib import Path

import whyqd as _w
import whyqd.common as _c

filename = "/test_schema.json"
source = str(Path(__file__).resolve().parent) + filename
data = _c.load_json(source)

class TestSchema:

	def test_create(self):
		s = _w.Schema()
		field = {
			"name": "test_field",
			"type": "string",
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
		s.set_details(name="test_schema")
		s.set_field(**field)
		assert s.validates

	def test_load(self):
		s = _w.Schema(source)
		assert s.validates
		assert s.settings == data

	def test_build(self):
		s = _w.Schema()
		details = {
			"name": data["name"],
			"title": data["title"],
			"description": data["description"]
		}
		s.set_details(**details)
		for field in data["fields"]:
			s.set_field(**field)
		assert s.validates
		assert s.settings == data