"""
Transformation functions to perform wrangling according to a defined method. Assumes the method
is valid.
"""
import pandas as pd
import numpy as np
import uuid

import whyqd.common as _c

def perform_transform(df, field_name, field_type, structure, category = None):
	"""
	A recursive transformation. A method should be a list fields upon which actions are applied, but
	each field may have nested sub-fields requiring their own actions. Before the action on the
	current field can be completed, it is necessary to perform the actions on each sub-field.

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0
	category: list
		List defining unique terms to be categorised

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	perform = {
		"ORDER": transform_by_order,
		"ORDER_NEW": transform_by_order_by_date,
		"ORDER_OLD": transform_by_order_by_date,
		"CALCULATE": transform_by_calculation,
		"JOIN": transform_by_joining,
		"CATEGORISE": transform_by_categorisation,
		"NEW": transform_by_new_field,
		"RENAME": transform_by_rename
	}
	# Analyse requirements for this method
	if len(structure) < 2 or structure[0]["type"] != "action":
		e = "Field `{}` has invalid method. Please review.".format(field_name)
		raise ValueError(e)
	action = structure[0]
	# Recursive check ...
	flattened_structure = [action]
	for i, field in enumerate(structure[1:]):
		if isinstance(field, list):
			# Need to create a temporary column ... the action will be performed here
			# then this nested structure will be replaced by the output of this new column
			temp_name = "nested_" + str(uuid.uuid4())
			df = perform_transform(df, temp_name, field_type, field, category=category)
			field = {
				"name": temp_name,
				"type": "nested"
			}
		flattened_structure.append(field)
	# Actions: ORDER / ORDER_NEW / ORDER_OLD / CALCULATE / JOIN / CATEGORISE / NEW / RENAME
	if action["name"] == "CATEGORISE":
		return perform[action["name"]](df, field_name, field_type,
									   flattened_structure, category=category)
	return perform[action["name"]](df, field_name, flattened_structure)

def transform_by_rename(df, field_name, structure):
	"""
	Perform a default transformation, simply renaming the field to the schema field.

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	# Analyse requirements for this method
	if len(structure) != 2 or structure[0]["name"] != "RENAME":
		e = "Field `{}` has invalid RENAME method. Please review.".format(field_name)
		raise ValueError(e)
	# Rename, note, can only be one field if a rename ...
	# https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rename.html
	# {'from': 'too'}
	df.rename(index=str,
			  columns= {structure[1]["name"]: field_name},
			  inplace=True)
	return df

def transform_by_new_field(df, field_name, structure):
	"""
	Add a new field to a dataframe and set its value to the default provided.

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	if len(structure) != 2 or structure[0]["name"] != "NEW":
		e = "Field `{}` has invalid NEW method. Please review.".format(field_name)
		raise ValueError(e)
	# Add field, note, can only be one field if new ...
	df.loc[:, field_name] = structure[1]["value"]
	return df

def transform_by_joining(df, field_name, structure):
	"""
	Join a list of columns together with a space (i.e. concatenating text in multiple fields).

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	if len(structure) < 2 or structure[0]["name"] != "JOIN":
		e = "Field `{}` has invalid JOIN method. Please review.".format(field_name)
		raise ValueError(e)
	fields = [field["name"] for field in structure[1:]]
	# https://stackoverflow.com/a/45976632
	df.loc[:, field_name] = df.loc[:, fields].apply(lambda x: "" if x.isnull().all() else
															  " ".join(x.dropna().astype(str)).strip(),
													axis=1)
	return df

