"""
.. module:: method
   :synopsis: Create and manage a wrangling method based on a predefined schema.

.. moduleauthor:: Gavin Chait <github.com/turukawa>

Method
======

Once you have created your `Schema` it can be imported and used to develop a wrangling `method`, a
complete, structured JSON file which describes all aspects of the wrangling process. There is no
'magic'. Only what is defined in the method will be executed during transformation.

A method file can be shared, along with your input data, and anyone can import **whyqd** and
validate your method to verify that your output data is the product of these inputs::

	import whyqd as _w
	method = _w.Method(source, directory=DIRECTORY, input_data=INPUT_DATA)

`source` is the full path to the schema you wish to use, and `DIRECTORY` will be your working
directory for saved data, imports, working data and output.

`INPUT_DATA` is a list of filenames or file sources. This is optional at this stage, and you can
add and edit your sources later. File sources can include URI's.

Help
----

To get help, type::

	method.help()
	# or
	method.help(option)

Where `option` can be any of::

	"status"
	"merge"
	"structure"
	"category"
	"filter"

`status` will return the current method status, and your mostly likely next steps. The other options
will return methodology, and output of that option's result (if appropriate).

These are the steps to create a complete method:

Merge
-----
`merge` will join, in order from right to left, your input data on a common column. You can modify
your input data at any time. Note, however, that this will reset your status and require
revalidation of all subsequent steps.

To add input data, where `input_data` is a filename / source, or list of filenames / sources::

	method.add_input_data(input_data)

To remove input data, where `id` is the unique id for that input data:

	method.remove_input_data(id)

To display a nicely-formatted output for review::

	# Permits horizontal scroll-bar in Jupyter Notebook
	from IPython.core.display import HTML
	display(HTML("<style>pre { white-space: pre !important; }</style>"))

	print(method.pretty_print_input_data())

	Data id: c8944fed-4e8c-4cbd-807d-53fcc96b7018

	====  ====================  ========================  =================================  =============================  =======================================================  =============================  ===========================
	  ..  Account Start date      Current Rateable Value  Current Relief Award Start Date    Current Relief Type            Full Property Address                                    Primary Liable party name        Property Reference Number
	====  ====================  ========================  =================================  =============================  =======================================================  =============================  ===========================
	   0  2003-05-14 00:00:00                       8600  2019-04-01 00:00:00                Retail Discount                Ground Floor, 25, Albert Road, Southsea, Hants, PO5 2SE  Personal details not supplied                 177500080710
	   1  2003-07-28 00:00:00                       9900  2005-04-01 00:00:00                Small Business Relief England  Ground Floor, 102, London Road, Portsmouth, PO2 0LZ      Personal details not supplied                 177504942310
	   2  2003-07-08 00:00:00                       6400  2005-04-01 00:00:00                Small Business Relief England  33, Festing Road, Southsea, Hants, PO4 0NG               Personal details not supplied                 177502823510
	====  ====================  ========================  =================================  =============================  =======================================================  =============================  ===========================

	Data id: a9ad7716-f777-4752-8627-dd6206bede65

	====  ===================================  =================================  ========================  ================================================================  =======================================================  ===========================
	  ..  Current Prop Exemption Start Date    Current Property Exemption Code      Current Rateable Value  Full Property Address                                             Primary Liable party name                                  Property Reference Number
	====  ===================================  =================================  ========================  ================================================================  =======================================================  ===========================
	   0  2019-11-08 00:00:00                  LOW RV                                                  700  Advertising Right, 29 Albert Road, Portsmouth, PO5 2SE            Personal details not supplied                                           177512281010
	   1  2019-09-23 00:00:00                  INDUSTRIAL                                            11000  24, Ordnance Court, Ackworth Road, Portsmouth, PO3 5RZ            Personal details not supplied                                           177590107810
	   2  2019-09-13 00:00:00                  EPRI                                                  26500  Unit 12, Admiral Park, Airport Service Road, Portsmouth, PO3 5RQ  Legal & General Property Partners (Industrial Fund) Ltd                 177500058410
	====  ===================================  =================================  ========================  ================================================================  =======================================================  ===========================

	Data id: 1e5a165d-5e83-4eec-9781-d450a1d3f5f1

	====  ====================  ========================  =========================================================================  ==========================================  =================
	  ..  Account Start date      Current Rateable Value  Full Property Address                                                      Primary Liable party name                     Property ref no
	====  ====================  ========================  =========================================================================  ==========================================  =================
	   0  2003-11-10 00:00:00                      37000  Unit 7b, The Pompey Centre, Dickinson Road, Southsea, Hants, PO4 8SH       City Electrical Factors  Ltd                     177200066910
	   1  2003-11-08 00:00:00                     594000  Express By Holiday Inn, The Plaza, Gunwharf Quays, Portsmouth, PO1 3FD     Kew Green Hotels (Portsmouth Lrg1) Limited       177209823010
	   2  1994-12-25 00:00:00                      13250  Unit 2cd, Shawcross Industrial Estate, Ackworth Road, Portsmouth, PO3 5JP  Personal details not supplied                    177500013310
	====  ====================  ========================  =========================================================================  ==========================================  =================

Once you're satisfied with your `input_data`, prepare an `order_and_key` list to define the merge
order, and a unique key for merging. Each input data file needs to be defined in a list as a dict::

	{id: input_data id, key: column_name for merge}

Run the merge by calling (and, optionally - if you need to overwrite an existing merge - setting
`overwrite_working=True`)::

	method.merge(order_and_key, overwrite_working=True)

To view your existing `input_data` as a JSON output (or the `pretty_print_input_data` as above)::

	method.input_data

Structure
---------
`structure` is the core of the wrangling process and is the step where you define the actions
which must be performed to restructure your working data.

Create a list of methods of the form::

	{
		"schema_field1": ["action", "column_name1", ["action", "column_name2"]],
		"schema_field2": ["action", "column_name1", "modifier", ["action", "column_name2"]],
	}

The format for defining a `structure` is as follows, and - yes - this does permit you to create
nested wrangling tasks::

	[action, column_name, [action, column_name]]

e.g.::

	["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

This permits the creation of quite expressive wrangling structures from simple building blocks.

Every task structure must start with an action to describe what to do with the following terms.
There are several "actions" which can be performed, and some require action modifiers:

	* NEW: Add in a new column, and populate it according to the value in the "new" constraint

	* RENAME: If only 1 item in list of source fields, then rename that field

	* ORDER: If > 1 item in list of source fields, pick the value from the column, replacing each value with one from the next in the order of the provided fields

	* ORDER_NEW: As in ORDER, but replacing each value with one associated with a newer "dateorder" constraint

		* MODIFIER: `+` between terms for source and source_date

	* ORDER_OLD: As in ORDER, but replacing each value with one associated with an older "dateorder" constraint

		* MODIFIER: `+` between terms for source and source_date

	* CALCULATE: Only if of "type" = "float64" (or which can be forced to float64)

		* MODIFIER: `+` or `-` before each term to define whether add or subtract

	* JOIN: Only if of "type" = "object", join text with " ".join()

	* CATEGORISE: Only if of "type" = "string"; look for associated constraint, "categorise" where `True` = keep a list of categories, `False` = set True if terms found in list

		* MODIFIER:

			* `+` before terms where column values to be classified as unique

			* `-` before terms where column values are treated as boolean

Category
--------

Provide a list of categories of the form::

	{
		"schema_field1": {
			"category_1": ["term1", "term2", "term3"],
			"category_2": ["term4", "term5", "term6"]
		}
	}

The format for defining a `category` term as follows::

	term_name::column_name

Get a list of available terms, and the categories for assignment, by calling::

	method.category(field_name)

Once your data are prepared as above::

	method.set_category(**category)

Filter
------
Set date filters on any date-type fields. **whyqd** offers only rudimentary post-
wrangling functionality. Filters are there to, for example, facilitate importing data
outside the bounds of a previous import.

This is also an optional step. By default, if no filters are present, the transformed output
will include `ALL` data. Parameters for filtering:

	* `field_name`: Name of field on which filters to be set
	* `filter_name`: Name of filter type from the list of valid filter names
	* `filter_date`: A date in the format specified by the field type
	* `foreign_field`: Name of field to which filter will be applied. Defaults to `field_name`

There are four filter_names:

	* `ALL`: default, import all data
	* `LATEST`: only the latest date
	* `BEFORE`: before a specified date
	* `AFTER`: after a specified date

`BEFORE` and `AFTER` take an optional `foreign_field` term for filtering on that column. e.g::

	method.set_filter("occupation_state_date", "AFTER", "2019-09-01", "ba_ref")

Filters references in column `ba_ref` by dates in column `occupation_state_date` after `2019-09-01`.

Validation
----------
Each step can be validated and, once all steps validate, you can move to transformation of your data::

	method.validate_input_data
	method.validate_merge_data
	method.validate_merge
	method.validate_structure
	method.validate_category
	method.validate_filter

Or, to run all the above and complete the method (setting status to 'Ready to Transform')::

	method.validate
"""
import os, uuid
from shutil import copyfile
from copy import deepcopy
import pandas as pd
from tabulate import tabulate
from operator import itemgetter

