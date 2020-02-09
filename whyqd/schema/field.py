"""
Target Fields
-------------

Definitions and customisation for canonical destination fields forming the target schema.
"""
from copy import deepcopy

import whyqd.common as _c

class Field:
	"""
	Field definitions for a schema. A list of fields defines a schema.  Minimum arguments to create
	a field are a `name` and a `type`.
	"""
	def __init__(self, name, field_type, **kwargs):
		self.common_settings = _c.get_settings("schema")["common"]
		self.default_settings = _c.get_field_settings(field_type)
		self.default_constraints = self.default_settings["constraints"]["properties"]
		self.default_filters = _c.get_settings("filters")["filters"]["modifiers"]
		self.default_format = self.default_settings.get("format", {})
		self._name = "_".join(name.split(" ")).lower()
		self._type = field_type
		self.field_settings = {
			"name": self._name,
			"type": self._type,
			"constraints": {}
		}
		kwargs = deepcopy(kwargs)
		if kwargs and kwargs.get("validate", True):
			self.set_all(**kwargs)
		if kwargs and not kwargs.get("validate", True):
			del kwargs["validate"]
			self.field_settings = {**self.field_settings, **kwargs}

	def __repr__(self):
		"""
		Returns the string representation of the model.
		"""
		return "Field: `{}` of type `{}`".format(self._name, self._type)

	@property
	def name(self):
		"""
		Field name

		Returns
		-------
			str: field name
		"""
		return self.field_settings.get("name")

	@property
	def type(self):
		"""
		Field type

		Returns
		-------
			str: field type
		"""
		return self.field_settings.get("type")

	@property
	def format(self):
		"""
		Field format

		Returns
		-------
			str: field format
		"""
		return self.field_settings.get("format", "default")

	@property
	def required(self):
		"""
		Field required

		Returns
		-------
			bool: true if required
		"""
		return self.field_settings["constraints"].get('required', False)

	@property
	def constraints(self):
		"""
		Field constraints

		Returns
		-------
			dict: dict of field constraints
		"""
		return deepcopy(self.field_settings.get('constraints', {}))

	@property
	def settings(self):
		"""
		Field settings

		Returns
		-------
			dict: settings
		"""
		response = deepcopy(self.field_settings)
		# Remove empty category fields if none used
		if not response["constraints"]: del response["constraints"]
		return response

	@property
	def validates(self):
		"""
		Field validates with minimum required keys

		Returns
		-------
			bool: True for has all keys
		"""
		if not all(key in self.settings for key in self.default_settings["required"]):
			e = "Required `field` parameters not present for `{}`.".format(self._name)
			raise ValueError(e)
		return True

	def set_constraint(self, constraint, value):
		"""
		Set field constraints. User-defined constraints will be automatically passed through, as
		long as the constraints validate.

		Raises
		------
			KeyError: if constraint is not permitted in this field
			ValueError: if value is out of range of that permitted by this constraint
		"""
		if constraint not in self.default_constraints:
			e = "`{}` not permitted in list of constraints".format(constraint)
			raise KeyError(e)
		value = deepcopy(value)
		constraint_type = _c.get_field_type(value)
		# Check for boolean constraints
		if (constraint in ["unique", "required"] and constraint_type != "boolean"):
			e = "`{}` not a permitted value type for `{}`".format(constraint_type, constraint)
			raise ValueError(e)
		# Check for appropriate minimum and maximum constraints
		if constraint in ["minimum", "maximum"]:
			if (self.default_constraints[constraint]["type"] in ["string", "integer", "number"] and
				constraint_type not in ["integer", "number"]):
				e = "Constraint `{}` should be an integer or number.".format(constraint)
				raise ValueError(e)
			if (self.default_constraints[constraint]["type"] in ["string", "integer"] and
				constraint_type == "number"):
				e = "Constraint `{}` should be an integer".format(constraint)
				raise ValueError(e)
		if constraint == "category":
			# Category constraints are very specific
			if not (isinstance(value, list) and
					isinstance(value[0], dict) and
					all(["name" in v for v in value])):
				e = "Terms defining this category constraint must be presented as a list of dicts with keys `name` & (optional) `description`"
				raise KeyError(e)
			# Each term is an object with `name`/`description`, where`name` defined by a `type`
			# Test if terms are of the required type
			terms = [t["name"] for t in value]
			# Not sure what my intention is here. I mean, names are going to be strings, right?
			# Maybe need to specify the types in the array somewhere?
			# leaving it for now...
			#required_type = self.default_constraints["category"]["terms"]["type"]
			#if not all([_c.get_field_type(t) == required_type for t in terms]):
			#	e = "`{}` are not all of type `{}`".format(terms, required_type)
			#	raise ValueError(e)
			# Test if terms are unique
			if len(terms) < len(set(terms)):
				e = "Category list `{}` has duplicate terms".format(value)
				raise ValueError(e)
		if constraint == "valueType":
			# This is to set the `type` for the contents of an array
			if self._type != "array":
				import warnings
				e = "`valueType` will be ignored for fields which are not type `array`."
				warnings.warn(e)
			if value not in self.default_constraints["valueType"]["type"]:
				e = "valueType `{}` not one of `{}`".format(value, self.default_constraints["valueType"]["type"])
				raise ValueError(e)
		if constraint == "filters":
			# This is a user-defined constraint which can be applied to any date-related field type
			if not value.get("modifiers"):
				e = "`{}` has missing `modifiers` in `filters`".format(constraint)
				raise KeyError(e)
			if "field" in value and not (isinstance(value["field"], str) or
										 isinstance(value["field"], bool)):
				e = "Filter field `{}` is not of type `string` or `True`".format(value["field"])
				raise KeyError(e)
			if value.get("field", "foreignKey") == "foreignKey":
				value["field"] = True
		self.field_settings["constraints"][constraint] = value

	def set_missing(self, value):
		"""
		Set default value for missing values.

		Raises
		------
			ValueError: if value is out of range of that permitted by this field
		"""
		value = deepcopy(value)
		_type = _c.get_field_type(value)
		if value != "" or _type != self.field_settings["type"]:
			e = "`{}` not a permitted value type for `{}`".format(value, self.field_settings["type"])
			raise ValueError(e)
		self.field_settings["missing"] = value

	def set_format(self, value="default"):
		"""
		Set field format.

		Raises
		------
			ValueError: if value is not permitted for this field
		"""
		value = deepcopy(value)
		_type = _c.get_field_type(value)
		if value not in self.default_format.get("category", ["default"]):
			e = "`{}` not a permitted format".format(value)
			raise ValueError(e)
		self.field_settings["format"] = value

	def set_foreign_key(self, value):
		"""
		Set foreign_key value.

		Raises
		------
			TypeError: if value is not a bool
		"""
		value = deepcopy(value)
		if not isinstance(value, bool):
			e = "`{}` is not boolean".format(value)
			raise TypeError(e)
		if value:
			self.field_settings["foreignKey"] = True
		elif "foreignKey" in self.field_settings:
			del self.field_settings["foreignKey"]

	def set_all(self, **kwargs):
		"""
		Set all keys and values for this field. Note, this also permits updating of existing
		`name`, but not `type` (which would cause a disaster).

		Arguments
		---------
			kwargs: dict of all the permitted key: value pairs for this field

		Raises
		------
			ValueError: if `name` contains spaces
			TypeError: if string terms are not strings
		"""
		kwargs = deepcopy(kwargs)
		if "type" in kwargs:
			e = "Warning: You are not permitted to change an existing Field type. Better to delete & start again."
			print(e)
		for key, value in kwargs.items():
			if key == "type":
				# Ignore any attempts to change `type`
				continue
			if key == "foreignKey":
				self.set_foreign_key(value)
				continue
			if key in self.common_settings:
				if not isinstance(value, str):
					e = "`{}` is not a string".format(value)
					raise TypeError(e)
				if key == "name" and " " in value:
					e = "Name `{}` not permitted to have space characters".format(value)
					raise ValueError(e)
				self.field_settings[key] = value
				continue
			if key == "format":
				self.set_format(value)
				continue
			if key == "missing":
				self.set_missing(value)
				continue
			# Anything else is a constraint
			if key == "constraints" and isinstance(value, dict):
				for k, v in value.items():
					self.set_constraint(k, v)