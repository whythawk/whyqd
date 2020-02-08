import whyqd as _w
import whyqd.common as _c

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