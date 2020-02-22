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
				if term == "value" and not _c.get_field_type(field[i]):
					# Special case for NEW actions where the field can be anything
					return False
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