import whyqd.common as _c
from whyqd.schema import Schema
from whyqd.method import Action

STATUS_CODES = {
	"WAITING": "Waiting ...",
	"PROCESSING": "Processing ...",
	"READY_MERGE": "Ready to Merge",
	"READY_STRUCTURE": "Ready to Structure",
	"READY_CATEGORY": "Ready to Categorise",
	"READY_FILTER": "Ready to Filter",
	"READY_TRANSFORM": "Ready to Transform",
	"CREATE_ERROR": "Create Error",
	"MERGE_ERROR": "Merge Error",
	"STRUCTURE_ERROR": "Structure Error",
	"CATEGORY_ERROR": "Categorisation Error",
	"TRANSFORMATION_ERROR": "Transform Error",
	"PROCESS_COMPLETE": "Process Complete"
}

class Method(Schema):
	"""
	Create and manage a method to perform a wrangling process.

	Parameters
	----------
	source: path to a json file containing a saved schema, default is None
	directory: working path for creating methods, interim data files and final output
	kwargs: a schema defined as a dictionary, or default blank dictionary
	"""
	def __init__(self, source=None, **kwargs):
		self._status = "WAITING"
		# Clear kwargs of things we need to process prior to initialising
		self.directory = kwargs.pop("directory", None)
		if not self.directory.endswith("/"):
			self.directory += "/"
		constructors = kwargs.pop("constructors", None)
		input_data = kwargs.pop("input_data", None)
		super().__init__(source=source, **kwargs)
		# Initialise after Schema initialisation
		self.default_actions = self.build_default_actions()
		if constructors: self.set_constructors(constructors)
		if input_data: self.add_input_data(input_data)
		self.valid_filter_field_types = ["date", "year", "datetime"]

	def merge(self, order_and_key=None, overwrite_working=False):
		"""
		Merge input data on a key column.

		Parameters
		----------
		order_and_key: list
			List of dictionaries specifying `input_data` order and key for merge. Can also use
			`order_and_key_input_data` directly. Each dict in the list has
			`{id: input_data id, key: column_name for merge}`
		overwrite_working: bool
			Permission to overwrite existing working data

		TO_DO
		-----
		While `merge` validates column uniqueness prior to merge, if the column is not unique there
		is nothing the user can do about it (without manually going and refixing the input data).
		Some sort of uniqueness fix required (probably using the filters).
		"""
		if order_and_key and isinstance(order_and_key, list):
			self.order_and_key_input_data(*order_and_key)
		if self._status in STATUS_CODES.keys() - ["READY_MERGE", "READY_STRUCTURE", "READY_CATEGORY",
												  "READY_FILTER", "READY_TRANSFORM", "PROCESS_COMPLETE",
												  "MERGE_ERROR"]:
			e = "Current status: `{}` - performing `merge` is not permitted.".format(self.status)
			raise PermissionError(e)
		self.validate_merge_data
		if ("working_data" in self.schema_settings and
			not self.schema_settings["working_data"].get("checksum")):
			e = "Permission required to overwrite `working_data`. Set `overwrite_working` to `True`."
			raise PermissionError(e)
		# Pandas 1.0 says `dtype = "string"` is possible, but it isn't currently working
		# defaulting to `dtype = object` ...
		# Note, this is done to avoid any random column processing
		df = _c.get_dataframe(self.directory + self.schema_settings["input_data"][0]["file"],
							  dtype = object)
		df_key = self.schema_settings["input_data"][0]["key"]
		for data in self.schema_settings["input_data"][1:]:
			# defaulting to `dtype = object` ...
			dfm = _c.get_dataframe(self.directory + data["file"], dtype = object)
			dfm_key = data["key"]
			df = pd.merge(df, dfm, how="outer",
						  left_on=df_key, right_on=dfm_key,
						  indicator=False)
		# Deduplicate any columns after merge (and deduplicate the deduplicate in case of artifacts)
		df.columns = self.deduplicate_columns(self.deduplicate_columns(df.columns))
		# Save the file to the working directory
		if "working_data" in self.schema_settings:
			del self.schema_settings["working_data"]
		self.schema_settings["working_data"] = self.save_data(df)

		# Review for any existing actions
		# self.validate_actions

		self._status = "READY_STRUCTURE"

	def structure(self, name):
		"""
		Return a 'markdown' version of the formal structure for a specific `name` field.

		Returns
		-------
		list
			(nested) strings in structure format
		"""
		markdown = self.field(name).get("structure")
		if markdown:
			return self.build_structure_markdown(markdown)
		return []

	def set_structure(self, **kwargs):
		"""
		Receive a list of methods of the form::

			{
				"schema_field1": ["action", "column_name1", ["action", "column_name2"]],
				"schema_field2": ["action", "column_name1", "modifier", ["action", "column_name2"]],
			}

		The format for defining a `structure` is as follows::

			[action, column_name, [action, column_name]]

		e.g.::

			["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

		This permits the creation of quite expressive wrangling structures from simple building
		blocks.

		Every task structure must start with an action to describe what to do with the following
		terms. There are several "actions" which can be performed, and some require action
		modifiers:

			* NEW: Add in a new column, and populate it according to the value in the "new" constraint

			* RENAME: If only 1 item in list of source fields, then rename that field

			* ORDER: If > 1 item in list of source fields, pick the value from the column, replacing each value with one from the next in the order of the provided fields

			* ORDER_NEW: As in ORDER, but replacing each value with one associated with a newer "dateorder" constraint

				* MODIFIER: `+` between terms for source and source_date

			* ORDER_OLD: As in ORDER, but replacing each value with one associated with an older "dateorder" constraint

				* MODIFIER: `+` between terms for source and source_date

			* CALCULATE: Only if of "type" = "float64" (or which can be forced to float64)

				* MODIFIER: `+` or `-` before each term to define whether add or subtract

			* JOIN: Only if of "type" = "object", join text with " ".join()

			* CATEGORISE: Only if of "type" = "string"; look for associated constraint, "categorise" where `True` = keep a list of categories, `False` = set True if terms found in list

				* MODIFIER:

					* `+` before terms where column values to be classified as unique

					* `-` before terms where column values are treated as boolean

		Paramaters
		----------
		kwargs: dict
			Where key is schema target field and value is list defining the structure action
		"""
		if self._status in STATUS_CODES.keys() - ["READY_STRUCTURE", "READY_CATEGORY", "READY_FILTER",
												  "READY_TRANSFORM", "PROCESS_COMPLETE", "STRUCTURE_ERROR"]:
			e = "Current status: `{}` - performing `set_structure` not permitted.".format(self.status)
			raise PermissionError(e)
		self.validate_merge
		category_check = False
		for field_name in kwargs:
			if field_name not in self.all_field_names:
				e = "Term `{}` not a valid field for this schema.".format(field_name)
				raise ValueError(e)
			schema_field = self.field(field_name)
			schema_field["structure"] = self.set_field_structure(kwargs[field_name])
			# Set unique field structure categories
			has_category = []
			for term in set(self.flatten_category_fields(kwargs[field_name])):
				term = term.split("::")
				modifier = term[0]
				# Just in case
				column = "::".join(term[1:])
				has_category.append(self.set_field_structure_categories(modifier, column))
			if has_category:
				category_check = True
				if (not schema_field.get("constraints", {}).get("category") and
					schema_field["type"] == "boolean"):
					if not schema_field.get("constraints"):
						schema_field["constraints"] = {}
					# Boolean fields have an implied constraint
					schema_field["constraints"]["category"] = [
						{
							"name": True
						},
						{
							"name": False
						}
					]
				if not schema_field.get("constraints", {}).get("category"):
					e = "Field `{}` has no `category` constraints. Please `set_field_category`."
					raise ValueError(e.format(field_name))
				schema_field["constraints"]["category_input"] = has_category
			# Validation would not add in the new values
			self.set_field(validate=False, **schema_field)
		self._status = "READY_CATEGORY"
		if not category_check: self._status = "READY_FILTER"

	def category(self, name):
		"""
		Return a 'markdown' version of assigned and unassigned category inputs for a named field
		of the form::

			{
				"categories": ["category_1", "category_2"]
				"assigned": {
					"category_1": ["term1", "term2", "term3"],
					"category_2": ["term4", "term5", "term6"]
				},
				"unassigned": ["term1", "term2", "term3"]
			}

		The format for defining a `category` term as follows::

			`term_name::column_name`

		Returns
		-------
		list of (nested) strings in structure format
		"""
		schema_field = self.field(name)
		assigned = {}
		unassigned = []
		if schema_field.get("category"):
			for marked in schema_field["category"].get("assigned", []):
				if schema_field["type"] == "boolean":
					if marked["name"]: u = "true"
					else: u = "false"
				else:
					u = marked["name"]
				assigned[u] = self.build_category_markdown(marked["category_input"])
			unassigned = self.build_category_markdown(schema_field["category"].get("unassigned", []))
		if (not schema_field.get("constraints", {}).get("category", []) or
			not schema_field.get("constraints", {}).get("category_input")):
			e = "Field `{}` has no available categorical data.".format(field_name)
			raise ValueError(e)
		if not schema_field.get("category"):
			unassigned = self.build_category_markdown(schema_field["constraints"]["category_input"])
		# Deals with boolean `True`/`False` case...
		if schema_field["type"] == "boolean":
			categories = ["true", "false"]
		else:
			categories = [c["name"] for c in schema_field["constraints"]["category"]]
		response = {
			"categories": categories,
			"assigned": assigned,
			"unassigned": unassigned
		}
		return response

	def set_category(self, **kwargs):
		"""
		Receive a list of categories of the form::

			{
				"schema_field1": {
					"category_1": ["term1", "term2", "term3"],
					"category_2": ["term4", "term5", "term6"]
				}
			}

		The format for defining a `category` term as follows::

			`term_name::column_name`
		"""
		if self._status in STATUS_CODES.keys() - ["READY_CATEGORY", "READY_FILTER",
												  "READY_TRANSFORM", "PROCESS_COMPLETE", "CATEGORY_ERROR"]:
			e = "Current status: `{}` - performing `set_category` not permitted.".format(self.status)
			raise PermissionError(e)
		self.validate_structure
		for field_name in kwargs:
			if field_name not in self.all_field_names:
				e = "Term `{}` not a valid field for this schema.".format(field_name)
				raise ValueError(e)
			schema_field = self.field(field_name)
			field_category = schema_field.get("constraints", {}).get("category_input")
			# Validation checks
			if not field_category:
				e = "Field `{}` has no available categorical data.".format(field_name)
				raise ValueError(e)
			if schema_field["type"] == "boolean":
				cat_diff = set(kwargs[field_name].keys()) - set(["true", "false"])
			else:
				field_category = schema_field.get("constraints", {}).get("category", [])
				cat_diff = set(kwargs[field_name].keys()) - set([c["name"] for c in field_category])
			if cat_diff:
				e = "Field `{}` has invalid categories `{}`.".format(field_name, cat_diff)
				raise ValueError(e)
			# Get assigned category_inputs
			assigned = []
			for name in kwargs[field_name]:
				c_name = name
				if schema_field["type"] == "boolean":
					if c_name == "true":
						c_name = True
					else:
						c_name = False
				category_term = {
					"name": c_name,
					"category_input": []
				}
				input_terms = {}
				for term in kwargs[field_name][name]:
					term = term.split("::")
					column = term[-1]
					term = "::".join(term[:-1])
					if not input_terms.get(column):
						input_terms[column] = []
					if term not in input_terms[column]:
						input_terms[column].append(term)
				# process input_terms
				for column in input_terms:
					category_term["category_input"].append(
						{
							"column": column,
							"terms": input_terms[column]
						}
					)
				# append to category
				assigned.append(category_term)
			# Get unassigned category_inputs
			unassigned = []
			for terms in schema_field["constraints"]["category_input"]:
				all_terms = terms["terms"]
				all_assigned_terms = []
				for assigned_term in assigned:
					assigned_input_terms = []
					for assigned_input in assigned_term["category_input"]:
						if assigned_input["column"] == terms["column"]:
							assigned_input_terms = assigned_input["terms"]
							break
					# validate
					if set(assigned_input_terms) - set(all_terms):
						e = "Field `{}` has invalid input category terms `{}`."
						raise ValueError(e.format(field_name,
												  set(assigned_input_terms) - set(all_terms)))
					# extend
					all_assigned_terms.extend(assigned_input_terms)
				# validate if duplicates
				if len(all_assigned_terms) > len(set(all_assigned_terms)):
					e = "Field `{}` has duplicate input category terms `{}`."
					# https://stackoverflow.com/a/9835819
					seen = set()
					dupes = [x for x in all_assigned_terms if x not in seen and not seen.add(x)]
					raise ValueError(e.format(field_name, dupes))
				unassigned_terms = list(set(all_terms) - set(all_assigned_terms))
				unassigned.append(
						{
							"column": terms["column"],
							"terms": unassigned_terms
						}
					)
			# Set the category
			schema_field["category"] = {
				"assigned": assigned,
				"unassigned": unassigned
			}
			# Update the field
			self.set_field(validate=False, **schema_field)
		self._status = "READY_TRANSFORM"

	def filter(self, name):
		"""
		Return the filter settings for a named field. If there are no filter settings, return None.

		Raises
		------
		TypeError if setting a filter on this field type is not permitted.

		Returns
		-------
		dict of filter settings, or None
		"""
		schema_field = self.field(field_name)
		# Validate the filter
		if schema_field["type"] not in self.valid_filter_field_types:
			e = "Filters cannot be set on field of type `{}`.".format(schema_field["type"])
			raise TypeError(e)
		return schema_field.get("filter", None)

	def set_filter(self, field_name, filter_name, filter_date=None, foreign_field=None):
		"""
		Sets the filter settings for a named field after validating all parameters.

		NOTE: filters can only be set on date-type fields. **whyqd** offers only rudimentary post-
		wrangling functionality. Filters are there to, for example, facilitate importing data
		outside the bounds of a previous import.

		This is also an optional step. By default, if no filters are present, the transformed output
		will include `ALL` data.

		Parameters
		----------
		field_name: str
			Name of field on which filters to be set
		filter_name: str
			Name of filter type from the list of valid filter names
		filter_date: str (optional)
			A date in the format specified by the field type
		foreign_field: str (optional)
			Name of field to which filter will be applied. Defaults to `field_name`

		Raises
		------
		TypeError if setting a filter on this field type is not permitted.
		ValueError for any validation failures.
		"""
		if self._status in STATUS_CODES.keys() - ["READY_FILTER", "READY_TRANSFORM",
												  "PROCESS_COMPLETE", "FILTER_ERROR"]:
			e = "Current status: `{}` - performing `set_filter` not permitted.".format(self.status)
			raise PermissionError(e)
		self.validate_category
		schema_field = self.field(field_name)
		# Validate the filter
		if schema_field["type"] not in self.valid_filter_field_types:
			e = "Filters cannot be set on field of type `{}`.".format(schema_field["type"])
			raise TypeError(e)
		filter_settings = {}
		for fset in self.default_filters["filter"]["modifiers"]:
			if fset["name"] == filter_name:
				filter_settings = fset
				break
		if not filter_settings:
			e = "Filter: `{}` is not a valid filter-type.".format(filter_name)
			raise TypeError(e)
		if filter_settings["date"]:
			if not filter_date:
				e = "Filter: `{}` requires a `{}` for filtering.".format(filter_name,
																		 schema_field["type"])
				raise ValueError(e)
			_c.check_date_format(schema_field["type"], filter_date)
		else:
			# Make sure
			filter_date = False
		# Validate the foreign field
		if foreign_field:
			if foreign_field not in self.all_field_names:
				e = "Filter foreign field `{}` is not a valid field.".format(foreign_field)
				raise ValueError(e)
		else:
			foreign_field = schema_field["name"]
		# Set the filter
		schema_field["filter"] = {
			"field": foreign_field,
			"modifiers": {
				"name": filter_settings["name"],
				"date": filter_date
			}
		}
		# Update the field
		self.set_field(validate=False, **schema_field)
		self._status = "READY_TRANSFORM"

	#########################################################################################
	# SUPPORT FUNCTIONS
	#########################################################################################

	@property
	def status(self):
		return STATUS_CODES[self._status]

	def set_directory(self, directory):
		_c.check_path(directory)
		self.schema_settings["directory"] = directory
		self.directory = directory

	@property
	def constructors(self):
		"""
		Constructors are additional metadata to be included with the `method`. Ordinarily, this is
		a dictionary of key:value pairs defining any metadata that may be used post-wrangling and
		need to be maintained with the target data.
		"""
		return deepcopy(self.schema_settings.get("constructors"))

	def set_constructors(self, constructors):
		"""
		Define additional metadata to be included with the `method`.

		Parameters
		----------
		constructors: dict
			A set of key:value pairs. These will not be validated, or used during transformation.

		Raises
		------
		TypeError if not a dict.
		"""
		if not constructors or not isinstance(constructors, dict):
			e = "Method constructor is not a valid dict."
			raise TypeError(e)
		self.schema_settings["constructors"] = deepcopy(constructors)

	#########################################################################################
	# CREATE & MODIFY INPUT DATA
	#########################################################################################

	@property
	def input_data(self):
		return deepcopy(self.schema_settings.get("input_data", []))

	def pretty_print_input_data(self, format="rst"):
		# https://github.com/astanin/python-tabulate#table-format
		response = ""
		for data in self.input_data:
			_id = data["id"]
			_df = pd.DataFrame(data["dataframe"])
			_df = tabulate(_df, headers="keys", tablefmt=format)
			response += HELP_RESPONSE["data"].format(_id, _df)
		return response

	def add_input_data(self, input_data):
		"""
		Provide a list of strings, each the filename of input data for wrangling.

		Parameters
		----------
		input_data: str or list of str
			Each input data can be a filename, or a file_source (where filename is remote)

		Raises
		------
		TypeError if not a list of str.
		"""
		valid = False
		if isinstance(input_data, str):
			input_data = [input_data]
		if isinstance(input_data, list):
			valid = all([isinstance(i, str) for i in input_data])
		if not valid:
			self._status = "CREATE_ERROR"
			e = "`{}` is not a valid list of input data.".format(input_data)
			raise TypeError(e)
		self.schema_settings["input_data"] = self.schema_settings.get("input_data", [])
		for filename in input_data:
			# Check if the filename is remote
			file_source = "/".join(filename.split("/")[:-1])
			filename = filename.split("/")[-1]
			source = self.directory + filename
			if file_source:
				copyfile(file_source + "/" + filename, source)
			_id = str(uuid.uuid4())
			summary_data = _c.get_dataframe_summary(source)
			data = {
				"id": _id,
				"checksum": _c.get_checksum(source),
				"file": _c.rename_file(source, _id),
				"original": filename,
				"dataframe": summary_data["df"],
				"columns": summary_data["columns"]
			}
			self.schema_settings["input_data"].append(data)

	def remove_input_data(self, _id, reset_status=False):
		"""
		Remove an input data source defined by a source _id. If data have already been merged,
		reset data processing, or raise an error.

		Parameters
		----------
		_id: str
			Unique id for an input data source. View all input data from `input_data`

		Raises
		------
		TypeError if not a list of str.
		"""
		if self.schema_settings.get("working_data", {}).get("checksum"):
			if reset_status:
				del self.schema_settings["working_data"]["checksum"]
			else:
				e = "Permission required to reset `working_data`. Set `reset_status` to `True`."
				raise PermissionError(e)
		if self.schema_settings.get("input_data", []):
			self.schema_settings["input_data"] = [data for data in self.schema_settings["input_data"]
												  if data["id"] != _id]

	#########################################################################################
	# MERGE HELPERS
	#########################################################################################

	def order_and_key_input_data(self, *order_and_key):
		"""
		Reorder a list of input_data prior to merging, and add in the merge keys.

		Parameters
		----------
		order_and_key: list of dicts
			Each dict in the list has {id: input_data id, key: column_name for merge}

		Raises
		------
		ValueError not all input_data are assigned an order and key.
		"""
		self.validate_input_data
		reordered_data = []
		for oak in order_and_key:
			for data in self.input_data:
				columns = [c["name"] for c in data["columns"]]
				if oak["id"] == data["id"] and oak["key"] in columns:
					data["key"] = oak["key"]
					reordered_data.append(data)
		if len(reordered_data) != len(self.schema_settings["input_data"]):
			e = "List mismatch. Input-data different from list submitted for ordering."
			raise ValueError(e)
		self.schema_settings["input_data"] = reordered_data
		self._status = "READY_MERGE"

	def deduplicate_columns(self, idx, fmt=None, ignoreFirst=True):
		"""
		Source: https://stackoverflow.com/a/55405151
		Returns a new column list permitting deduplication of dataframes which may result from merge.

		Parameters
		----------
		idx: df.columns (i.e. the indexed column list)
		fmt: A string format that receives two arguments: name and a counter. By default: fmt='%s.%03d'
		ignoreFirst: Disable/enable postfixing of first element.

		Returns
		-------
		list of strings
			Updated column names
		"""
		idx = pd.Series(idx)
		duplicates = idx[idx.duplicated()].unique()
		fmt = '%s_%03d' if fmt is None else fmt
		for name in duplicates:
			dups = idx==name
			ret = [fmt%(name,i) if (i!=0 or not ignoreFirst) else name
				   for i in range(dups.sum())]
			idx.loc[dups] = ret
		# Fix any fields with the same name as any of the target fields
		for name in self.all_field_names:
			dups = idx==name
			ret = ["{}__dd".format(name) for i in range(dups.sum())]
			idx.loc[dups] = ret
		return pd.Index(idx)

	@property
	def working_column_list(self):
		if self.schema_settings.get("working_data"):
			return [c["name"] for c in self.schema_settings["working_data"]["columns"]]
		return []

	def working_data_field(self, column):
		if self.schema_settings.get("working_data"):
			for field in self.schema_settings["working_data"]["columns"]:
				if field["name"] == column:
					return field
		e = "Field `{}` is not in the working data.".format(column)
		raise KeyError(e)

	@property
	def working_dataframe(self):
		if "working_data" in self.schema_settings:
			source = self.directory + self.schema_settings["working_data"]["file"]
			return _c.get_dataframe(source, dtype=object)
		e = "No working data found."
		raise ValueError(e)

	@property
	def working_data(self):
		return deepcopy(self.schema_settings.get("working_data", {}))

	#########################################################################################
	# STRUCTURE HELPERS
	#########################################################################################

	def flatten_category_fields(self, structure, modifier=None):
		modifier_list = ["+", "-"]
		response = []
		for sublist in structure:
			if isinstance(sublist, list):
				response.extend(get_category_fields(sublist))
		if structure[0] == "CATEGORISE":
			for strut in _c.chunks(structure[1:], len(modifier_list)):
				if len(strut) < len(modifier_list):
					continue
				if strut[0] in modifier_list:
					if isinstance(strut[1], list):
						response.extend(get_category_fields(strut[1], modifier=strut[0]))
					if isinstance(strut[1], str):
						response.append(strut[0] + "::" + strut[1])
		if structure[0] != "CATEGORISE" and modifier is not None:
			for strut in structure[1:]:
				if isinstance(strut, str):
					response.append(modifier + "::" + strut)
				if isinstance(strut, list):
					response.extend(get_category_fields(strut, modifier=modifier))
		return response

	def set_field_structure_categories(self, modifier, column):
		"""
		If a structure `action` is `CATEGORISE`, then specify the terms available for
		categorisation. Each field must have a modifier, including the first (e.g. +A -B +C).

		The `modifier` is one of:

			- `-`: presence/absence of column values as true/false for a specific term
			- `+`:  unique terms in the field must be matched to the unique terms defined by the
			`field` `constraints`

		As with `set_structure`, the recursive step of managing nested structures is left to the
		calling function.

		Parameters
		----------
		modifier: str
			One of `-` or `+`
		column: str
			Must be a valid column from `working_column_list`
		"""
		if column not in self.working_column_list:
			return []
		category_list = [True, False]
		# Get the modifier: + for uniqueness, and - for boolean treatment
		if modifier == "+":
			category_list = list(self.working_dataframe[column].dropna().unique())
		structure_categories = {
			"terms": category_list,
			"column": column
		}
		return structure_categories

	def set_field_structure(self, structure_list):
		"""
		A recursive function which traverses a list defined by `*structure`, ensuring that the first
		term is an `action`, and that the subsequent terms conform to that action's requirements.
		Nested structures are permitted.

		The format for defining a `structure` is as follows::

			[action, column_name, [action, column_name]]

		e.g.::

			["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

		This permits the creation of quite expressive wrangling structures from simple building
		blocks.

		Parameters
		----------
		structure_list: list
			Each structure list must start with an `action`, with subsequent terms conforming to the
			requirements for that action. Nested actions defined by nested lists.
		"""
		# Sets or updates a structure, and sets any required categories
		structure = []
		for i, term in enumerate(structure_list):
			if i == 0:
				# Validate the rest of the structure_list first
				action = self.default_actions[term]
				if not action.has_valid_structure(self.working_column_list, structure_list[1:]):
					e = "Task action `{}` has invalid structure `{}`.".format(term, structure_list)
					raise ValueError(e)
				structure.append(action.settings)
				continue
			if isinstance(term, list):
				# Deal with nested structures
				structure.append(self.set_field_structure(term))
				continue
			if action.name == "NEW":
				# Special case for "NEW" action
				new_term = {
					"value": term,
					"type": _c.get_field_type(term)
				}
				structure.append(new_term)
				continue
			if term in action.modifier_names:
				structure.append(action.get_modifier(term))
				continue
			if term in self.working_column_list:
				structure.append(self.working_data_field(term))
				continue
		return structure

	@property
	def default_action_types(self):
		"""
		Default list of actions available to define methods. Returns only a list
		of types. Details for individual default actions can be returned with
		`default_action_settings`.

		Returns
		-------
		list
		"""
		return list(self.default_actions.keys())

	def default_action_settings(self, action):
		"""
		Get the default settings available for a specific action type.

		Parameters
		----------
		action: string
			A specific term for an action type (as listed in `default_action_types`).

		Returns
		-------
		dict, or empty dict if no such `action_type`
		"""
		if action in self.default_actions:
			return deepcopy(self.default_action[action].settings)
		return {}

	def build_default_actions(self):
		"""
		Build the default actions for presentation to the user as options.

		Returns
		-------
		dict of Actions
		"""
		default_actions = {action["name"]: Action(validate=False, **action)
						   for action in _c.get_settings("actions")["fields"]}
		return default_actions

	def build_structure_markdown(self, structure):
		"""
		Recursive function that iteratively builds a markdown version of a formal field structure.

		Returns
		-------
		list
		"""
		markdown = []
		for strut in structure:
			if isinstance(strut, list):
				markdown.append(self.build_structure_markdown(strut))
				continue
			if strut.get("name"):
				markdown.append(strut["name"])
				continue
			if strut.get("value"):
				markdown.append(strut["value"])
		return markdown

	#########################################################################################
	# CATEGORY HELPERS
	#########################################################################################

	def build_category_markdown(self, category_input):
		"""
		Converts category_terms dict into a markdown format::

			["term1", "term2", "term3"]

		Where the format for defining a `category` term as follows::

			`term_name::column_name`

		From::

			{
				"column": "column_name",
				"terms": [
					"term_1",
					"term_2",
					"term_3"
				]
			}
		"""
		markdown = []
		for column in category_input:
			for term in column["terms"]:
				markdown.append("{}::{}".format(term, column["column"]))
		return markdown

	#########################################################################################
	# VALIDATE, BUILD AND SAVE
	#########################################################################################

	@property
	def validate_input_data(self):
		"""
		Test input data for checksum errors.

		Raises
		------
		ValueError on checksum failure.
		"""
		if not self.schema_settings.get("input_data", []):
			e = "Empty list. No valid input data."
			raise ValueError(e)
		for data in self.schema_settings["input_data"]:
			source = self.directory + data["file"]
			if _c.get_checksum(source) != data["checksum"]:
				e = "Checksum error on input data `{}`".format(data["original"])
				raise ValueError(e)
		return True

	@property
	def validate_merge_data(self):
		"""
		Test input data ready to merge; that it has a merge key, and that the data in that column
		are unique.

		Raises
		------
		ValueError on uniqueness failure.
		"""
		self.validate_input_data
		for data in self.schema_settings["input_data"]:
			if not data.get("key"):
				e = "Missing merge key on input data `{}`".format(data["original"])
				raise ValueError(e)
			source = self.directory + data["file"]
			_c.check_column_unique(source, data["key"])
		return True

	@property
	def validate_merge(self):
		"""
		Validate merge output.

		Raises
		------
		ValueError on checksum failure.

		Returns
		-------
		bool: True for validates
		"""
		self.validate_merge_data
		df = _c.get_dataframe(self.directory + self.schema_settings["input_data"][0]["file"],
							  dtype = object)
		df_key = self.schema_settings["input_data"][0]["key"]
		for data in self.schema_settings["input_data"][1:]:
			dfm = _c.get_dataframe(self.directory + data["file"], dtype = object)
			dfm_key = data["key"]
			df = pd.merge(df, dfm, how="outer",
						  left_on=df_key, right_on=dfm_key,
						  indicator=False)
		# Deduplicate any columns after merge (and deduplicate the deduplicate in case of artifacts)
		df.columns = self.deduplicate_columns(self.deduplicate_columns(df.columns))
		# Save temporary file ... has to save & load for checksum validation
		_id = str(uuid.uuid4())
		filetype = self.schema_settings["working_data"]["file"].split(".")[-1]
		filename = "".join([_id, ".", filetype])
		source = self.directory + filename
		if filetype == "csv":
			df.to_csv(source, index=False)
		if filetype == "xlsx":
			df.to_excel(source, index=False)
		checksum = _c.get_checksum(source)
		_c.delete_file(source)
		if (self.schema_settings["working_data"]["checksum"] != checksum):
			e = "Merge validation checksum failure {} != {}".format(
				self.schema_settings["working_data"]["checksum"],
				checksum)
			raise ValueError(e)
		return True

	@property
	def validate_structure(self):
		"""
		Method validates structure formats.

		Raises
		------
		ValueError on structure failure.

		Returns
		-------
		bool: True for validates
		"""
		self.validates # First check the fields
		for field_name in self.all_field_names:
			# Test structure
			structure = self.field(field_name).get("structure")
			if not structure:
				e = "Structure: {}".format(field_name)
				raise ValueError(e)
			test_structure = self.build_structure_markdown(structure)
			if structure != self.set_field_structure(test_structure):
				e = "Structure for Field `{}` is not valid".format(field_name)
				raise ValueError(e)
			# Test structure categories
			category = self.field(field_name).get("constraints", {}).get("category_input")
			if category and self.field(field_name).get("constraints", {}).get("category"):
				# Needs to have both a set of terms derived from the columns, and a
				# defined set of terms to be categorised as...
				test_category = []
				for term in set(self.flatten_category_fields(test_structure)):
					term = term.split("::")
					modifier = term[0]
					# Just in case
					column = "::".join(term[1:])
					test_category.append(self.set_field_structure_categories(modifier, column))
				if (sorted(category, key=itemgetter("column")) !=
					sorted(test_category, key=itemgetter("column"))):
					# Equality test on list of dicts requires them to be in the same order
					e = "Category for Field `{}` is not valid".format(field_name)
					raise ValueError(e)
		return True

	@property
	def validate_category(self):
		"""
		Method validates category terms.

		Raises
		------
		ValueError on category failure.

		Returns
		-------
		bool: True for validates
		"""
		for field_name in self.all_field_names:
			schema_field = self.field(field_name)
			if schema_field.get("category"):
				# Test if the category and category_input constraints are valid
				# assigned is of the form: category: [term::column]
				# constraints of the form: category -> name | category_input -> column | terms
				category = self.category(field_name).get("assigned")
				if schema_field["type"] == "boolean":
					category_constraints = ["true", "false"]
				else:
					category_constraints = [c["name"] for c in
											schema_field["constraints"].get("category", {})]
				diff = set(category.keys()) - set(category_constraints)
				if diff:
					e = "Category for Field `{}` has invalid constraints `{}`"
					raise ValueError(e.format(field_name, diff))
				category_input = {}
				for terms in category.values():
					for term in terms:
						term = term.split("::")
						if not category_input.get(term[-1]):
							category_input[term[-1]] = []
						category_input[term[-1]].append("::".join(term[:-1]))
				category_input_columns = [c["column"] for c in
										  schema_field["constraints"].get("category_input", {})]
				diff = set(category_input.keys()) - set(category_input_columns)
				if diff:
					e = "Category for Field `{}` has invalid data columns `{}`"
					raise ValueError(e.format(field_name, diff))
				category_input_terms = [c["terms"] for c in
										schema_field["constraints"].get("category_input", {})]
				category_input_terms = [item for sublist in category_input_terms
										for item in sublist]
				category_terms = [item for sublist in category_input.values()
								  for item in sublist]
				diff = set(category_terms) - set(category_input_terms)
				if diff:
					e = "Category for Field `{}` has invalid input category terms `{}`"
					raise ValueError(e.format(field_name, diff))
				diff = len(category_terms) - len(set(category_terms))
				if diff:
					e = "Category for Field `{}` has duplicate input category terms"
					raise ValueError(e.format(field_name))
		return True

	@property
	def validate_filter(self):
		"""
		Method validates filter terms.

		Raises
		------
		ValueError on filter failure.

		Returns
		-------
		bool: True for validates
		"""
		for field_name in self.all_field_names:
			schema_field = self.field(field_name)
			if not schema_field.get("filter"):
				continue
			# Filter permitted
			if schema_field["type"] not in self.valid_filter_field_types:
				e = "Filter of field `{}` is not permitted.".format(schema_field["name"])
				raise PermissionError(e)
			# Foreign key valid
			if schema_field["filter"]["field"] not in self.all_field_names:
				e = "Filter foreign key `{}` not a valid field for this schema"
				raise ValueError(e.format(schema_field["filter"]["field"]))
			# Filter type valid
			default_filters = [f["name"] for f in self.default_filters["filter"]["modifiers"]]
			if schema_field["filter"]["modifiers"]["name"] not in default_filters:
				e = "Filter: `{}` is not a valid filter-type."
				raise TypeError(e.format(schema_field["filter"]["modifiers"]["name"]))
			# Filter date valid
			if schema_field["filter"]["modifiers"]["date"]:
				_c.check_date_format(schema_field["type"],
									 schema_field["filter"]["modifiers"]["date"])
		return True

	@property
	def validate(self):
		"""
		Method validates all steps. Sets `READY_TRANSFORM` if all pass.

		Returns
		-------
		bool: True for validates
		"""
		self.validate_input_data
		self.validate_merge_data
		self.validate_merge
		self.validate_structure
		self.validate_category
		self.validate_filter
		self._status = "READY_TRANSFORM"
		return True

	def build_action(self, **action):
		"""
		For a list of actions, defined as dictionaries, create and return Action objects.

		Parameters
		----------
		field: dictionary of Action parameters

		Raises
		------
		ValueError: if action fails validation

		Returns
		-------
		Action
		"""
		if not isinstance(action, dict) or not all(key in action for key in self.required_field_terms):
			e = "Action is not a valid dictionary"
			raise ValueError(e)
		action = Action(**action)
		if not action.validates:
			e = "Action `{}` of type `{}` does not validate".format(_name, _type)
			raise ValueError(e)
		return action

	def build(self):
		"""
		Build and validate the Method. Note, this replaces the Schema base-class.
		"""
		self.schema_settings["fields"] = [self.build_field(validate=False, **field) for field in
										  self.schema_settings.get("fields", [])]
		if not self.directory:
			e = "Action is not a valid dictionary"
			raise ValueError(e)
		self.set_directory(self.directory)
		self._status = self.schema_settings.get("status", self._status)

	def save_data(self, df, filetype="xlsx"):
		"""
		Generate a unique filename for a dataframe, save to the working directory, and return the
		unique filename and data summary.

		Parameters
		----------
		df: Pandas DataFrame
		filetype: Save the dataframe as a particular type. Default is "CSV".

		Returns
		-------
		dict
			Keys include: id, filename, checksum, df header, columns
		"""
		if df.empty:
			e = "Cannot save empty DataFrame."
			raise ValueError(e)
		if filetype not in ["xlsx", "csv"]:
			e = "`{}` not supported for saving DataFrame".format(filetype)
			raise TypeError(e)
		_id = str(uuid.uuid4())
		filename = "".join([_id, ".", filetype])
		source = self.directory + filename
		if filetype == "csv":
			df.to_csv(source, index=False)
		if filetype == "xlsx":
			df.to_excel(source, index=False)
		summary_data = _c.get_dataframe_summary(source)
		data = {
			"id": _id,
			"checksum": _c.get_checksum(source),
			"file": filename,
			"dataframe": summary_data["df"],
			"columns": summary_data["columns"]
		}
		return data

	def save(self, directory=None, filename=None, overwrite=False, created_by=None):
		if not directory: directory = self.directory
		self.schema_settings["status"] = self._status
		super().save(directory=directory, filename=filename,
					 overwrite=overwrite, created_by=created_by)

	#########################################################################################
	# HELP
	#########################################################################################

	def help(self, option=None):
		"""
		Get generic help, or help on a specific method.

		Paramater
		---------
		option: str
			Any of None, 'status', 'merge', 'structure', 'category', 'filter', 'transform', 'error'.

		Returns
		-------
		Help
		"""
		response = ""
		if not option or option not in ["status", "merge", "structure", "category",
										  "filter", "transform", "error"]:
			response = HELP_RESPONSE["default"].format(self.status)
		elif option != "status":
			response = HELP_RESPONSE[option]
			if option == "merge":
				for data in self.input_data:
					_id = data["id"]
					_df = pd.DataFrame(data["dataframe"])
					_df = tabulate(_df, headers="keys", tablefmt="fancy_grid")
					response += HELP_RESPONSE["data"].format(_id, _df)
			if option == "structure":
				response = response.format(self.all_field_names,
										   self.default_action_types,
										   self.working_column_list)
				if "working_data" in self.schema_settings:
					_id = self.schema_settings["working_data"]["id"]
					_df = pd.DataFrame(self.schema_settings["working_data"]["dataframe"])
					_df = tabulate(_df, headers="keys", tablefmt="fancy_grid")
					response += HELP_RESPONSE["data"].format(_id, _df)
			if option == "category":
				category_fields = []
				for field_name in self.all_field_names:
					if self.field(field_name).get("constraints", {}).get("category"):
						category_fields.append(field_name)
				response = response.format(category_fields)
			if option == "filter":
				filter_fields = []
				for field_name in self.all_field_names:
					if self.field(field_name)["type"] in self.valid_filter_field_types:
						filter_fields.append(field_name)
				response = response.format(filter_fields)
		# `status` request
		response += HELP_RESPONSE["status"].format(self.status)
		return response