def transform_by_order(df, field_name, structure):
	"""
	Create a new field by iterating over a list of fields and picking the next value in the list.

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	if len(structure) < 2 or structure[0]["name"] != "ORDER":
		e = "Field `{}` has invalid ORDER method. Please review.".format(field_name)
		raise ValueError(e)
	fields = [field["name"] for field in structure[1:]]
	if len(fields) > 1:
		df.rename(index=str, columns= {fields[0]: field_name}, inplace=True)
		for field in fields[1:]:
			df.loc[:, field_name] = df.apply(lambda x: (x[field]
														if pd.notnull(x[field])
														else x[field_name]),
											  axis=1)
	else:
		# Deal with the single case
		structure[1]["name"] = "RENAME"
		return transform_by_rename(df, field_name, structure)
	return df

def transform_by_order_by_date(df, field_name, structure):
	"""
	Create a new field by iterating over a list of fields and picking the newest or oldest value in
	the list. Requires a "datename" constraint, otherwise it defaults to an ORDER action.

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	if len(structure) < 4 or not structure[0]["name"].startswith("ORDER_"):
		e = "Field `{}` has invalid ORDER_BY method. Please review.".format(field_name)
		raise ValueError(e)
	action = structure[0]["name"].split("_")
	fields = [field["name"] for field in structure[1:]]
	base_date = None
	# Requires sets of 3 terms: field, +, date_field
	term_set = len(structure[0]["structure"])
	for data, modifier, date in _c.chunks(fields, term_set):
		if modifier != "+":
			e = "Field `{}` has invalid ORDER_BY method. Please review.".format(field_name)
			raise ValueError(e)
		if not base_date:
			# Start the comparison on the next round
			df.rename(index=str, columns= {data: field_name}, inplace=True)
			base_date = date
			if data == date:
				# Just comparing date columns
				base_date = field_name
			df.loc[:, base_date] = df.loc[:, base_date].apply(lambda x: pd.to_datetime(_c.parse_dates(x),
																					   errors="coerce"))
			continue
		# np.where date is <> base_date and don't replace value with null
		# logic: if test_date not null & base_date <> test_date
		# False if (test_date == nan) | (base_date == nan) | base_date >< test_date
		# Therefore we need to test again for the alternatives
		df.loc[:, date] = df.loc[:, date].apply(lambda x: pd.to_datetime(_c.parse_dates(x),
																		 errors="coerce"))
		if action[1] == "NEW":
			df.loc[:, field_name] = np.where(~pd.notnull(df[date]) | (df[base_date] > df[date]),
											  np.where(pd.notnull(df[field_name]),
													   df[field_name], df[data]),
											  np.where(pd.notnull(df[data]),
													   df[data], df[field_name]))
			if base_date != field_name:
				df.loc[:, base_date] = np.where(~pd.notnull(df[date]) | (df[base_date] > df[date]),
												np.where(pd.notnull(df[base_date]),
														 df[base_date], df[date]),
												np.where(pd.notnull(df[date]),
														 df[date], df[base_date]))
		if action[1] == "OLD":
			df.loc[:, field_name] = np.where(~pd.notnull(df[date]) | (df[base_date] < df[date]),
											  np.where(pd.notnull(df[field_name]),
													   df[field_name], df[data]),
											  np.where(pd.notnull(df[data]),
													   df[data], df[field_name]))
			if base_date != field_name:
				df.loc[:, base_date] = np.where(~pd.notnull(df[date]) | (df[base_date] < df[date]),
												np.where(pd.notnull(df[base_date]),
														 df[base_date], df[date]),
												np.where(pd.notnull(df[date]),
														 df[date], df[base_date]))
	return df

