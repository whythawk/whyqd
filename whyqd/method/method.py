"""
Target Schema
-------------

Define and manage a structural metadata schema as the target for a wrangling process.

**whyqd** munges input-data into a target schema where automated scripts can perform further cleaning
and validation. Data produced will conform to the schema but are in an interim state. The schema
process is similar to FrictionlessData.io, but without its error-checking and validation components.

Input data structure
--------------------

If you are working with tabular data, you're probably familiar with basic machine-readability
requirements. **whyqd** requires the basics of
"""
import os, uuid
from copy import deepcopy
import pandas as pd

import whyqd.common as _c
from whyqd.schema import Schema

STATUS_CODES = {
	"WAITING": "Waiting ...",
	"PROCESSING": "Processing ...",
	"READY_MERGE": "Ready to Merge",
	"READY_STRUCTURE": "Ready to Structure",
	"READY_CATEGORIES": "Ready to Categories",
	"READY_FILTER": "Ready to Filter",
	"READY_TRANSFORM": "Ready to Transform",
	"READY_IMPORT": "Ready to Import",
	"CREATE_ERROR": "Create Error",
	"MERGE_ERROR": "Merge Error",
	"STRUCTURE_ERROR": "Structure Error",
	"CATEGORISE_ERROR": "Categorise Error",
	"TRANSFORMATION_ERROR": "Transform Error",
	"IMPORT_ERROR": "Import Error",
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
		if "directory" in kwargs:
			self.set_directory(kwargs["directory"])
			del kwargs["directory"]
		if "constructors" in kwargs:
			self.set_constructors(kwargs["constructors"])
			del kwargs["constructors"]
		if "input_data" in kwargs:
			self.add_input_data(kwargs["input_data"])
			del kwargs["input_data"]
		super().__init__(source=source, **kwargs)
		self.default_actions = self.build_default_actions()

	def merge(self, overwrite_working=False):
		"""
		Merge input data on a key column.

		Paramaters
		----------
		overwrite_working: bool, permission to overwrite existing working data

		TO_DO
		-----
		While `merge` validates column uniqueness prior to merge, if the column is not unique there
		is nothing the user can do about it (without manually going and refixing the input data).
		Some sort of uniqueness fix required (probably using the filters).
		"""
		if self._status in STATUS_CODES.keys() - ["READY_MERGE", "READY_STRUCTURE", "READY_CATEGORIES",
												  "READY_FILTER", "READY_TRANSFORM", "PROCESS_COMPLETE",
												  "MERGE_ERROR"]:
			e = "Current status: `{}` - performing `merge` is not permitted.".format(self.status)
			raise PermissionError(e)
		self.validate_merge_data
		if ("working_data" in self.schema_settings and
			not self.schema_settings["working_data"].get("checksum")):
			e = "Permission required to overwrite `working_data`. Set `overwrite_working` to `True`."
			raise PermissionError(e)
		df = _c.get_dataframe(self.directory + self.schema_settings["input_data"][0]["file"],
							  dtype = "string")
		df_key = self.schema_settings["input_data"][0]["key"]
		for data in self.schema_settings["input_data"][1:]:
			dfm = _c.get_dataframe(self.directory + data["file"], dtype = "string")
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
		#df.to_excel(dir_source + f, index=False)

		# Review for any existing actions
		# self.validate_actions

		self._status = "READY_STRUCTURE"

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

			NEW:			Add in a new column, and populate it according to the value in the "new"
							constraint;
			RENAME:			If only 1 item in list of source fields, then rename that field;
			ORDER:			If > 1 1 item in list of source fields, pick the value from the column,
							replacing each value with one from the next in the order of the provided
							fields;
			ORDER_NEW:		As in ORDER, but replacing each value with one associated with a
							newer "dateorder" constraint;
							MODIFIER: + between terms for source and source_date;
			ORDER_OLD:		As in ORDER, but replacing each value with one associated with an
							older "dateorder" constraint;
							MODIFIER: + between terms for source and source_date;
			CALCULATE:		Only if of "type" = "float64" (or which can be forced to float64);
							MODIFIER: + or - before each term to define whether add or subtract;
			JOIN:			Only if of "type" = "object", join text with " ".join();
			CATEGORISE:		Only if of "type" = "string"; look for associated constraint, "categorise"
							where True = keep a list of categories, False = set True if terms found
							in list;

			MODIFIER: + before terms where column values are to be classified as unique;
					  - before terms where column values are treated as boolean;
		"""
		if self._status in STATUS_CODES.keys() - ["READY_STRUCTURE", "READY_CATEGORIES", "READY_FILTER",
												  "READY_TRANSFORM", "PROCESS_COMPLETE", "STRUCTURE_ERROR"]:
			e = "Current status: `{}` - performing `structure` is not permitted.".format(self.status)
			raise PermissionError(e)
		for field_name in kwargs:
			if field_name not in self.all_field_names:
				e = "Term `{}` not a valid field for this schema.".format(field_name)
				raise ValueError(e)
			schema_field = self.field(field_name)
			schema_field["structure"] = self.set_field_structure(*kwargs[field_name])
			# Set unique field structure categories
			schema_field["category"] = []
			for term in set(self.flatten_category_fields(kwargs[field_name])):
				term = term.split("::")
				modifier = term[0]
				# Just in case
				column = "::".join(term[1:])
				schema_field["category"].append(self.set_field_structure_categories(modifier, column))
		# Validation would not add in the new values
		self.set_field(validate=False, **schema_field)

	# SUPPORT FUNCTIONS

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

	@property
	def input_data(self):
		return deepcopy(self.schema_settings.get("input_data", []))

	def add_input_data(self, input_data):
		"""
		Provide a list of strings, each the filename of input data for wrangling.

		Parameters
		----------
		input_data: str or list of str

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
			source = self.directory + filename
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

	def order_and_key_input_data(self, *order_and_key):
		"""
		Reorder a list of input_data prior to merging, and add in the merge keys.

		Parameters
		----------
		order_and_key: list of dicts
			Each dict in the list has {_id: input_data _id, key: column_name for merge}

		Raises
		------
		ValueError not all input_data are assigned an order and key.
		"""
		self.validate_input_data
		reordered_data = []
		for ok in order_and_key:
			for data in self.schema_settings["input_data"]:
				columns = [c["name"] for c in data["columns"]]
				if ok["id"] == data["id"] and ok["key"] in columns:
					data["key"] = ok["key"]
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
	def working_data(self):
		if "working_data" in self.schema_settings:
			source = self.directory + self.schema_settings["working_data"]["file"]
			return _c.get_dataframe(source, dtype="string")
		e = "No working data found."
		raise ValueError(e)

	# SET, UPDATE AND BUILD STRUCTURES (ACTION LISTS)

	def flatten_category_fields(self, structure, modifier=None):
		response = []
		for sublist in structure:
			if isinstance(sublist, list):
				response.extend(get_category_fields(sublist))
		if structure[0] == "CATEGORISE":
			for strut in chunks(structure[1:]):
				if len(strut) < 2:
					continue
				if strut[0] in ["+", "-"]:
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
			category_list = list(self.working_data[column].dropna().unique())
		structure_categories = {
			"terms": category_list,
			"column": column
		}
		return structure_categories

	def set_field_structure(self, *structure_list):
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
				if action.name == "CATEGORISE":
					# do something to categorise this structure
				structure.append(action.settings)
				continue
			if isinstance(term, list):
				# Deal with nested structures
				structure.append(self.set_field_structure(*term))
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

	def default_field_settings(self, action):
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

	# VALIDATE, BUILD AND SAVE

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
		Build and validate the Method. Note, this subclasses the Schema base-class.
		"""
		if "directory" not in self.schema_settings:
			e = "Action is not a valid dictionary"
			raise ValueError(e)
		self.set_directory(self.schema_settings["directory"])
		self._status = self.schema_settings.get("status", self._status)
		self.schema_settings["fields"] = [self.build_action(**action) for action in
										  self.schema_settings["fields"]]

	def save_data(self, df, filetype="XLSX"):
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
		if filetype not in ["XLSX", "CSV"]:
			e = "`{}` not supported for saving DataFrame".format(filetype)
			raise TypeError(e)
		_id = str(uuid.uuid4())
		filename = "".join([_id, ".", filetype])
		source = self.directory + filename
		if filetype == "CSV":
			df.to_csv(source, index=False)
		if filetype == "XLSX":
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