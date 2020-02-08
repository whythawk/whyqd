"""
Dassie Command Interface
------------------------

Commands include:

"""

import os, io
import whyqd.common as _c

def get_field_types():
	fields = _get_schema_settings()["fields"]
	return [f["type"] for f in fields]

def get_field_constraints(field_type):
	constraints = _get_field_settings(field_type)["constraints"]
	return constraints["properties"].keys()

def get_field_format(field_type):
	return _get_field_settings(field_type).get("format", {})

# Internal functions

def _get_schema_settings():
	"""
	Return the complete json schema for target settings as a dict.
	"""
	filename = "default_fields.json"
	source = os.path.join(_c.get_path(), "settings", filename)
	return _c.get_or_set_json(source)

def _get_field_settings(field_type):
	fields = _get_schema_settings()["fields"]
	for f in fields:
		if f["type"] == field_type:
			return f
	return {}