def transform_by_calculation(df, field_name, structure):
	"""
	Calculate the value of a field derived from the values of other fields. Requires a constraint
	indicating whether the fields should be ADD or SUB from the current total.

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	if len(structure) < 3 or structure[0]["name"] != "CALCULATE":
		e = "Field `{}` has invalid CALCULATE method. Please review.".format(field_name)
		raise ValueError(e)
	# Requires sets of 2 terms: + or -, field
	term_set = len(structure[0]["structure"])
	add_fields = [field["name"] for modifier, field in _c.chunks(structure[1:], term_set)
				  if modifier["name"] == "+"]
	sub_fields = [field["name"] for modifier, field in _c.chunks(structure[1:], term_set)
				  if modifier["name"] == "-"]
	for field in add_fields + sub_fields:
		df.loc[:, field] = df.loc[:, field].apply(lambda x: _c.parse_float(x))
	df.loc[:, field_name] = df[add_fields].abs().sum(axis=1) - df[sub_fields].abs().sum(axis=1)
	return df

def transform_by_categorisation(df, field_name, field_type, structure, category = None):
	"""
	Produce categories from terms or headers. There are three categorisation options:

		1. Term-data are categories derived from values in the data,
		2. Header-data are terms derived from the header name and boolean True for any value,
		3. "Boolean"-data, the category itself is True/False. Default in a boolean is True.

	Categorisation is a special case, requiring both method fields, and method categories, along
	with the schema field_name field to lookup the required term definitions.

	Parameters
	----------
	df: DataFrame
		Working data to be transformed
	field_name: str
		Name of the target schema field
	structure: list
		List of fields with restructuring action defined by term 0
	category: list
		List defining unique terms to be categorised

	Returns
	-------
	Dataframe
		Containing the implementation of all nested transformations
	"""
	if len(structure) < 2 or structure[0]["name"] != "CATEGORISE" or not category:
		e = "Field `{}` has invalid CATEGORISE method. Please review.".format(field_name)
		raise ValueError(e)
	# Fields are in sets of 2 terms: + or -, field
	# The modifier defines one of two approaches:
	#   '+': The terms in the field are used to identify the schema category
	#   '-': Non-null terms indicate presence of a schema category
	# If field type is 'array', then the destination terms are lists;
	# If field type is 'boolean', then the default term is True;
	is_array = True if field_type == "array" else False
	is_boolean = True if field_type == "boolean" else False
	# Sort out boolean term names before they cause further pain, correct later ...
	if is_boolean:
		for c in category:
			if c["name"]: c["name"] = "true"
			else: c["name"] = "false"
	default = "None" if is_array else is_boolean
	# Set the field according to the default
	#https://stackoverflow.com/a/31469249
	df[field_name] = [[] for _ in range(len(df))] if is_array else default
	# Develop the terms and conditions to assess membership of a category
	# Requires sets of 2 terms: + or -, field
	new_field = []
	term_set = len(structure[0]["structure"])
	all_terms = [c["name"] for c in category]
	# Any fields modified below must be restored: (tmp_column, original_column)
	modified_fields = []
	for modifier, field in _c.chunks(structure[1:], term_set):
		# https://docs.scipy.org/doc/numpy/reference/generated/numpy.select.html
		# Extract only the terms valid for this particular field
		terms = []
		for field_term in all_terms:
			for f in category:
				if f["name"] == field_term:
					for c in f["category_input"]:
						if c["column"] == field["name"]:
							terms.extend([field_term for t in c["terms"]])
					break
		if modifier["name"] == "+":
			conditions = [df[field["name"]].isin([t for subterms in
												  [item["terms"] for category_input in category
												   for item in category_input["category_input"]
												   if category_input["name"] == field_term]
												  for t in subterms])
						  for field_term in terms]
		else:
			# Modifier is -, so can make certain assumptions
			# - Terms are categorised as True or False, so choices are only True or False
			# - However, all terms allocated to 'true' will fail (since True on default is True no matter)
			# - User may return both True / False or only one
			# - If both True and False, keep False. If True, convert the True to False
			# Create temporary column to preserve data
			if df[field["name"]].dtype in ["float64", "int64", "datetime64[ns]"]:
				tmp = "tmp_" + str(uuid.uuid4())
				modified_fields.append((tmp, field["name"]))
				df[tmp] = df[field["name"]].copy()
			# Ensure any numerical zeros are nan'ed +
			if df[field["name"]].dtype in ["float64", "int64"]:
				df[field["name"]] = df[field["name"]].replace({0:np.nan, 0.0:np.nan})
			if df[field["name"]].dtype in ["datetime64[ns]"]:
				df.loc[:, field["name"]] = df.loc[:, field["name"]].apply(lambda x: pd.to_datetime(_c.parse_dates(x),
																								   errors="coerce"))
			conditions = [pd.notnull(df[field["name"]])
						  if category["fields"][field_term]["fields"][0]["name"] else
						  ~pd.notnull(df[field["name"]])
						  for field_term in terms]
		if is_boolean and modifier["name"] == "-":
			# if len(terms) == 1 and 'false', do nothing; if 'true', invert;
			# if len(terms) == 2, use 'false' only
			if "true" in terms:
				# We need to correct for the disaster of 'true'
				invrt = dict(zip(terms, conditions))
				if len(terms) == 1:
					invrt["false"] = ~invrt["true"]
				terms = [t for t in invrt.keys() if t != "true"]
				conditions = [invrt["false"]]
		# Only two terms, True or False. Reset the dictionary names
		if is_boolean and "false" in terms:
			terms = [False if t == "false" else t for t in terms]
		if not is_array:
			# Set the field terms immediately for membership, note, if no data defaults to current
			# i.e. this is equivalent to order, but with category data
			df[field_name] = np.select(conditions, terms, default=df[field_name])
		else:
			if terms and conditions:
				new_field.append(np.select(conditions, terms, default="none").tolist())
	# If a list of terms, organise the nested lists and then set the new field
	if is_array:
		# Sorted to avoid hashing errors later ...
		new_field = [sorted(list(set(x))) for x in zip(*new_field)]
		for n in new_field:
			if "none" in n: n.remove("none")
		if new_field:
			df[field_name] = new_field
	# Finally, fix the artifact columns introduced in the dataframe in case these are used elsewhere
	for tmp, original in modified_fields:
		df[original] = df[tmp].copy()
		del df[tmp]
	return df