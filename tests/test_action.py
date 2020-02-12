from pathlib import Path

import whyqd as _w
import whyqd.common as _c

filename = "/data/test_action.json"
source = str(Path(__file__).resolve().parent) + filename
data = _c.load_json(source)

class TestAction:

	def test_create(self):
		action = {
			"name": "test_name",
			"type": "string"
		}
		f = _w.Action(**action)
		assert f.name == action["name"]
		assert f.type == action["type"]
		assert f.validates