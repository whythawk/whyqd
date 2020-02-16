"""
.. module:: schema
   :synopsis: Create and manage a target data schema.

.. moduleauthor:: Gavin Chait <github.com/turukawa>

Schema
======

Creating a `schema` is the first part of the wrangling process. Your schema defines the structural
metadata target for your wrangling process. This is not the format your input data arrive in, but
it is what you require it to look like when you're done.

Your schema sets the requirements, constraints and sensible defaults available for creating each
`method` that will describe the process for wrangling input data into the fields defined by the
schema. It can be reused to create multiple `methods`. Once complete, automated scripts can perform
further cleaning and validation.

In simple terms, the columns in an input CSV or Excel-file will be restructured into new columns
defined by the fields in your schema. These target fields are likely to be those in your database,
or in your analytical software. Until your input data conform to this structure, you can't do your
real work.

Minimum valid requirements
--------------------------

A minimum valid schema requires a `name` to identify the schema, and a single, minimally-valid
`field` containing a `name` and `type`::

	{
	  "name": "A simple name",
	  "fields": [
		{
			"name": "Field name, e.g. 'column_name'",
			"type": "Valid data type, e.g. 'string', 'number'"
		}
	  ]
	}

Everything else is optional, unless specifically required by that field-type.

Schema descriptors
------------------

Schema terms include:

`name`
^^^^^^
This is a required term. Spaces will be replaced with `_` and the string will be lowercased.

`title`
^^^^^^^
A human-readable version of the schema name.

`description`
^^^^^^^^^^^^^
A complete description of the schema. Depending on how complex your work becomes, try and be as
helpful as possible to 'future-you'. You'll thank yourself later.

Field descriptors
-----------------

Fields, similarly, contain `name`, `title` and `description`, as well as `type` as compulsory. To
see the available field types::

	>>> sc = _d.Schema()
	>>> sc.default_field_types
	['string',
	'number',
	'integer',
	'boolean',
	'object',
	'array',
	'date',
	'datetime',
	'year']

To see further parameter options for each default type::

	>>> sc.default_field_settings('string')
	{
		'required': ['name', 'type'],
		'name': 'field_name',
		'title': 'A human-readable version of the field name',
		'description': 'Any text-based string.',
		'type': 'string',
		'format': {
			'description': 'The format keyword options for `string` are `default`, `email`, `uri`, `binary`, and `uuid`.',
			'category': ['default', 'email', 'uri', 'binary', 'uuid'],
			'default': 'default'
			},
		'foreignKey': {
			'type': 'boolean',
			'description': 'Set `foreignKey` `true` if the field is to be treated as an immutable value.'
			},
		'constraints': {
			'description': 'The following constraints are supported.',
			'properties': {
				'required': {
					'type': 'boolean',
					'description': 'Indicates whether a property must have a value for each instance.'
				},
				'unique': {
					'type': 'boolean',
					'description': 'When `true`, each value for the property `MUST` be unique.'
				},
			'category': {
				'type': 'array',
				'minItems': 1,
				'uniqueItems': True,
				'terms': {
					'type': 'string'
					}
				},
			'minimum': {
				'type': 'integer',
				'description': 'An integer that specifies the minimum length of a value.'
				},
			'maximum': {
				'type': 'integer',
				'description': 'An integer that specifies the maximum length of a value.'
				}
			}
		},
	'missing': {
		'description': 'Default to be used for missing values.',
		'default': ''
		}
	}

`name`
^^^^^^
This is a required term and is equivalent to a column header. Spaces will be replaced with `_` and
the string will be lowercased.

`title`
^^^^^^^
A human-readable version of the field name.

`description`
^^^^^^^^^^^^^
A complete description of the field. As for the schema, try and be as helpful as possible to
future-you.

`foreignKey`
^^^^^^^^^^^^
This is a boolean term, only required if you need this field to be treated as a foreign-key or
identifier for your destination data::

	"foreignKey": True

Data in this field will not be tested for uniqueness. Instead, these data will remain immutable, not
being 'forced' into a date or number type to preserve whatever fruity formatting are described in
your input data.

During the wrangling process, this field can be used for merging with other input
data, ensuring consistency between sources.

`type` and `format`
^^^^^^^^^^^^^^^^^^^
`type` defines the data-type of the field, while `format` - which is currently unsupported in
wrangling - further refines the specific `type` properties. The core supported types, with indents
for formats:

* `string`: any text-based string.

  * `default`: any string
  * `email`: an email address
  * `uri`: any web address / URI

* `number`: any number-based value, including integers and floats.
* `integer`: any integer-based value.
* `boolean`: a boolean [`true`, `false`] value. Can set category constraints to fix term used.
* `object`: any valid JSON data.
* `array`: any valid array-based data.
* `date`: any date without a time. Must be in ISO8601 format, `YYYY-MM-DD`.
* `datetime`: any date with a time. Must be in ISO8601 format, with UTC time specified (optionally) as `YYYY-MM-DD hh:mm:ss Zz`.
* `year`: any year, formatted as `YYYY`.

`missing`
^^^^^^^^^
`missing` defines the value to be used for any blank values in a column. This is normally `""` for
text and `np.nan` for numbers or dates. You can, however, set your own defaults for each field.

Field constraints
-----------------
`Constraints` are optional parameters that refine input data wrangling and act as a primary form of
validation. Not all of these are available to every `type`, and `default_field_settings(type)`
will list constraints available to a specific field type.

Define these as part of your schema definition for a specific field::

	{
	  "name": "A simple name",
	  "fields": [
		{
			"name": "Field name, e.g. 'column_name'",
			"type": "Valid data type, e.g. 'string', 'number'",
			"constraints": {
				"required": True,
				"unique": True
			}
		}
	  ]
	}

All available constraints:

* `required`: boolean, indicates whether this field is compulsory (but blank values in the input column are permitted and will be set to the `missing` default)
* `unique`: boolean, if `true` then all values for that input column must be unique
* `minimum`: `integer` / `number`, as appropriate defining min number of characters in a string, or the min values of numbers or integers
* `maximum`: `integer` / `number`, as appropriate defining max number of characters in a string, or the max values of numbers or integers

Field constraints: category
---------------------------
In FrictionlessData.io, this is called `enum`, which isn't particularly meaningful. `Category` data
are the set of unique category terms permitted in this field. During wrangling you will be able to
define values which should be assigned to each of these categories.

Define these as part of your schema definition for a specific field::

	{
	  "name": "A simple name",
	  "fields": [
		{
			"name": "Field name, e.g. 'column_name'",
			"type": "Valid data type, e.g. 'string', 'number'",
			"constraints": {
				"category": ["cheddar", "gouda", "other"]
			}
		}
	  ]
	}

Each field `type` will have its own category constraints. For example, boolean categories can use a
different term than True / False defined by the category, but only permits two terms. Others have
a minimum of one term in a category, but require the list member type to be `string`, `number`, etc.
Ordinarily, `category` terms must be unique.

Review the `default_field_settings(type)` for that field's specific category constraints.

Field constraints: filter
--------------------------
`Filters` are a constraint that filter a named field, or the `foreignKey`, by date-limited data.

Define these as part of your schema definition for a valid field::

	{
	  "name": "A simple name",
	  "fields": [
		{
			"name": "Field name, e.g. 'column_name'",
			"type": "Valid data type, e.g. 'date', 'datetime'",
			"filter": {
				"field": "foreignKey",
				"modifiers": ["LATEST", "AFTER"]
			}
		}
	  ]
	}

There are two compulsory parameters defining a filter:

* `field`: another field which is the subject of this filter, or by default the 'foreignKey'.
* `modifiers`: an array of permitted filter terms, including any of ["LATEST", "AFTER", "BEFORE", "ALL"].

call `default_filter_names()` to get a list, and `default_filter_settings(filter_name)` to get a
definition

For example, to filter all foreign keys (which may be duplicated as part of a time-series) to be
more recent than a specified date, include "AFTER" in your list of filter modifiers.
"""

