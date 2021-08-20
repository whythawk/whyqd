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

    print(method.print_input_data())

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

To view your existing `input_data` as a JSON output (or the `print_input_data` as above)::

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

Transform
---------

Transformation requires only the following::

    method.transform()
    method.save(DIRECTORY, filename=FILENAME, overwrite=True)

With one little permutation ... if you've ever created a transform before, you'll need to deliberately
tell the function to overwrite your original::

    method.transform(overwrite_output=True)

Citation
--------

**whyqd** is designed for sharing. Add information you wish to be cited to a `constructor` field in the `method`.

The `constructor` field is there to store any metadata you wish to add. Whether it be `Dublin Core <https://dublincore.org/>`_
or `SDMX <https://sdmx.org/>`_, add that metadata by creating a dictionary and placing it in the
`constructor`.

A citation is a special set of fields, with options for:

* **authors**: a list of author names in the format, and order, you wish to reference them
* **date**: publication date
* **title**: a text field for the full study title
* **repository**: the organisation, or distributor, responsible for hosting your data (and your method file)
* **doi**: the persistent `DOI <http://www.doi.org/>`_ for your repository

Those of you familiar with Dataverse's `universal numerical fingerprint <http://guides.dataverse.org/en/latest/developers/unf/index.html>`_
may be wondering where it is? **whyqd**, similarly, produces a unique hash for each datasource,
including inputs, working data, and outputs. Ours is based on `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_
and is sufficiently universally available as to ensure you can run this as required.

As an example::

    citation = {
        "authors": ["Gavin Chait"],
        "date": "2020-02-18",
        "title": "Portsmouth City Council normalised database of commercial ratepayers",
        "repository": "Github.com"
    }
    method.set_constructors({"citation": citation})
    method.save(DIRECTORY, filename=FILENAME, overwrite=True)

You can then get your citation report::

    method.citation

    Gavin Chait, 2020-02-18, Portsmouth City Council normalised database of commercial ratepayers,
    Github.com, 1367d4f02c99030f6645389141b85a93d54c226b435fb1b5a6cbccd7f703687e442a011f62c1381793a2d3fbf13cc52c176e0c5c573008991134658759eef948,
    [input sources:
    https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-properties-january-2020.xls,
    476089d8f37581613344873068d6e94f8cd63a1a64b421edf374a2b341bc7563aff03b86db4d3fec8ca90ce150ba1e531e3ff0d374f932d13fc103fd709e01bd;
    https://www.portsmouth.gov.uk/ext/documents-external/biz-ndr-reliefs-january-2020.xls,
    892ec5b6e9b1f68e0b371bbaed8d93095d57f2b656753af2b279aee17b5854c5e9d731b2795aac285d7f7d9f5991311bc8fae0cfe5446a47163f30f0314cac06;
    https://www.portsmouth.gov.uk/ext/documents-external/biz-empty-commercial-properties-january-2020.xls,
    a41b4eb629c249fd59e6816d10d113bf2b9594c7dd7f9a61a82333a8a41bf07e59f9104eb3c1dc4269607de5a4a12eaf3215d0afc7545fdb1dfe7fe1bf5e0d29]
"""
from __future__ import annotations
import uuid
from shutil import copyfile, SameFileError
import urllib.request
from copy import deepcopy
import pandas as pd
import numpy as np
import string
from tabulate import tabulate
from operator import itemgetter
from typing import Optional, Union, List, Dict
from enum import Enum

from whyqd.core import common as _c
from whyqd.core import dataframe as _d
from whyqd.models import SchemaModel, DataSourceModel, MethodModel
from whyqd.action import actions, default_actions
from whyqd.morph import morphs, default_morphs


class StatusType(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    READY_MERGE = "ready_merge"
    READY_STRUCTURE = "ready_structure"
    READY_CATEGORY = "ready_categorise"
    READY_FILTER = "ready_filter"
    READY_TRANSFORM = "ready_transform"
    CREATE_ERROR = "create_error"
    MERGE_ERROR = "merge_error"
    STRUCTURE_ERROR = "structure_error"
    CATEGORY_ERROR = "category_error"
    TRANSFORM_ERROR = "transform_error"
    PROCESS_COMPLETE = "process_complete"

    def describe(self):
        description = {
            "waiting": "Waiting ...",
            "processing": "Processing ...",
            "ready_merge": "Ready to Merge",
            "ready_structure": "Ready to Structure",
            "ready_categorise": "Ready to Categorise",
            "ready_filter": "Ready to Filter",
            "ready_transform": "Ready to Transform",
            "create_error": "Create Error",
            "merge_error": "Merge Error",
            "structure_error": "Structure Error",
            "category_error": "Categorisation Error",
            "transform_error": "Transform Error",
            "process_complete": "Process Complete",
        }
        return description[self.value]


class Method:
    """Create and manage a method to perform a wrangling process.

    Parameters
    ----------
        directory: str
                Working path for creating methods, interim data files and final output
    source: str
                Path to a json file containing a saved schema, default is None
    """

    def __init__(self, directory: str, schema: SchemaModel, method: Optional[MethodModel] = None):
        self._status = StatusType.WAITING
        # Default number of rows in a DataFrame to return from summaries
        self._nrows = 50
        # Clear kwargs of things we need to process prior to initialising
        self.directory = _c.check_path(directory)
        self._schema = SchemaModel(**schema)
        self._method = None
        if method:
            self._method = MethodModel(**method)
        # Initialise after Schema initialisation
        self.default_actions = actions
        self.default_morphs = morphs
        self.valid_filter_field_types = ["date", "year", "datetime"]

    def __repr__(self) -> str:
        """Returns the string representation of the model."""
        if self._schema:
            return f"Schema: `{self._schema.name}`"
        return "Schema"

    @property
    def describe(self) -> Union[Dict[str, None], None]:
        """Get the method name, title and description.

         - name: Term used for filename and referencing. Will be lower-cased and spaces replaced with `_`
         - title: Human-readable term used as name.
         - description: Detailed description for the method. Reference its objective and use-case.

        Returns
        -------
        dict or None
        """
        if self._method:
            response = {
                "name": self._method.name,
                "title": self._method.title,
                "description": self._method.description,
            }
            return response
        return None

    @property
    def get(self) -> Union[MethodModel, None]:
        """Get the method model.

        Returns
        -------
        MethodModel or None
        """
        return self._method

    def _method_exists(self, message: Optional[str] = None):
        """Check whether the method model has been defined. If not, raise a ValueError.

        Parameters
        ----------
        message: str
            Custom replacement for default error message.

        Raises
        ------
        ValueError if method model does not exist.
        """
        if not message:
            message = "Operation not permitted. Define your method model first."
        if not self._method:
            raise ValueError(message)

    def set(self, method: MethodModel):
        """Update or create the method.

        Parameters
        ----------
        method: MethodModel
            A dictionary conforming to the MethodModel.
        """
        # Create a temporary MethodModel
        updated_method = MethodModel(**method)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self._method:
            self._method = self._method.copy(update=updated_method.dict(exclude_unset=True))
        else:
            self._method = updated_method

    def add_data(self, source: Union[DataSourceModel, List[DataSourceModel]]):
        """Provide a dictionary conforming to the DataSourceModel data for wrangling.

        Each source dictionary requires the minimum of:

            {
                "path": "path/to/source/file"
            }

        An optional `citation` conforming to `CitationModel` can also be provided.

        Parameters
        ----------
        source: DataSourceModel or list of DataSourceModel
            A dictionary conforming to the DataSourceModel. Each path can be to a filename, or a url.
        """
        self._method_exists()
        if not isinstance(source, list):
            source = [source]
        for data in source:
            data = DataSourceModel(**data)
            # Check if the filename is remote
            file_root = "/".join(data.path.split("/")[:-1])
            valid_file_source = "".join(
                c for c in data.path.split("/")[-1] if c in f"-_. {string.ascii_letters}{string.digits}"
            )
            local_source = self.directory + valid_file_source
            if _c.check_uri(data.path):
                # File at remote URI
                urllib.request.urlretrieve(data.path, local_source)
            elif file_root:
                try:
                    # File in another directory
                    copyfile(data.path, local_source)
                except SameFileError:
                    pass
            _c.rename_file(local_source, data.source)
            df_sample = _d.get_dataframe(
                data.source, filetype=data.mime, names=data.names, preserve=data.preserve, nrows=self._nrows
            )

            if not isinstance(df_sample, dict):
                # There weren't multiple sheets in MimeType.XLS/X
                df_sample = {"key": df_sample}
            for k in df_sample.keys():
                summary_data = _c.get_dataframe_summary(df_sample[k])
                data_k = data.copy()
                if len(df_sample.keys()) > 1:
                    data_k = data.copy(deep=True, update={"sheet_name": k})
                data_k.summary = summary_data["df"]
                data_k.columns = summary_data["columns"]
                self._method.input_data.append(data_k)
        if len(self._method.input_data):
            self._status = "READY_MERGE"

    def remove_data(self, uid: str, sheet_name: Optional[str] = None):
        """Remove an input data source defined by its source uuid4.

        .. note:: You can remove references to individual sheets of a data source if you provide `sheet_name`. If not,
            the entire data source will be removed.

        Parameters
        ----------
        uid: str
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to remove, or - by default - the entire
            data source will be removed.
        """
        # self.reset_data_checksums(reset_status=reset_status)
        if self._method.input_data:
            if sheet_name:
                self._method.input_data = [
                    ds for ds in self._method.input_data if str(ds.uuid) != uid and ds.sheet_name != sheet_name
                ]
            else:
                self._method.input_data = [ds for ds in self._method.input_data if str(ds.uuid) != uid]
        if not self._method.input_data:
            self._status = "WAITING"

    def merge(self, order_and_key=None, overwrite_working=False):
        """Merge input data on a key column.

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
        if self._status in STATUS_CODES.keys() - [
            "READY_MERGE",
            "READY_STRUCTURE",
            "READY_CATEGORY",
            "READY_FILTER",
            "READY_TRANSFORM",
            "PROCESS_COMPLETE",
            "MERGE_ERROR",
        ]:
            e = "Current status: `{}` - performing `merge` is not permitted.".format(self.status)
            raise PermissionError(e)
        self.validate_merge_data
        if self.schema_settings.get("working_data", {}).get("checksum") and not overwrite_working:
            e = "Permission required to overwrite `working_data`. Set `overwrite_working` to `True`."
            raise PermissionError(e)
        # Perform merge
        df = self.perform_merge
        # Save the file to the working directory
        if "working_data" in self.schema_settings:
            del self.schema_settings["working_data"]
        self.schema_settings["working_data"] = self.save_data(df, prefix="working")

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
        if self._status in STATUS_CODES.keys() - [
            "READY_STRUCTURE",
            "READY_CATEGORY",
            "READY_FILTER",
            "READY_TRANSFORM",
            "PROCESS_COMPLETE",
            "STRUCTURE_ERROR",
        ]:
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
                if not schema_field.get("constraints", {}).get("category") and schema_field["type"] == "boolean":
                    if not schema_field.get("constraints"):
                        schema_field["constraints"] = {}
                    # Boolean fields have an implied constraint
                    schema_field["constraints"]["category"] = [{"name": True}, {"name": False}]
                if not schema_field.get("constraints", {}).get("category"):
                    e = "Field `{}` has no `category` constraints. Please `set_field_category`."
                    raise ValueError(e.format(field_name))
                schema_field["constraints"]["category_input"] = has_category
            # Validation would not add in the new values
            self.set_field(validate=False, **schema_field)
        self._status = "READY_CATEGORY"
        if not category_check:
            self._status = "READY_FILTER"

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
                    if marked["name"]:
                        u = "true"
                    else:
                        u = "false"
                else:
                    u = marked["name"]
                assigned[u] = self.build_category_markdown(marked["category_input"])
            unassigned = self.build_category_markdown(schema_field["category"].get("unassigned", []))
        if not schema_field.get("constraints", {}).get("category", []) or not schema_field.get("constraints", {}).get(
            "category_input"
        ):
            e = "Field `{}` has no available categorical data.".format(field_name)
            raise ValueError(e)
        if not schema_field.get("category"):
            unassigned = self.build_category_markdown(schema_field["constraints"]["category_input"])
        # Deals with boolean `True`/`False` case...
        if schema_field["type"] == "boolean":
            categories = ["true", "false"]
        else:
            categories = [c["name"] for c in schema_field["constraints"]["category"]]
        response = {"categories": categories, "assigned": assigned, "unassigned": unassigned}
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
        if self._status in STATUS_CODES.keys() - [
            "READY_CATEGORY",
            "READY_FILTER",
            "READY_TRANSFORM",
            "PROCESS_COMPLETE",
            "CATEGORY_ERROR",
        ]:
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
                category_term = {"name": c_name, "category_input": []}
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
                    category_term["category_input"].append({"column": column, "terms": input_terms[column]})
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
                        raise ValueError(e.format(field_name, set(assigned_input_terms) - set(all_terms)))
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
                unassigned.append({"column": terms["column"], "terms": unassigned_terms})
            # Set the category
            schema_field["category"] = {"assigned": assigned, "unassigned": unassigned}
            # Update the field
            self.set_field(validate=False, **schema_field)
        self.reset_data_checksums(reset_output_only=True)
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

        .. note:: filters can only be set on date-type fields. **whyqd** offers only rudimentary post-
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
        if self._status in STATUS_CODES.keys() - [
            "READY_FILTER",
            "READY_TRANSFORM",
            "PROCESS_COMPLETE",
            "FILTER_ERROR",
        ]:
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
                e = "Filter: `{}` requires a `{}` for filtering.".format(filter_name, schema_field["type"])
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
            "modifiers": {"name": filter_settings["name"], "date": filter_date},
        }
        # Update the field
        self.set_field(validate=False, **schema_field)
        self.reset_data_checksums(reset_output_only=True)
        self._status = "READY_TRANSFORM"

    def transform(self, overwrite_output=False, filetype="csv"):
        """
        Implement the method to transform input data into output data.

        Parameters
        ----------
        overwrite_output: bool
            Permission to overwrite existing output data
        filetype: str
            Must be in 'xlsx' or 'csv'. Default, 'csv'.
        """
        if filetype not in ["csv", "xlsx"]:
            filetype = "csv"
        if self._status in STATUS_CODES.keys() - ["READY_FILTER", "READY_TRANSFORM", "PROCESS_COMPLETE"]:
            e = "Current status: `{}` - performing `transform` is not permitted.".format(self.status)
            raise PermissionError(e)
        self.validates
        if self.schema_settings.get("output_data", {}).get("checksum") and not overwrite_output:
            e = "Permission required to overwrite `output_data`. Set `overwrite_output` to `True`."
            raise PermissionError(e)
        # Perform the transformation according to the method
        df = self.perform_transform
        self.schema_settings["process_date"] = _c.get_now()
        # Save the file to the working directory
        if "output_data" in self.schema_settings:
            del self.schema_settings["output_data"]
        self.schema_settings["output_data"] = self.save_data(df, filetype=filetype, prefix="output")
        self._status = "PROCESS_COMPLETE"

    #########################################################################################
    # CITATION
    #########################################################################################

    @property
    def citation(self):
        """
        Present a citation and validation report for this method. If citation data has been included
        in the `constructor` then that will be included.

        A citation is a special set of fields, with options for:

        * **authors**: a list of author names in the format, and order, you wish to reference them
        * **date**: publication date (uses transformation date, if not provided)
        * **title**: a text field for the full study title
        * **repository**: the organisation, or distributor, responsible for hosting your data (and your method file)
        * **doi**: the persistent `DOI <http://www.doi.org/>`_ for your repository

        Format for citation is:

            author/s, date, title, repository, doi, hash (for output data), [input sources: URI, hash]

        Returns
        -------
        str
            Text ready for citation.
        """
        # Validate the input and output
        self.validate_input_data
        self.validate_transform
        citation = []
        ctn = self.schema_settings.get("constructors", {}).get("citation", {})
        if ctn.get("authors"):
            if isinstance(ctn["authors"], list):
                citation.extend(ctn["authors"])
            else:
                citation.append(ctn["authors"])
        # Date
        citation.append(ctn.get("date", self.schema_settings["process_date"]))
        if ctn.get("title", self.details.get("title")):
            citation.append(ctn.get("title", self.details.get("title")))
        if ctn.get("repository"):
            citation.append(ctn["repository"])
        if ctn.get("doi"):
            citation.append(ctn["doi"])
        # Output hash
        citation.append(self.schema_settings["output_data"]["checksum"])
        # Input data
        input_reference = []
        for input_data in self.input_data:
            input_reference.append("{}, {}".format(input_data["original"], input_data["checksum"]))
        citation.append("[input sources: {}]".format("; ".join(input_reference)))
        return ", ".join(citation)

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

    def set_constructors(self, constructors, overwrite=False):
        """
        Define additional metadata to be included with the `method`.

        Citation data must be specifically included as:

            {
                "citation": {
                    "authors": ["Author Name 1", "Author Name 2"],
                    "title": "Citation Title",
                    "repository": "Data distributor",
                    "doi": "Persistent URI"
                }
            }

        Parameters
        ----------
        constructors: dict
            A set of key:value pairs. These will not be validated, or used during transformation.
        overwrite: boolean
            To overwrite any existing data in the constructor, set to True

        Raises
        ------
        TypeError if not a dict.
        """
        if not constructors or not isinstance(constructors, dict):
            e = "Method constructor is not a valid dict."
            raise TypeError(e)
        if self.schema_settings.get("constructors") and not overwrite:
            self.schema_settings["constructors"] = {**self.schema_settings["constructors"], **deepcopy(constructors)}
        else:
            self.schema_settings["constructors"] = deepcopy(constructors)

    def reset_data_checksums(self, reset_status=False, reset_output_only=False):
        """
        If input or working data are modified, then the checksums for working and output data
        must be deleted (i.e. they're no longer valid and everything else must be re-run).

        Parameters
        ----------
        reset_status: bool
            Requires a deliberate choice. Default False.
        reset_output_only: bool
            Requires a deliberate choice. Default False. Only resets output data.
        """
        if not (reset_status or reset_output_only) and (
            self.schema_settings.get("output_data", {}).get("checksum")
            or self.schema_settings.get("working_data", {}).get("checksum")
        ):
            e = "Permission required to reset data. Set `reset_status` or `reset_output_only` to `True`."
            raise PermissionError(e)
        if reset_status and self.schema_settings.get("working_data", {}).get("checksum"):
            del self.schema_settings["working_data"]["checksum"]
        if (reset_status or reset_output_only) and self.schema_settings.get("output_data", {}).get("checksum"):
            del self.schema_settings["output_data"]["checksum"]

    #########################################################################################
    # CREATE & MODIFY INPUT DATA
    #########################################################################################

    @property
    def input_data(self):
        return deepcopy(self.schema_settings.get("input_data", []))

    def input_dataframe(self, _id, do_morph=True):
        """
        Return dataframe of a specified `input_data` source. Perform the current morph method.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`
        do_morph: boolean, default True
            Perform the current morph method.

        Returns
        -------
        DataFrame
        """
        if "input_data" in self.schema_settings:
            input_dataframe = self._get_input_data_morph(_id)
            source = self.directory + input_dataframe["file"]
            df = _c.get_dataframe(source, dtype=object)
            if do_morph and input_dataframe.get("morph"):
                df = self.morph_transform(df, morph_methods=input_dataframe["morph"])
            return df
        e = f"No input data found for {_id}."
        raise ValueError(e)

    def print_input_data(self, format="rst"):
        # https://github.com/astanin/python-tabulate#table-format
        response = ""
        for data in self.input_data:
            _id = data["id"]
            _source = data["original"]
            _df = pd.DataFrame(data["dataframe"])
            _df = tabulate(_df, headers="keys", tablefmt=format)
            response += HELP_RESPONSE["data"].format(_id, _source, _df)
        return response

    def add_input_data(self, input_data, reset_status=False):
        """
        Provide a list of strings, each the filename of input data for wrangling.

        Parameters
        ----------
        input_data: str or list of str
            Each input data can be a filename, or a file_source (where filename is remote)
        reset_status: bool
            Requires a deliberate choice. Default False.

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
            e = "`{}` is not a valid list of input data.".format(input_data)
            raise TypeError(e)
        self.schema_settings["input_data"] = self.schema_settings.get("input_data", [])
        self.reset_data_checksums(reset_status=reset_status)
        for file_source in input_data:
            # Check if the filename is remote
            file_root = "/".join(file_source.split("/")[:-1])
            valid_file_source = "".join(
                c for c in file_source.split("/")[-1] if c in f"-_. {string.ascii_letters}{string.digits}"
            )
            source = self.directory + valid_file_source
            if _c.check_uri(file_source):
                # File at remote URI
                urllib.request.urlretrieve(file_source, source)
            elif file_root:
                try:
                    # File in another directory
                    copyfile(file_source, source)
                except SameFileError:
                    pass
            _id = str(uuid.uuid4())
            summary_data = _c.get_dataframe_summary(source)
            data = {
                "id": _id,
                "checksum": _c.get_checksum(source),
                "file": _c.rename_file(source, _id),
                "original": file_source,
                "dataframe": summary_data["df"],
                "columns": summary_data["columns"],
            }
            self.schema_settings["input_data"].append(data)
        if input_data and self.input_data:
            self._status = "READY_MERGE"

    def remove_input_data(self, _id, reset_status=False):
        """
        Remove an input data source defined by a source _id. If data have already been merged,
        reset data processing, or raise an error.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`
        reset_status: bool
            Requires a deliberate choice. Default False.

        Raises
        ------
        TypeError if not a list of str.
        """
        self.reset_data_checksums(reset_status=reset_status)
        if self.schema_settings.get("input_data", []):
            self.schema_settings["input_data"] = [
                data for data in self.schema_settings["input_data"] if data["id"] != _id
            ]
        if not self.input_data:
            self._status = "WAITING"

    def _get_input_data_morph(self, _id):
        """
        Returns the `input_data` source settings based on its `id`.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`.

        Raises
        ------
        ValueError if id does not exist.

        Returns
        -------
        Dict
            Settings for that `input_data` source.
        """
        input_source = next((item for item in self.schema_settings["input_data"] if item["id"] == _id), None)
        if input_source is None:
            e = f"Input data source {_id} does not exist."
            raise ValueError(e)
        return input_source

    def _set_input_data_morph(self, input_source):
        """
        Updates the morph methods of an `input_data` source.

        Parameters
        ----------
        input_source: dict
            Complete replacement of existing source, checked by id.
        """
        self.schema_settings["input_data"] = [
            data if data["id"] != input_source["id"] else input_source for data in self.schema_settings["input_data"]
        ]

    def reset_input_data_morph(self, _id, empty=False):
        """
        Wrapper around `reset_morph`. Reset list of morph methods to base. Automatically adds `DEBLANK` and `DEDUPE`
        unless `empty=True`.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`
        empty: boolean
            Start with an empty morph method. Default `False`.
        """
        input_source = self._get_input_data_morph(_id)
        input_source["morph"] = self.reset_morph(empty=empty)
        self._set_input_data_morph(input_source)

    def add_input_data_morph(self, _id, new_morph=None):
        """
        Wrapper around `add_morph`. Append a new morph method defined by `new_morph` to `morph_methods`,
        ensuring that the first term is a `morph`, and that the subsequent terms conform to that morph's
        validation requirements.

        The format for defining a `new_morph` is as follows::

            [morph, rows, columns, column_names]

        e.g.::

            ["REBASE", [2]]

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`
        new_morph: list
            Each parameter list must start with a `morph`, with subsequent terms conforming to the
            requirements for that morph.
        """
        input_source = self._get_input_data_morph(_id)
        if not input_source.get("morph"):
            input_source["morph"] = self.reset_morph()
            self._set_input_data_morph(input_source)
            input_source = self._get_input_data_morph(_id)
        df = self.input_dataframe(_id)
        input_source["morph"] = self.add_morph(df=df, new_morph=new_morph, morph_methods=input_source.get("morph"))
        self._set_input_data_morph(input_source)

    def delete_input_data_morph(self, _id, morph_id):
        """
        Wrapper around `delete_morph`. Delete morph method defined by `morph_id`.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`
        morph_id: str
            Unique id for morph method. View all morph methods from `input_data_morphs`.
        """
        input_source = self._get_input_data_morph(_id)
        input_source["morph"] = self.delete_morph_id(_id=morph_id, morph_methods=input_source.get("morph"))
        self._set_input_data_morph(input_source)

    def reorder_input_data_morph(self, _id, order):
        """
        Wrapper around `reorder_morph`. Reorder morph methods defined by `order`.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`
        order: list
            List of id strings.
        """
        input_source = self._get_input_data_morph(_id)
        input_source["morph"] = self.delete_morph_id(morph_methods=input_source.get("morph"), order=order)
        self._set_input_data_morph(input_source)

    def input_data_morphs(self, _id):
        """
        Wrapper around `get_morph_markup`. Return a markup version of a formal morph method.
        Useful for re-ordering methods.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`

        Returns
        -------
        list of dicts
        """
        input_source = self._get_input_data_morph(_id)
        return self.get_morph_markup(morph_methods=input_source.get("morph"))

    #########################################################################################
    # MORPH HELPERS
    #########################################################################################

    @property
    def default_morph_types(self):
        """
        Default list of morphs available to transform tabular data. Returns only a list
        of types. Details for individual default morphs can be returned with
        `default_morph_settings`.

        Returns
        -------
        list
        """
        return list(morphs.keys())

    def default_morph_settings(self, morph):
        """
        Get the default settings available for a specific morph type.

        Parameters
        ----------
        morph: string
            A specific term for an morph type (as listed in `default_morph_types`).

        Returns
        -------
        dict, or empty dict if no such `morph_type`
        """
        for field_morph in default_morphs["fields"]:
            if morph == field_morph["name"]:
                field_morph = deepcopy(field_morph)
                if "parameters" in field_morph:
                    del field_morph["parameters"]
                return field_morph
        return {}

    def add_morph(self, df=pd.DataFrame(), new_morph=None, morph_methods=None):
        """
        Append a new morph method defined by `new_morph` to `morph_methods`, ensuring that the first
        term is a `morph`, and that the subsequent terms conform to that morph's validation requirements.

        The format for defining a `new_morph` is as follows::

            [morph, rows, columns, column_names]

        e.g.::

            ["REBASE", [2]]

        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided.
        new_morph: list
            Each parameter list must start with a `morph`, with subsequent terms conforming to the
            requirements for that morph.
        morph_methods: list of morphs
            Existing morph methods. If `None` provided, creates a new list.
        """
        if morph_methods is None:
            morph_methods = self.reset_morph()
        if new_morph is None:
            # For the default reset case
            return morph_methods
        structure = []
        # Validate the morph of the structure_list first
        morph = self.default_morphs[new_morph[0]]()
        parameters = {}
        if len(new_morph) > 1:
            parameters = dict(zip(morph.structure, new_morph[1:]))
        if not morph.validates(df=df, **parameters):
            e = f"Task morph `{morph.name}` has invalid structure `{morph.structure}`."
            raise ValueError(e)
        morph_settings = morph.settings
        morph_settings["id"] = str(uuid.uuid4())
        morph_methods.append(morph_settings)
        return morph_methods

    def delete_morph_id(self, _id, morph_methods):
        """
        Delete morph method by id.

        Parameters
        ----------
        morph_methods: list of dicts of morphs
            Existing morph methods.
        _id: string
        """
        return [m for m in morph_methods if not (m["id"] == _id)]

    def reset_morph(self, empty=False):
        """
        Reset list of morph methods to base. Automatically adds `DEBLANK` and `DEDUPE` unless `empty=True`.

        Parameters
        ----------
        empty: boolean
            Start with an empty morph method. Default `False`.
        """
        morph_methods = []
        if not empty:
            morph_methods = self.add_morph(new_morph=["DEBLANK"], morph_methods=morph_methods)
            morph_methods = self.add_morph(new_morph=["DEDUPE"], morph_methods=morph_methods)
        return morph_methods

    def reorder_morph(self, morph_methods, order):
        """
        Reorder morph methods.

        Parameters
        ----------
        order: list
            List of id strings.

        Raises
        ------
        ValueError if not all ids in list, or duplicates in list.
        """
        if len(order) > len(morph_methods):
            e = f"List of ids is longer than list of methods."
            raise ValueError(e)
        if set([i["id"] for i in morph_methods]).difference(set(order)):
            e = f"List of ids must contain all method ids."
            raise ValueError(e)
        return sorted(morph_methods, key=lambda item: order.index(item["id"]))

    def get_morph_markup(self, morph_methods):
        """
        Return a markup version of a formal morph method. Useful for re-ordering methods.

        Returns
        -------
        list of dicts
        """
        markup = []
        if morph_methods is None:
            return markup
        for morph in morph_methods:
            mrph = [morph["name"]]
            for s in self.default_morphs[morph["name"]]().structure:
                if morph["parameters"].get(s):
                    mrph.append(morph["parameters"][s])
            markup.append({morph["id"]: mrph})
        return markup

    #########################################################################################
    # MERGE HELPERS
    #########################################################################################

    @property
    def perform_merge(self):
        """
        Helper function to perform the merge. Also used by merge_validation step.

        Returns
        -------
        DataFrame
            Merged dataframe derived from input_data
        """
        # Pandas 1.0 says `dtype = "string"` is possible, but it isn't currently working
        # defaulting to `dtype = object` ...
        # Note, this is done to avoid any random column processing
        df = _c.get_dataframe(self.directory + self.schema_settings["input_data"][0]["file"], dtype=object)
        # Perform morph
        if "morph" in self.schema_settings["input_data"][0]:
            df = self.morph_transform(df, morph_methods=self.schema_settings["input_data"][0]["morph"])
        if len(self.schema_settings["input_data"]) == 1:
            return df
        # Continue merge if > 1 `input_data` sources
        df_key = self.schema_settings["input_data"][0]["key"]
        missing_keys = []
        for data in self.schema_settings["input_data"][1:]:
            # defaulting to `dtype = object` ...
            dfm = _c.get_dataframe(self.directory + data["file"], dtype=object)
            # Perform morph
            if "morph" in data:
                dfm = self.morph_transform(df, morph_methods=data["morph"])
            dfm_key = data["key"]
            missing_keys.append(dfm_key)
            df = pd.merge(df, dfm, how="outer", left_on=df_key, right_on=dfm_key, indicator=False)
        # Where left key values null, copy any values in the right join-field (i.e. no key match)
        for key in missing_keys:
            df.loc[:, df_key] = np.where(pd.isnull(df[df_key]), df[key], df[df_key])
        # Deduplicate any columns after merge (and deduplicate the deduplicate in case of artifacts)
        df.columns = self.deduplicate_columns(self.deduplicate_columns(df.columns))
        return df

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
        fmt = "%s_%03d" if fmt is None else fmt
        for name in duplicates:
            dups = idx == name
            ret = [fmt % (name, i) if (i != 0 or not ignoreFirst) else name for i in range(dups.sum())]
            idx.loc[dups] = ret
        # Fix any fields with the same name as any of the target fields
        for name in self.all_field_names:
            dups = idx == name
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
            # if do_morph and input_dataframe.get("morph"):
            #    df = self.morph_transform(df, morph_methods=input_dataframe["morph"])
        e = "No working data found."
        raise ValueError(e)

    @property
    def working_data(self):
        return deepcopy(self.schema_settings.get("working_data", {}))

    def print_working_data(self, format="rst"):
        # https://github.com/astanin/python-tabulate#table-format
        _id = self.working_data["id"]
        _source = "working data"
        _df = pd.DataFrame(self.working_data["dataframe"])
        _df = tabulate(_df, headers="keys", tablefmt=format)
        return HELP_RESPONSE["data"].format(_id, _source, _df)

    def add_working_data_morph(self, new_morph=None):
        """
        Wrapper around `add_morph`. Append a new morph method defined by `new_morph` to `morph_methods`,
        ensuring that the first term is a `morph`, and that the subsequent terms conform to that morph's
        validation requirements.

        The format for defining a `new_morph` is as follows::

            [morph, rows, columns, column_names]

        e.g.::

            ["REBASE", [2]]

        Parameters
        ----------
        new_morph: list
            Each parameter list must start with a `morph`, with subsequent terms conforming to the
            requirements for that morph.
        """
        df = self.working_dataframe
        morph = self.add_morph(df=df, new_morph=new_morph, morph_methods=self.working_data.get(morph_methods))
        self.schema_settings["working_data"]["morph"] = morph

    def delete_working_data_morph(self, _id):
        """
        Wrapper around `delete_morph`. Delete morph method defined by `morph_id`.

        Parameters
        ----------
        _id: str
            Unique id for morph method. View all morph methods from `working_data_morphs`.
        """
        morph = self.delete_morph_id(morph_methods=self.working_data.get(morph_methods), _id=_id)
        self.schema_settings["working_data"]["morph"] = morph

    def reorder_working_data_morph(self, order):
        """
        Wrapper around `reorder_morph`. Reorder morph methods defined by `order`.

        Parameters
        ----------
        order: list
            List of id strings.
        """
        morph = self.delete_morph_id(morph_methods=self.working_data.get(morph_methods), order=order)
        self.schema_settings["working_data"]["morph"] = morph

    def working_data_morphs(self):
        """
        Wrapper around `get_morph_markup`. Return a markup version of a formal morph method.
        Useful for re-ordering methods.

        Parameters
        ----------
        _id: str
            Unique id for an input data source. View all input data from `input_data`

        Returns
        -------
        list of dicts
        """
        return self.get_morph_markup(morph_methods=self.working_data.get(morph_methods))

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
        structure_categories = {"terms": category_list, "column": column}
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
        # Validate the action of the structure_list first
        action = self.default_actions[structure_list[0]]()
        if not action.validates(structure_list[1:], self.working_column_list):
            e = "Task action `{}` has invalid structure `{}`.".format(action.name, structure_list)
            raise ValueError(e)
        structure.append(action.settings)
        term_set = len(action.structure)
        # Process the rest of the action structure
        for field in _c.chunks(structure_list[1:], term_set):
            for i, term in enumerate(action.structure):
                if isinstance(field[i], list):
                    # Deal with nested structures
                    structure.append(self.set_field_structure(field[i]))
                    continue
                if term == "value":
                    new_field = {"value": field[i], "type": _c.get_field_type(field[i])}
                    structure.append(new_field)
                if term == "modifier" and field[i] in action.modifier_names:
                    structure.append(action.get_modifier(field[i]))
                if term == "field" and field[i] in self.working_column_list:
                    structure.append(self.working_data_field(field[i]))
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
        return list(actions.keys())

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
        for field_action in default_actions:
            if action == field_action["name"]:
                return deepcopy(field_action)
        return {}

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
    # TRANSFORM HELPERS
    #########################################################################################

    def morph_transform(self, df, morph_methods=None):
        """
        Performs the morph transforms on a DataFrame. Assumes parameters have been validated.

        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided.
        morph_methods: list of morphs
            Existing morph methods.

        Returns
        -------
        Dataframe
            Containing the implementation of all morph transformations
        """
        if morph_methods is None:
            return df
        for mm in deepcopy(morph_methods):
            morph = self.default_morphs[mm["name"]]()
            df = morph.transform(df=df, **mm.get("parameters", {}))
        return df

    def action_transform(self, df, field_name, structure, **kwargs):
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
            List of fields with restructuring action defined by term 0 (i.e. `this` action)
        **kwargs:
            Other fields which may be required in custom transforms

        Returns
        -------
        Dataframe
            Containing the implementation of all nested transformations
        """
        action = self.default_actions[structure[0]["name"]]()
        if not action.validates(self.build_structure_markdown(deepcopy(structure[1:])), self.working_column_list):
            e = "Task action `{}` has invalid structure `{}`.".format(action.name, structure)
            raise ValueError(e)
        # Recursive check ...
        flattened_structure = []
        for i, field in enumerate(structure[1:]):
            if isinstance(field, list):
                # Need to create a temporary column ... the action will be performed here
                # then this nested structure will be replaced by the output of this new column
                temp_name = "nested_" + str(uuid.uuid4())
                df = self.action_transform(df, field_name, field, **kwargs)
                field = {"name": temp_name, "type": "nested"}
            flattened_structure.append(field)
        # Action transform
        return action.transform(df, field_name, flattened_structure, **kwargs)

    @property
    def perform_transform(self):
        """
        Helper function to perform the transformation. Also used by validate_transform step.

        Returns
        -------
        DataFrame
            Transformed dataframe derived from method
        """
        # Keep the original merge key field as a dtype=object to avoid messing with text formatting
        # e.g. leading 0s in a reference id
        set_dtypes = {}
        if self.schema_settings["input_data"][0].get("key"):
            set_dtypes[self.schema_settings["input_data"][0]["key"]] = object
        df = _c.get_dataframe(self.directory + self.schema_settings["working_data"]["file"], dtype=set_dtypes)
        # Begin transformations + keep track if any need filters
        filter_list = []
        for field_name in self.all_field_names:
            field = self.field(field_name)
            if field.get("filter"):
                filter_list.append(field_name)
            if not field.get("structure") and not field.get("constraints", {}).get("required"):
                # Isn't present and is not required
                continue
            kwargs = {"field_type": field["type"], "category": field.get("category", {}).get("assigned")}
            df = self.action_transform(df, field_name, field["structure"], **kwargs)
        # Identify required output fields not in df, and set blank fields for these
        blank_fields = list(set(self.all_field_names) - set(df.columns))
        for blank in blank_fields:
            df[blank] = ""
        # Conclude transformation
        df = df[self.all_field_names]
        df = df.loc[df.astype(str).drop_duplicates().index]
        # Perform filter requirements - note, the order may be important, but the user should be
        # careful with brute-force filters and should only set one. If they didn't ...
        for field_name in filter_list:
            field = self.field(field_name)
            filter = field["filter"]
            if filter["modifiers"]["name"] == "LATEST":
                # https://pandas.pydata.org/pandas-docs/stable/groupby.html#splitting-an-object-into-groups
                df = df.sort_values(by=field_name)
                df = df.groupby(filter["field"])
                # Select only the latest date
                df = df.last()
                # https://stackoverflow.com/a/20461206
                df.reset_index(level=df.index.names, inplace=True)
            if filter["modifiers"]["name"] == "AFTER" and filter["modifiers"].get("date"):
                df = df[df[field_name] > filter["modifiers"]["date"]]
            if filter["modifiers"]["name"] == "BEFORE" and filter["modifiers"].get("date"):
                df = df[df[field_name] < filter["modifiers"]["date"]]
            try:
                if filter["modifiers"]["name"] in ["LATEST", "AFTER"]:
                    field["filter"]["date"] = df[pd.notnull(df[field_name])][field_name].max()
                else:
                    field["filter"]["date"] = df[pd.notnull(df[field_name])][field_name].min()
                self.set_field(validate=False, **field)
            except TypeError:
                # They're not actually dates but are text for some reason
                pass
        return df

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
        are unique. Only required if there is more than one `input_data` source.

        Raises
        ------
        ValueError on uniqueness failure.
        """
        for data in (data for data in self.input_data if len(self.input_data) > 1):
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
        df = self.perform_merge
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
        if self.schema_settings["working_data"]["checksum"] != checksum:
            e = "Merge validation checksum failure {} != {}".format(
                self.schema_settings["working_data"]["checksum"], checksum
            )
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
        for field_name in self.all_field_names:
            # Test structure
            structure = self.field(field_name).get("structure")
            if not structure:
                if not self.field(field_name).get("constraints", {}).get("required"):
                    # Isn't present and is not required
                    continue
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
                if sorted(category, key=itemgetter("column")) != sorted(test_category, key=itemgetter("column")):
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
                    category_constraints = [c["name"] for c in schema_field["constraints"].get("category", {})]
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
                category_input_columns = [c["column"] for c in schema_field["constraints"].get("category_input", {})]
                diff = set(category_input.keys()) - set(category_input_columns)
                if diff:
                    e = "Category for Field `{}` has invalid data columns `{}`"
                    raise ValueError(e.format(field_name, diff))
                category_input_terms = [c["terms"] for c in schema_field["constraints"].get("category_input", {})]
                category_input_terms = [item for sublist in category_input_terms for item in sublist]
                category_terms = [item for sublist in category_input.values() for item in sublist]
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
                _c.check_date_format(schema_field["type"], schema_field["filter"]["modifiers"]["date"])
        return True

    @property
    def validate_transform(self):
        """
        Validate output data.

        Raises
        ------
        ValueError on checksum failure.

        Returns
        -------
        bool: True for validates
        """
        df = self.perform_transform
        # Save temporary file ... has to save & load for checksum validation
        _id = str(uuid.uuid4())
        filetype = self.schema_settings["output_data"]["file"].split(".")[-1]
        filename = "".join([_id, ".", filetype])
        source = self.directory + filename
        if filetype == "csv":
            df.to_csv(source, index=False)
        if filetype == "xlsx":
            df.to_excel(source, index=False)
        checksum = _c.get_checksum(source)
        _c.delete_file(source)
        if self.schema_settings["output_data"]["checksum"] != checksum:
            e = "Transformation validation checksum failure {} != {}".format(
                self.schema_settings["output_data"]["checksum"], checksum
            )
            raise ValueError(e)
        return True

    @property
    def validates(self):
        """
        Method validates all steps. Sets `READY_TRANSFORM` if all pass.

        Returns
        -------
        bool: True for validates
        """
        super().validates
        self.validate_input_data
        self.validate_merge_data
        self.validate_merge
        self.validate_structure
        self.validate_category
        self.validate_filter
        self._status = "READY_TRANSFORM"
        return True

    def build(self):
        """
        Build and validate the Method. Note, this replaces the Schema base-class.
        """
        self.schema_settings["fields"] = [
            self.build_field(validate=False, **field) for field in self.schema_settings.get("fields", [])
        ]
        if not self.directory:
            e = "Action is not a valid dictionary"
            raise ValueError(e)
        self._status = self.schema_settings.get("status", self._status)

    def save_data(self, df, filetype="xlsx", prefix=None):
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
        if prefix:
            _id = "_".join([prefix, _id])
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
            "columns": summary_data["columns"],
        }
        return data

    def save(self, directory=None, filename=None, overwrite=False, created_by=None):
        if not directory:
            directory = self.directory
        self.schema_settings["status"] = self._status
        super().save(directory=directory, filename=filename, overwrite=overwrite, created_by=created_by)

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
        if not option or option not in ["status", "merge", "structure", "category", "filter", "transform", "error"]:
            response = HELP_RESPONSE["default"].format(self.status)
        elif option != "status":
            response = HELP_RESPONSE[option]
            if option == "merge":
                for data in self.input_data:
                    _id = data["id"]
                    _source = data["original"]
                    _df = pd.DataFrame(data["dataframe"])
                    _df = tabulate(_df, headers="keys", tablefmt="rst")
                    response += HELP_RESPONSE["data"].format(_id, _source, _df)
            if option == "structure":
                response = response.format(self.all_field_names, self.default_action_types, self.working_column_list)
                if "working_data" in self.schema_settings:
                    _id = self.schema_settings["working_data"]["id"]
                    _source = "method.input_data"
                    _df = pd.DataFrame(self.schema_settings["working_data"]["dataframe"])
                    _df = tabulate(_df, headers="keys", tablefmt="rst")
                    response += HELP_RESPONSE["data"].format(_id, _source, _df)
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

    {{id: input_data id, key: column_name for merge}}

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
Original source: {}

{}
""",
    "status": """

Current method status: `{}`""",
}
