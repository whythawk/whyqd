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

	def set_filters(self, working_data, filter, date_filter=None):
		# Need to set a date for "AFTER" & "BEFORE"
		pass

	def set_category(self, modifier, working_data):
		# If modifier "-", set [True, False], if "+", get unique terms from that dataframe column
		pass

	def set_task(self, working_data, *action):
		# Sets or updates a task, and sets any required categories
		pass

	def validate_task(self, working_columns, *task):
		"""
		A recursive function testing method structure and that field names are entities of the list
		of `working_columns`. A method should have fields upon which actions are applied, but each
		field may have sub-fields requiring their own actions.

		Parameters
		----------
		working_columns: list
			Permitted column names from `working_data`
		method: list of dicts
			Each dict an element of a `method`, and must start with an `action`
		"""
		# Analyse requirements for this field
		if len(task) < 2 or task[0]["type"] != "action":
			e = "A method must start with an `action` and contain at least one `field`."
			raise ValueError(e)
		action = task[0]
		# Superficial validation check
		for field in task[1:]:
			# Validate that the source column names are actually in the `working_columns`
			if field["type"] == "field" and field["name"] not in working_columns:
				e = "Method field `{}` of type `{}` in action `{}` has invalid column `{}`."
				e = e.format(self._name, self._type, action["name"], field["name"])
				raise ValueError(e)
			# Recurse for any nested fields down the tree
			if field["type"] == "nested":
				try:
					self.validate_method(working_columns, *field["action"])
				except KeyError:
					e = "Method field `{}` of type `{}` in action `{}` has missing nested action."
					e = e.format(self._name, self._type, action["name"])
					raise KeyError(e)
			if not field:
				e = "Method field `{}` of type `{}` in action `{}` has void field."
				e = e.format(self._name, self._type, action["name"])
				raise ValueError(e)
		# Validation of specific action structure
		if action["name"] not in ["ORDER_NEW", "ORDER_OLD", "CALCULATE", "CATEGORISE"]:
			return True
		if action["name"] in ["ORDER_NEW", "ORDER_OLD"]:
			# Requires sets of 3 terms: field, +, date_field
			term_set = 3
		if action["name"] in ["CALCULATE", "CATEGORISE"]:
			# Requires sets of 2 terms: + or -, field
			term_set = 2
		valid = True
		for field in _c.chunks(task[1:], term_set):
			if len(field) != term_set:
				valid = False
			if valid and action["name"] in ["ORDER_NEW", "ORDER_OLD"]:
				if ((field[0]["type"] != "field" and field[0]["type"] != "nested") or
					(field[1]["name"] != "+") or
					(field[2]["type"] != "field" and field[2]["type"] != "nested")):
					valid = False
			if valid and action["name"] in ["CALCULATE", "CATEGORISE"]:
				if ((field[0]["type"] != "modifier") or
					((field[1]["type"] != "field") and (field[1]["type"] != "nested"))):
					valid = False
			if valid and action["name"] == "CATEGORISE":
				if not field[1].get("constraints", {}).get("category"):
					valid = False
				if ((field[0]["name"] == "-") and
					(field[1]["constraints"]["category"] != [True, False])):
					valid = False
				if ((field[0]["name"] == "+") and
					(len(field[1]["constraints"]["category"]) !=
					 len(set(field[1]["constraints"]["category"])))):
					valid = False
			if not valid:
				e = "Method field `{}` of type `{}` in action `{}` has invalid structure."
				e = e.format(self._name, self._type, action["name"], field["name"])
				raise ValueError(e)
		return True

	def validates(self, working_columns):
		"""
		Test action `task` for structure (every action starts with an action `type`), and that
		columns, categories and filters (depending on what is supplied) are valid.

		Parameters
		----------
		working_columns: list
			Permitted column names from `working_data`

		Raises
		------
		ValueError if working data not provided, if names not permitted, or if action not valid

		Returns
		-------
		Bool, True if valid
		"""
		if "task" not in self.settings:
			e = "Method field `{}` of type `{}` has no `methods`.".format(self._name, self._type)
			raise ValueError(e)
		self.validate_task(working_columns, self.settings["task"])
		# Need to validate the filters
		return super().validates