"""
Target Schema
-------------

Define and manage a structural metadata schema as the target for a wrangling process.

Dassie munges input-data into a target schema where automated scripts can perform further cleaning
and validation. Data produced will conform to the schema but are in an interim state. The schema
process is similar to FrictionlessData.io, but without its error-checking and validation components.
"""

import whyqd.common as _c
from whyqd.schema import Field

class Action(Field):

	def __init__(self, **kwargs):
		# If this is initialising default Actions, then the name and type are actions. There will be
		# no 'actions' field. Else they are the Field name and type from the Schema
		_name = kwargs["name"]
		del kwargs["name"]
		_type = kwargs["type"]
		del kwargs["type"]
		if not kwargs.get("action", {}).get("type") and kwargs.get("validate", True):
			e = "Missing type for Action initialisation"
			TypeError(e)
		super().__init__(_name, _type, **kwargs)
		if not kwargs.get("action", {}):
			self.action_type = self._type
		else:
			self.action_type = self.field_settings["actions"][0]["type"]
		self.default_settings = _c.get_field_settings(field_type, "actions")

	def validates(self, working_fields=None, working_categories=None):
		"""
		After `merge`, need to test if any field actions are still valid. Update accordingly and
		return the updated method.
		"""
		actions = [{"data": item,
					"order": "action_{}".format(index),
					"fixed": False,
					"colour": "-red",
					"type": "action"}
			for index, item in enumerate(get_settings(get="ACTIONS")["fields"])]
		# https://stackoverflow.com/a/8653568
		this_action = {
			"default": next(item for item in actions if item["data"]["name"] == "ORDER"),
			"calculate": next(item for item in actions if item["data"]["name"] == "CALCULATE"),
			"categorise": next(item for item in actions if item["data"]["name"] == "CATEGORISE")
		}
		schema = {item["name"]: [this_action["categorise"] if item.get("constraints", {}).get("category")
								 else this_action["calculate"] if item.get("type") == "number"
								 else this_action["default"]]
				  for item in get_settings()["fields"] if item["name"] != "la_code"}
		new_fields = []
		for field in method["fields"]:
			if field["data"]["name"] == "la_code":
				continue
			validated_field = get_fields_structure(df, *field["fields"])
			if not validated_field:
				validated_field = schema[field["data"]["name"]]
			field["fields"] = validated_field
			new_fields.append(field)
		method["fields"] = new_fields
		return super().validates