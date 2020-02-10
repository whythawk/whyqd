"""
Miscellaneous tools for supporting core functionality.
"""
import json
import re
import copy
import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path, PurePath
import pandas as pd

short_rows = 3
long_rows = 5

def get_now():
	return date.isoformat(datetime.now())

def check_path(directory):
	Path(directory).mkdir(parents=True, exist_ok=True)

def check_source(source):
	if Path(source).exists():
		return True
	else:
		e = "Source at `{}` not found.".format(source)
		raise FileNotFoundError(e)

def get_path():
	return Path(__file__).resolve().parent

def rename_file(source, newname):
	p = Path(source)
	newname = "{}{}".format(newname, p.suffix)
	p.rename(Path(p.parent, newname))
	return newname

def delete_file(source):
	Path(source).unlink(missing_ok=True)

def get_checksum(source):
	checksum = hashlib.blake2b()
	with open(source, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			checksum.update(chunk)
	return checksum.hexdigest()

def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	# https://stackoverflow.com/a/976918/295606
	for i in range(0, len(l), n):
		yield l[i:i + n]

###################################################################################################
### JSON, Schema and Action get and set
###################################################################################################

def load_json(source):
	"""
	Load and return a JSON file, if it exists.

	Paramaters
	----------
	source: the filename & path to open

	Raises
	------
	JSONDecoderError if not a valid json file
	FileNotFoundError if not a valid source

	Returns
	-------
	dict
	"""
	check_source(source)
	with open(source, "r") as f:
		try:
			return json.load(f)
		except json.decoder.JSONDecodeError:
			e = "File at `{}` not valid json.".format(source)
			raise json.decoder.JSONDecodeError(e)

def save_json(data, source, overwrite=False):
	"""
	Save a dictionary as a json file. Return `False` if file `source` already exists and not
	`overwrite`.

	Parameters
	----------
	data: dictionary to be saved
	source: the filename to open, including path
	overwrite: bool, True if overwrite existing file

	Returns
	-------
	bool, True if saved, False if already exists without `overwrite`
	"""
	if Path(source).exists() and not overwrite:
		e = "`{}` already exists. Set `overwrite` to `True`.".format(source)
		raise FileExistsError(e)
	with open(source, "w") as f:
		json.dump(data, f)
	return True

JSON_SETTING_FILES = {
	"schema": "default_fields.json",
	"filters": "default_filters.json",
	"actions": "default_actions.json"
}

def get_settings(choice):
	"""
	Return the complete json settings for a json `filename` as a dict.
	"""
	filename = JSON_SETTING_FILES[choice]
	source = PurePath.joinpath(get_path(), "settings", filename)
	return load_json(source)

def get_field_settings(field_type, setting_file="schema"):
	fields = get_settings(setting_file)["fields"]
	for f in fields:
		if f["type"] == field_type:
			return f
	return {}

def get_field_type(field_type):
	if isinstance(field_type, str): return "string"
	if isinstance(field_type, bool): return "boolean"
	if isinstance(field_type, int): return "integer"
	if isinstance(field_type, float): return "number"
	if isinstance(field_type, list): return "array"
	if isinstance(field_type, dict): return "object"
	return None

###################################################################################################
### Dataframe get and set
###################################################################################################

def get_dataframe(source,
				  foreign_key = None,
				  filetype = None,
				  **kwargs):
	"""
	For a given file and directory, return an initial set of rows along with a list of the columns
	and types for each column.

	Will determine filetype (CSV or XLSX) by bruteforce, but can accept a non-compulsory filetype
	kwargs.

	Parameters
	----------
	source: Source filename;
	filetype: (Optional) must be in ['CSV', 'XLS', 'XLSX']
	kwargs: additional keyword-arguments for Pandas;

	Returns
	-------
	Dataframe (if fails, returns empty dataframe)
	"""
	check_source(source)
	# If the dtypes have not been set, then ensure that any provided foreign_key remains untouched
	# i.e. no forcing of text to numbers
	if foreign_key and "dtype" not in kwargs:
		kwargs["dtype"] = {
			foreign_key: "string"
		}
	# Get file delimiter
	if filetype and filetype.upper() in ["CSV", "XLS", "XLSX"]:
		filetype = filetype.upper()
	else:
		filetype = source.split(".")[-1].upper()
	if filetype == "XLSX" or filetype == "XLS":
		df = pd.read_excel(source, **kwargs)
	elif filetype == "CSV":
		kwargs["encoding"] = kwargs.get("encoding", "ISO-8859-1")
		kwargs["iterator"] = True
		kwargs["chunk_size"] = kwargs.get("chunk_size", 100000)
		df = pd.read_csv(source, **kwargs)
		df_chunks = []
		loop = True
		while loop:
			try:
				chunk = df.get_chunk(kwargs["chunk_size"])
				df_chunks.append(chunk)
			except StopIteration:
				loop = False
		df = pd.concat(df_chunks, ignore_index=True)
	return df

def get_dataframe_summary(source,
						  rows = short_rows,
						  foreign_key = None,
						  **kwargs):

	"""
	For a given file and directory, return an initial set of rows along with a list of the columns
	and types for each column.

	Will determine filetype (CSV or XLSX) by bruteforce, but can accept a non-compulsory filetype
	kwargs.

	Parameters
	----------
	source: Source filename;
	rows: Number of rows to return (to reduce load times), default = short_rows;
	foreign_key: Column name of field where data are not to be messed with;
	kwargs: additional keyword-arguments for Pandas;

	Returns
	-------
	dict:
		"data": { "df": df.head(rows).to_dict(), "columns": list of dicts with column names & type}
	"""
	# limit rows for dataframe
	kwargs["nrows"] = rows
	filetype = kwargs.get("filetype")
	if filetype: del kwargs["filetype"]
	# Get dataframe
	df = get_dataframe(source, foreign_key = foreign_key, filetype = filetype, **kwargs)
	# Prepare summary
	kwargs = {
		"df": df.head(rows).to_dict(),
		"columns": [
				{"name": k, "type": "number"} if v in ["float64", "int64"]
				else {"name": k, "type": "date"} if v in ["datetime64[ns]"]
				else {"name": k, "type": "string"}
			for k,v in df.dtypes.apply(lambda x: x.name).to_dict().items()]
	}
	return kwargs

def check_column_unique(source, key):
	"""
	Test a column in a dataframe to ensure all values are unique.

	Parameters
	----------
	source: Source filename
	key: Column name of field where data are to be tested for uniqueness

	Raises
	------
	ValueError if not unique

	Returns
	-------
	bool, True if unique
	"""
	df = get_dataframe(source, key)
	if len(df[key]) != len(df[key].unique()):
		e = "'{}' contains non-unique rows in column `{}`".format(source, key)
		raise ValueError(e)
	return True