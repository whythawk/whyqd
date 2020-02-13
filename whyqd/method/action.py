"""
Actions
-------

Definitions and validation for actions anchoring structures in methods.

Key functions are:

  - Validate an action exists
  - Specify any modifiers
  - Validate action structure
"""
from copy import deepcopy
import whyqd.common as _c

class Action:

	def __init__(self, **action):
		if not action.get("name") and action.get("validate", True):
			e = "Missing type for Action initialisation"
			TypeError(e)
		if action.get("validate", True):
			valid = False
			for valid_action in _c.get_settings("actions")["fields"]:
				if valid_action["name"] == action["name"]:
					action = valid_action
					valid = True
					break
			if not valid:
				e = "Action `{}` is not a valid term.".format(action["name"])
				raise ValueError(e)
		action.pop("validate", None)
		self.action_settings = deepcopy(action)
		self.name = self.action_settings.get("name")
		self.title = self.action_settings.get("title")
		self.description = self.action_settings.get("description")
		self.default_structure = {
			"field": [f["type"] for f in _c.get_settings("schema")["fields"]],
			"modifier": self.modifier_names
		}

	@property
	def modifier_names(self):
		if "modifiers" in self.action_settings:
			return [modifier["name"] for modifier in self.action_settings["modifiers"]]
		return []

	def has_modifier(self, term):
		for modifier in self.action_settings.get("modifiers", []):
			if modifier["name"] == term:
				return True
		return False

	def get_modifier(self, term):
		for modifier in self.action_settings.get("modifiers", []):
			if modifier["name"] == term:
				return deepcopy(modifier)
		return {}

	def has_valid_structure(self, working_columns, structure):
		"""
		Traverses a list defined by `*structure`, ensuring that the terms conform to that action's
		default structural requirements. Nested structures are permitted. Note that the
		responsibility for digging in to the nested structures lies with the calling function.

		The format for defining a `structure` is as follows::

			[action, column_name, [action, column_name]]

		e.g.::

			["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

		A calling function would specify::

			Action.has_valid_structure(working_columns, *structure[1:])

		Parameters
		----------
		working_columns: list
			List of valid terms from the working data columns.
		structure: list
			Each structure list must conform to the requirements for that action. Nested actions
			defined by nested lists.

		Returns
		-------
		bool, True if valid
		"""
		if not structure:
			e = "A structure must contain at least one `field`."
			raise ValueError(e)
		term_set = len(self.action_settings.get("structure", [1]))
		for field in _c.chunks(structure, term_set):
			if len(field) != term_set:
				return False
			for i, term in enumerate(self.action_settings["structure"]):
				if term == "field" and isinstance(field[i], list):
					# The calling function needs to handle recursion through the list
					continue
				if term == "field" and self.name == "NEW":
					# Special case for NEW actions where the field can be anything
					# TODO: some sort of validation here ... test for type, maybe a dict?
					continue
				if term == "field" and field[i] not in working_columns:
					return False
				if term == "modifier" and field[i] not in self.default_structure[term]:
					return False
		return True

	@property
	def settings(self):
		"""
		Action settings

		Returns
		-------
		dict: settings
		"""
		return deepcopy(self.action_settings)

	def validate_structure(self, working_columns, *structure):
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
		if len(structure) < 2 or structure[0]["type"] != "action":
			e = "A method must start with an `action` and contain at least one `field`."
			raise ValueError(e)
		action = structure[0]
		# Superficial validation check
		for field in structure[1:]:
			# Validate that the source column names are actually in the `working_columns`
			if field["type"] in self.default_field_types and field["name"] not in working_columns:
				e = "Method field `{}` of type `{}` in action `{}` has invalid column `{}`."
				e = e.format(self._name, self._type, action["name"], field["name"])
				raise ValueError(e)
			# Recurse for any nested fields down the tree
			if field["type"] == "nested":
				try:
					self.validate_structure(working_columns, *field["action"])
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
		for field in _c.chunks(structure[1:], term_set):
			if len(field) != term_set:
				valid = False
			if valid and action["name"] in ["ORDER_NEW", "ORDER_OLD"]:
				if ((field[0]["type"] not in self.default_field_types + ["nested"]) or
					(field[1]["name"] != "+") or
					(field[2]["type"] not in self.default_field_types + ["nested"])):
					valid = False
			if valid and action["name"] in ["CALCULATE", "CATEGORISE"]:
				if ((field[0]["type"] != "modifier") or
					(field[1]["type"] not in self.default_field_types + ["nested"])):
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
		Test action `structure` for structure (every action starts with an action `type`), and that
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
		if "structure" not in self.settings:
			e = "Method field `{}` of type `{}` has no `methods`.".format(self._name, self._type)
			raise ValueError(e)
		self.validate_structure(working_columns, self.settings["structure"])
		# Need to validate the filters
		return super().validates