HELP_RESPONSE = {
	"default": """
**whyqd** provides data wrangling simplicity, complete audit transparency, and at speed.

To get help, type:

	>>> method.help(option)

Where `option` can be any of:

	status
	merge
	structure
	category
	filter
	transform
	error

`status` will return the current method status, and your mostly likely next steps. The other options
will return methodology, and output of that option's result (if appropriate). The `error` will
present an error trace and attempt to guide you to fix the process problem.""",
	"merge": """
`merge` will join, in order from right to left, your input data on a common column.

To add input data, where `input_data` is a filename, or list of filenames:

	>>> method.add_input_data(input_data)

To remove input data, where `id` is the unique id for that input data:

	>>> method.remove_input_data(id)

Prepare an `order_and_key` list, where each dict in the list has:

	{id: input_data id, key: column_name for merge}

Run the merge by calling (and, optionally - if you need to overwrite an existing merge - setting
`overwrite_working=True`):

	>>> method.merge(order_and_key, overwrite_working=True)

To view your existing `input_data`:

	>>> method.input_data
""",
	"structure": """
`structure` is the core of the wrangling process and is the process where you define the actions
which must be performed to restructure your working data.

Create a list of methods of the form:

	{{
		"schema_field1": ["action", "column_name1", ["action", "column_name2"]],
		"schema_field2": ["action", "column_name1", "modifier", ["action", "column_name2"]],
	}}

The format for defining a `structure` is as follows::

	[action, column_name, [action, column_name]]

e.g.::

	["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

This permits the creation of quite expressive wrangling structures from simple building
blocks.

The schema for this method consists of the following terms:

{}

The actions:

{}

The columns from your working data:

{}
""",
	"category": """
Provide a list of categories of the form::

	{{
		"schema_field1": {{
			"category_1": ["term1", "term2", "term3"],
			"category_2": ["term4", "term5", "term6"]
		}}
	}}

The format for defining a `category` term as follows::

	`term_name::column_name`

Get a list of available terms, and the categories for assignment, by calling::

	>>> method.category(field_name)

Once your data are prepared as above::

	>>> method.set_category(**category)

Field names requiring categorisation are: {}
""",
	"filter": """
Set date filters on any date-type fields. **whyqd** offers only rudimentary post-
wrangling functionality. Filters are there to, for example, facilitate importing data
outside the bounds of a previous import.

This is also an optional step. By default, if no filters are present, the transformed output
will include `ALL` data.

Parameters
----------
field_name: str
	Name of field on which filters to be set
filter_name: str
	Name of filter type from the list of valid filter names
filter_date: str (optional)
	A date in the format specified by the field type
foreign_field: str (optional)
	Name of field to which filter will be applied. Defaults to `field_name`

There are four filter_names:

	ALL: default, import all data
	LATEST: only the latest date
	BEFORE: before a specified date
	AFTER: after a specified date

BEFORE and AFTER take an optional `foreign_field` term for filtering on that column. e.g.

	>>> method.set_filter("occupation_state_date", "AFTER", "2019-09-01", "ba_ref")

Filters references in column `ba_ref` by dates in column `occupation_state_date` after `2019-09-01`.

Field names which can be filtered are: {}
""",
	"data": """

Data id: {}

{}
""",
	"status": """

Current method status: `{}`"""
}