from copy import deepcopy

from whyqd.schema import Field
import whyqd.common as _c

class Schema:
	"""Create and manage a target schema for a wrangling process.

	Parameters
	----------
	source: path to a json file containing a saved schema, default is None
	kwargs: a schema defined as a dictionary, or default blank dictionary
	"""
	def __init__(self, source=None, **kwargs):
		self.required_field_terms = ["name", "type"]
		# Get default fields
		self.default_fields = self.build_default_fields()
		self.default_filters = _c.get_settings("filter")
		if source:
			kwargs = _c.load_json(source)
		self.schema_settings = deepcopy(kwargs)
		self.build()

	def __repr__(self):
		"""
		Returns the string representation of the model.
		"""
		if self.schema_settings.get("name"):
			return "Schema: `{}`".format(self.schema_settings["name"])
		return "Schema"

	@property
	def details(self):
		"""
		Schema name, title and description.

		Parameters
		----------
		name: string
			Term used for filename and referencing. Will be lower-cased and spaces replaced with `_`
		title: string
			Human-readable term used as name.
		description: string
			Detailed description for the schema. Reference its objective and use-case.

		Returns
		-------
		dict
		"""
		response = {
			"name": self.schema_settings.get("name"),
			"title": self.schema_settings.get("title"),
			"description": self.schema_settings.get("description")
		}
		return response

	def set_details(self, name=None, title=None, description=None):
		"""
		Set schema name, title and description. Can also be used to update existing information.

		Parameters
		----------
		name: string
			Term used for filename and referencing. Will be lower-cased and spaces replaced with `_`
		title: string
			Human-readable term used as name.
		description: string
			Detailed description for the schema. Reference its objective and use-case.

		Raises
		------
		KeyError: if missing name
		"""
		if "name" not in self.schema_settings and not name:
			# `name` required
			e = "`name` not found in target schema"
			raise KeyError(e)
		for v in [name, title, description]:
			if v and not isinstance(v, str):
				e = "`{}` is not a valid string. Schema details must be strings."
				raise TypeError(e)
		self.schema_settings["name"] = "_".join(name.split(" ")).lower()
		if title: self.schema_settings["title"] = title
		if description: self.schema_settings["description"] = description

	@property
	def default_filter_names(self):
		"""
		Default list of filter names available as field constraints for the schema. Returns only a
		list of types. Details for individual filters can be returned with
		`default_filter_settings`.

		Returns
		-------
		list
		"""
		return [f["name"] for f in self.default_filters["filter"]["modifiers"]]

	def default_filter_settings(self, filter_name):
		"""
		Get the default settings available for a specific filter.

		Parameters
		----------
		filter_name: string
			A specific name for a filter type (as listed in `default_filter_names`).

		Returns
		-------
		dict, or empty dict if no such `filter_name`
		"""
		for filter in self.default_filters["filter"]["modifiers"]:
			if filter["name"] == filter_name:
				return deepcopy(filter)
		return {}

	@property
	def default_field_types(self):
		"""
		Default list of field names available to define fields for the schema. Returns only a list
		of types. Details for individual default fields can be returned with
		`default_field_settings`.

		Returns
		-------
		list
		"""
		return [f.type for f in self.default_fields]

	def default_field_settings(self, field_type):
		"""
		Get the default settings available for a specific field type.

		Parameters
		----------
		field_type: string
			A specific term for a field type (as listed in `default_field_types`).

		Returns
		-------
		dict, or empty dict if no such `field_type`
		"""
		for f in self.default_fields:
			if f.type == field_type:
				return deepcopy(f.settings)
		return {}

	@property
	def all_fields(self):
		"""
		Get dictionary of fields, where key: `field_name` and value: `type`.

		Returns
		-------
		dict, or empty dict if no fields
		"""
		return {f.name: f.type for f in self.schema_settings.get("fields", [])}

	@property
	def all_field_names(self):
		"""
		Get list of field names,.

		Returns
		-------
		list
		"""
		return [f.name for f in self.schema_settings.get("fields", [])]

	def field(self, name):
		"""
		A specific field from the list of fields defining this schema, called by a unique `name`.

		Parameters
		----------
		name: string
			Field names must be unique, so a valid `name` in the field list will have no collisions.

		Returns
		-------
		dict, or empty dict if no such `name`
		"""
		for field in self.schema_settings.get("fields", []):
			if field.name == name:
				return deepcopy(field.settings)
		e = "`{}` not found in Schema fields.".format(name)
		raise ValueError(e)

	def set_field(self, **kwargs):
		"""
		Set the parameters for a specific field to define this schema, called by a unique `name`.
		If the `name` is already in the schema, then this will update that field.

		Parameters
		----------
		kwargs: dict
			Parameters will be validated against the type requirements, so check carefully with
			`default_field_settings`.
		"""
		kwargs = deepcopy(kwargs)
		if "name" not in kwargs:
			e = "No valid `name` provided for Field."
			raise ValueError(e)
		self.schema_settings.get("fields", [])[:] = [f for f in self.schema_settings.get("fields", [])
													 if f.name != kwargs["name"]]
		kwargs["name"] = "_".join(kwargs["name"].split(" ")).lower()
		field = self.build_field(**kwargs)
		self.schema_settings["fields"].append(field)

	def set_field_constraints(self, name, **constraints):
		"""
		Set the constraint parameters for a specific field to define this schema, called by a unique
		`name` already in the schema.

		The structure of the constraints is defined as follows::

			{
				"key": "value",
				"key": "value"
			}

		`category` is a special constraint that can be defined as e.g.::

			{
				"category": ["term1", "term2"]
			}

		All that is required is a list, and the function will take care of the formal structure.
		`filter` are managed in the Method part of the process (since this are defined in respect
		to the data being structured).

		Parameters
		----------
		name: string
			Specific name for a field already in the Schema
		constraints: dict
			A set of key:value pairs defining constraints as described in `default_field_settings`.
		"""
		field = self.field(name)
		valid_constraints = self.default_field_settings(field["type"]).get("constraints", {}).keys()
		if not valid_constraints:
			e = "Field `{}` has no permitted constraints.".format(name)
			raise ValueError(e)
		for constraint in constraints:
			if constraint not in valid_constraints:
				e = "Constraint `{}` is not permitted in field `{}`.".format(constraint, name)
				raise KeyError(e)
		category = constraints.pop("category", None)
		if not field.get("constraints"):
			field["constraints"] = {}
		if constraints:
			field["constraints"] = {**field["constraints"], **constraints}
			self.set_field(**field)
		if category: self.set_field_category(name, *category["category"])

	def set_field_category(self, name, *categories, overwrite=True):
		"""
		Set the category constraint parameters for a specific field. `categories` is defined as e.g.::

			["term1", "term2"]

		All that is required is a list, and the function will take care of the formal structure.

		Parameters
		----------
		name: string
			Specific name for a field already in the Schema
		categories: list
			A list of string terms defining target categories.
		overwrite: bool
			If field has existing category constraints, then overwrite with this new list.
		"""
		field = self.field(name)
		if not overwrite:
			original = [c["name"] for c in field.get("constraints", {}).get("category", [])]
			categories.extend(original)
			categories = set(categories)
		category = [{"name": c} for c in categories]
		field["constraints"]["category"] = category
		self.set_field(**field)

	def set_field_filters(self, name, *filters):
		"""
		Set the filter parameters for a specific field to define this schema, called by a unique
		`name` already in the schema.

		Parameters
		----------
		name: string
			Specific name for a field already in the Schema
		filters: list of strings
			A list of filter names as described in `default_filter_names`.
		"""
		field = self.field(name)
		self.schema_settings["fields"][:] = [f for f in self.schema_settings["fields"]
											 if f.name != field.name]
		# update field
		filters = deepcopy(filters)
		modifiers = [f for f in self.default_filters["filters"]["modifiers"]
					 if f["name"] in filters]
		if modifiers:
			filters = {
				"field": self.default_filters["filter"]["field"],
				"modifiers": modifiers
			}
			field["constraints"]["properties"]["filter"] = filters
			field = self.build_field(**field)
			self.schema_settings["fields"].append(field)

	def build_field(self, **field):
		"""
		For a list of fields, defined as dictionaries, create and return Field objects.

		Parameters
		----------
		field: dictionary of Field parameters

		Raises
		------
		ValueError: if field fails validation

		Returns
		-------
		Field
		"""
		field = deepcopy(field)
		if not isinstance(field, dict) or not all(key in field for key in self.required_field_terms):
			e = "Field is not a valid dictionary"
			raise ValueError(e)
		_name = field["name"]
		del field["name"]
		_type = field["type"]
		del field["type"]
		field = Field(_name, _type, **field)
		if not field.validates:
			e = "Field `{}` of type `{}` does not validate".format(_name, _type)
			raise ValueError(e)
		return field

	def build(self):
		"""
		Build and validate the Schema.
		"""
		self.schema_settings["fields"] = [self.build_field(**field) for field in
										  self.schema_settings.get("fields", [])]

	def build_default_fields(self):
		"""
		Build the default fields for presentation to the user as options.

		Returns
		-------
		list of Fields
		"""
		default_fields = _c.get_settings("schema")
		default_fields = [{**default_fields["common"], **f}
						  for f in default_fields["fields"]]
		response = []
		for field in default_fields:
			_name = field["name"]
			del field["name"]
			_type = field["type"]
			del field["type"]
			response.append(Field(_name, _type, validate=False, **field))
		return response

	@property
	def validates(self):
		"""
		Schema validates with all fields unique and required terms.

		Raises
		------
		ValueError on field failure.

		Returns
		-------
		bool: True for validates
		"""
		if not all([field.validates for field in self.schema_settings.get("fields", [])]):
			e = "Individual `fields` in schema are not valid."
			raise ValueError(e)
		fields = [field.name for field in self.schema_settings.get("fields", [])]
		if not fields:
			e = "No `fields` in schema. Need at least one."
			raise ValueError(e)
		if len(fields) != len(set(fields)):
			e = "Schema `field` names not unique: `{}`.".format(fields)
			raise ValueError(e)
		if not "name" in self.schema_settings:
			e = "Schema `name` not present."
			raise ValueError(e)
		return True

	@property
	def settings(self):
		"""
		Schema settings returned as a dictionary.

		Returns
		-------
		dict: settings
		"""
		schema_dict = deepcopy(self.schema_settings)
		if not self.validates:
			e = "Schema did not validate during dictionary build. Check `name` and `fields`."
			raise ValueError(e)
		schema_dict["fields"] = [field.settings for field in self.schema_settings.get("fields", [])]
		return schema_dict

	def save(self, directory, filename=None, overwrite=False, created_by=None):
		"""
		Schema settings returned as a dictionary.

		Parameters
		----------
		directory: the destination directory
		filename: default to schema name
		overwrite: bool, True if overwrite existing file
		created_by: string, or None, to define the schema creator/updater

		Raises
		------
		ValueError if no `filename`

		Returns
		-------
		bool True if saved
		"""
		if not filename: filename = self.schema_settings.get("name")
		if not filename:
			e = "Schema save requires a valid filename"
			raise ValueError(e)
		if filename.split(".")[-1] != "json":
			filename += ".json"
		data = self.settings
		now = _c.get_now()
		if "created" not in data:
			data["created"] = now
		data["updated"] = now
		if created_by and isinstance(created_by, str):
			if "created_by" not in data:
				data["created_by"] = created_by
			data["updated_by"] = created_by
		return _c.save_json(data, directory + filename, overwrite)