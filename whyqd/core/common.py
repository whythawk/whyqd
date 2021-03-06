"""
Miscellaneous tools for supporting core functionality.
"""
import json
import sys, re
import copy
import hashlib
from urllib.parse import urlparse
from datetime import date, datetime, timedelta
from pathlib import Path, PurePath
import pandas as pd
from xlrd import XLRDError
import numpy as np
import locale
try:
	locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except locale.Error:
	# Readthedocs has a problem, but difficult to replicate
	locale.setlocale(locale.LC_ALL, "")

###################################################################################################
### Path management
###################################################################################################

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
	# whyqd/core/common ... .parent.parent -> whyqd/
	return Path(__file__).resolve().parent.parent

def check_uri(source):
	# https://stackoverflow.com/a/38020041
    try:
        result = urlparse(source)
        return all([result.scheme, result.netloc, result.path])
    except:
        return False

def rename_file(source, newname):
	p = Path(source)
	newname = "{}{}".format(newname, p.suffix)
	p.rename(Path(p.parent, newname))
	return newname

def delete_file(source):
	try:
		assert sys.version_info >= (3,8)
	except AssertionError:
		Path(source).unlink()
	else:
		Path(source).unlink(missing_ok=True)

###################################################################################################
### Parsers
###################################################################################################

def get_checksum(source, load_source=True):
	# https://stackoverflow.com/a/47800021
	#checksum = hashlib.blake2b()
	#with open(source, "rb") as f:
	#	for chunk in iter(lambda: f.read(4096), b""):
	#		checksum.update(chunk)
	#return checksum.hexdigest()
	if load_source:
		df = get_dataframe(source)
	else:
		df = source
	df_checksum = pd.util.hash_pandas_object(df, index=True).values
	checksum = hashlib.blake2b
	return checksum(df_checksum).hexdigest()

def chunks(l, n):
	"""Yield successive n-sized chunks from l."""
	# https://stackoverflow.com/a/976918/295606
	for i in range(0, len(l), n):
		yield l[i:i + n]

DATE_FORMATS = {
	"date": {
		"fmt": ["%Y-%m-%d"],
		"txt": ["YYYY-MM-DD"]
	},
	"datetime": {
		"fmt": ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S %Z%z"],
		"txt": ["YYYY-MM-DD hh:mm:ss","YYYY-MM-DD hh:mm:ss UTC+0000"]
	},
	"year": {
		"fmt": ["%Y"],
		"txt": ["YYYY"]
	}
}

def check_date_format(date_type, date_value):
	# https://stackoverflow.com/a/37045601
	# https://www.saltycrane.com/blog/2009/05/converting-time-zones-datetime-objects-python/
	for i, fmt in enumerate(DATE_FORMATS[date_type]["fmt"]):
		try:
			if date_value == datetime.strptime(date_value, fmt).strftime(fmt):
				return True
		except ValueError:
			continue
	txt = DATE_FORMATS[date_type]["txt"]
	e = "Incorrect date format, should be: `{}`".format(txt)
	raise ValueError(e)

def parse_dates(x):
	"""
	This is the hard-won 'trust nobody', certainly not Americans, date parser.
	"""
	if pd.isnull(x): return pd.NaT
	# Check if to_datetime can handle things
	if not pd.isnull(pd.to_datetime(x, errors="coerce", dayfirst=True)):
		return date.isoformat(pd.to_datetime(x, errors="coerce", dayfirst=True))
	# Manually see if coersion will work
	x = str(x).strip()[:10]
	x = re.sub(r"[\\/,\.]","-", x)
	try:
		y, m, d = x.split("-")
	except ValueError:
		return pd.NaT
	if len(y) < 4:
		# Swap the day and year positions
		# Ignore US dates
		d, m, y = x.split("-")
	# Fat finger on 1999 ... not going to check for other date errors as no way to figure out
	if y[0] == "9": y = "1" + y[1:]
	x = "{}-{}-{}".format(y, m, d)
	try:
		x = datetime.strptime(x,"%Y-%m-%d")
	except ValueError:
		return pd.NaT
	x = date.isoformat(x)
	try:
		pd.Timestamp(x)
		return x
	except pd.errors.OutOfBoundsDatetime:
		return pd.NaT

def parse_float(x):
	"""
	Regex to extract wrecked floats: https://stackoverflow.com/a/385597
	Checked against: https://regex101.com/
	"""
	try:
		return float(x)
	except ValueError:
		re_float = re.compile("""(?x)
		   ^
			  \D*     		# first, match an optional sign *and space*
			  (             # then match integers or f.p. mantissas:
				  \d+       # start out with a ...
				  (
					  \.\d* # mantissa of the form a.b or a.
				  )?        # ? takes care of integers of the form a
				 |\.\d+     # mantissa of the form .b
			  )
			  ([eE][+-]?\d+)?  # finally, optionally match an exponent
		   $""")
		try:
			x = re_float.match(x).group(1)
			x = re.sub(r"[^e0-9,-\.]","", str(x))
			return locale.atof(x)
		except (ValueError, AttributeError):
			return np.nan

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
		json.dump(data, f, indent=4, sort_keys=True, default=str)
	return True

JSON_SETTING_FILES = {
	"schema": "default_fields.json",
	"filter": "default_filters.json",
	"actions": "default_actions.json"
}

def get_settings(choice):
	"""
	Return the complete json settings for a json `filename` as a dict.
	"""
	filename = JSON_SETTING_FILES[choice]
	source = PurePath.joinpath(get_path(), "settings", filename)
	return load_json(source)

def get_field_settings(field_type, key="type", setting_file="schema"):
	fields = get_settings(setting_file)["fields"]
	for f in fields:
		if f[key] == field_type:
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
	filetype: (Optional) must be in ['csv', 'xls', 'xlsx']
	kwargs: additional keyword-arguments for Pandas;

	Returns
	-------
	Dataframe (if fails, returns empty dataframe)
	"""
	check_source(source)
	# If the dtypes have not been set, then ensure that any provided foreign_key remains untouched
	# i.e. no forcing of text to numbers
	# Pandas 1.0 says `dtype = "string"` is possible, but it isn't currently working
	# defaulting to `dtype = object` ...
	if foreign_key and "dtype" not in kwargs:
		kwargs["dtype"] = {
			foreign_key: object
		}
	# Get file delimiter
	if filetype and filetype.lower() in ["csv", "xls", "xlsx"]:
		filetype = filetype.lower()
	else:
		filetype = source.split(".")[-1].lower()
	if filetype not in ["csv"]:
		try:
			df = pd.read_excel(source, **kwargs)
			return df
		except XLRDError:
			pass
	elif filetype not in ["xlsx", "xls"]:
		kwargs["encoding"] = kwargs.get("encoding", "ISO-8859-1")
		kwargs["iterator"] = True
		kwargs["chunksize"] = kwargs.get("chunksize", 100000)
		df = pd.read_csv(source, **kwargs)
		df_chunks = []
		loop = True
		while loop:
			try:
				chunk = df.get_chunk(kwargs["chunksize"])
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
		import warnings
		filename = source.split("/")[-1] # Obfuscate the path
		e = "'{}' contains non-unique rows in column `{}`".format(filename, key)
		#raise ValueError(e)
		warnings.warn(e)
	return True