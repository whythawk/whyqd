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
from shutil import copyfile, SameFileError
import urllib.request
import string
from typing import Optional, Union, List, Dict, Tuple, Type
from pydantic import Json
from uuid import UUID
import pandas as pd
import numpy as np

from ..models import (
    DataSourceModel,
    ActionScriptModel,
    MethodModel,
    CategoryActionModel,
    VersionModel,
    MorphActionModel,
)
from ..parsers import CoreScript, WranglingScript, MethodScript, ParserScript
from ..schema import Schema


class Method:
    """Create and manage a method to perform a wrangling process.

    Parameters
    ----------
        directory: str
                Working path for creating methods, interim data files and final output
    source: str
                Path to a json file containing a saved schema, default is None
    """

    def __init__(self, directory: str, schema: Type[Schema], method: Optional[MethodModel] = None) -> None:
        # Default number of rows in a DataFrame to return from summaries
        self._nrows = 50
        if not isinstance(schema, Schema):
            raise AssertionError("Schema must be a valid Schema type.")
        self._schema = schema
        if not self._schema.get.fields:
            raise ValueError(f"Schema ({self._schema}) has no defined fields.")
        self._method = None
        if method:
            self._method = MethodModel(**method)
            self._method.schema_fields = self._schema.get.fields.copy()
        # Initialise Parsers
        self.core = CoreScript()
        self.mthdprsr = MethodScript(self._schema)
        self.wrangle = WranglingScript()
        self.parser = ParserScript()
        # Set working directory
        self.directory = self.core.check_path(directory)

    def __repr__(self) -> str:
        """Returns the string representation of the model."""
        if self._method:
            return f"Method: `{self._method.name}`"
        return "Method"

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

    def set(self, method: MethodModel) -> None:
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
        self._method.schema_fields = self._schema.get.fields.copy()

    #########################################################################################
    # MANAGE INPUT DATA
    #########################################################################################

    def add_data(self, source: Union[DataSourceModel, List[DataSourceModel]]) -> None:
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
        if not isinstance(source, list):
            source = [source]
        for data in source:
            data = DataSourceModel(**data)
            # Check if the filename is remote
            file_root = "/".join(data.path.split("/")[:-1])
            valid_file_source = "".join(
                c for c in data.path.split("/")[-1] if c in f"-_. {string.ascii_letters}{string.digits}"
            )
            local_source = self.directory / valid_file_source
            if self.core.check_uri(data.path):
                # File at remote URI
                urllib.request.urlretrieve(data.path, local_source)
            elif file_root:
                try:
                    # File in another directory
                    copyfile(data.path, local_source)
                except SameFileError:
                    pass
            self.core.rename_file(local_source, data.source)
            df_sample = self.wrangle.get_dataframe(
                self.directory / data.source,
                filetype=data.mime,
                names=data.names,
                preserve=data.preserve,
                nrows=self._nrows,
            )
            if not isinstance(df_sample, dict):
                # There weren't multiple sheets in MimeType.XLS/X
                df_sample = {"key": df_sample}
            for k in df_sample.keys():
                df_columns = self.wrangle.get_dataframe_columns(df_sample[k])
                data_k = data.copy()
                if len(df_sample.keys()) > 1:
                    data_k = data.copy(deep=True, update={"sheet_name": k})
                data_k.columns = df_columns
                self._method.input_data.append(data_k)

    def remove_data(self, uid: UUID, sheet_name: Optional[str] = None) -> None:
        """Remove an input data source defined by its source uuid4.

        .. note:: You can remove references to individual sheets of a data source if you provide `sheet_name`. If not,
            the entire data source will be removed.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to remove, or - by default - the entire
            data source will be removed.
        """
        if self._method.input_data:
            if sheet_name:
                self._method.input_data = [
                    ds for ds in self._method.input_data if ds.uuid != UUID(uid) and ds.sheet_name != sheet_name
                ]
            else:
                self._method.input_data = [ds for ds in self._method.input_data if ds.uuid != UUID(uid)]

    def update_data(self, uid: UUID, source: DataSourceModel, sheet_name: Optional[str] = None) -> None:
        """Update an existing data source.

        Can be used to modify which columns are to be preserved, or other specific changes.

        .. warning:: You can only modify the following definitions: `names`, `preserve`, `citation`. Attempting to
            change any other definitions will raise an exception. Remove the source data instead.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.
        source: DataSourceModel
            A dictionary conforming to the DataSourceModel. Each path can be to a filename, or a url.

        Raises
        ------
        ValueError if a sheet_name exists without a sheet_name being provided.
        """
        # Create a temporary DataSourceModel to ensure validation
        updated_source = DataSourceModel(**source)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self._method.input_data:
            ds = self.mthdprsr.get_input_data(self._method.input_data, uid, sheet_name)
            # And update the modified definitions ... exclude unset to ensure only updates included
            keys = list(updated_source.dict(exclude_unset=True).keys())
            if "names" in keys:
                ds.names = updated_source.names
            if "preserve" in keys:
                ds.preserve = updated_source.preserve
            if "citation" in keys and ds.citation:
                ds.citation = ds.citation.copy(update=updated_source.citation.dict(exclude_unset=True))
            elif "citation" in keys and not ds.citation:
                ds.citation = updated_source.citation

    def reorder_data(self, order: List[Union[UUID, Tuple[UUID, str]]]) -> None:
        """Reorder a list of source data prior to merging them.

        Parameters
        ----------
        order: list of UUID or tuples of UUID, str

        Raises
        ------
        ValueError if the list of uuid4s doesn't conform to that in the list of source data.
        """
        if self._method.input_data:
            self._method.input_data = self.mthdprsr.reorder_models(self._method.input_data, order)

    #########################################################################################
    # APPLY ACTIONS TO INPUT AND INTERIM SOURCE DATA
    #########################################################################################

    def add_actions(self, actions: Union[str, List[str]], uid: UUID, sheet_name: Optional[str] = None) -> None:
        """Add an action script to a data source specified by its uid and optional sheet name.

        .. warning:: Morph-type ACTIONS (such as 'REBASE', 'PIVOT_LONG', and 'PIVOT_WIDE') change the header-row
            column names, and - with that - any of your subsequent referencing that relies on these names. It is
            best to run your morphs first, then your schema ACTIONS, that way you won't get any weird referencing
            errors. If column errors do arise, check your ACTION ordering.

        Parameters
        ----------
        actions: str or list of str
            An action script.
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.
        """
        if not isinstance(actions, list):
            actions = [actions]
        pre_df = pd.DataFrame()
        for a in actions:
            a = ActionScriptModel(**{"script": a})
            source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
            params = self.mthdprsr.parse_action_script(source_data, a)
            source_data.actions.append(a)
            if isinstance(params["action"], MorphActionModel):
                if pre_df.empty:
                    pre_df = self.wrangle.get_dataframe(
                        self.directory / source_data.source,
                        filetype=source_data.mime,
                        names=source_data.names,
                        preserve=source_data.preserve,
                    )
                    if isinstance(pre_df, dict):
                        pre_df = pre_df[source_data.sheet_name]
                    source_data.columns = self.wrangle.get_dataframe_columns(pre_df)
                pre_df = self.mthdprsr.transform_df_from_source(pre_df, source_data, **params)
                # And update the columns
                source_data.columns = self.wrangle.get_dataframe_columns(pre_df)

    def remove_action(self, uid: UUID, action_uid: UUID, sheet_name: Optional[str] = None) -> None:
        """Remove an action from a data source defined by its source uuid4. Raises an exception of sheet_name
        applies to that data source.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        action_uid: UUID
            Unique uuid4 for an action.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.

        Raises
        ------
        ValueError if a sheet_name exists without a sheet_name being provided.
        """
        source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
        source_data = self.mthdprsr.remove_action(source_data.actions, action_uid)
        self._rebuild_actions(source_data)

    def update_action(self, uid: UUID, action_uid: UUID, action: str, sheet_name: Optional[str] = None) -> None:
        """Update an action from a list of actions.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        action_uid: UUID
            Unique uuid4 for an action.
        action: str
            An updated action script.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.
        """
        new_action = ActionScriptModel(**{"script": action})
        source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
        # Check that it parses
        self.mthdprsr.parse_action_script(source_data, new_action)
        source_data = self.mthdprsr.update_actions(source_data.actions, action_uid, new_action)
        self._rebuild_actions(source_data)

    def reorder_actions(self, uid: UUID, order: List[UUID], sheet_name: Optional[str] = None) -> None:
        """Reorder a list of actions.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for a either an input or interim data source.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.
        order: list of UUID
            List of uuid4 action strings.

        Raises
        ------
        ValueError if the list of uuid4s doesn't conform to that in the list of actions.
        """
        source_data = self.mthdprsr.get_source_data(self._method, uid=uid, sheet_name=sheet_name)
        source_data = self.mthdprsr.reorder_models(source_data.actions, order)
        self._rebuild_actions(source_data)

    #########################################################################################
    # MERGE INPUT AND GENERATE INTERIM DATA
    #########################################################################################

    def merge(self, script: str) -> None:
        """Merge input data to generate any required interim data. Will perform all actions on each interim data source.

        .. note:: Merging, or an interim data source, are not required to produce a schema-defined destination data
            output.

        .. warning:: There is only so much hand-holding possible:
            * If an interim data source already exists, and has existing actions, this function will reset the
            action list, placing this `script` first.
            * If further actions are added to input data, this function must be run again.
            * The first two points are, obviously, detrimental to each other.
            * And then there are 'filters' which are intrinsically destructive.

        Merge script is of the form::

            "MERGE < ['key_column'::'source_hex'::'sheet_name', ...]"

        Where the source terms are in order for merging.

        Parameters
        ----------
        script: str
            Merge script, as defined.
        """
        # Get or create the working_file path
        if self._method.working_data:
            working_path = self._method.working_data.path
        else:
            working_file = (
                f"working_{'_'.join([m.lower() for m in self._method.name.split()])}_{self._method.uuid.hex}.xlsx"
            )
            working_path = self.directory / working_file
        merge_list = self.mthdprsr.parse_merge(script, self._method.input_data)
        # Perform the merge
        df = self._merge_dataframes(merge_list)
        # Establish the WORKING DATA term in method
        df.to_excel(working_path, index=False)
        working_data = DataSourceModel(**{"path": working_path})
        working_data.columns = self.wrangle.get_dataframe_columns(df)
        working_data.preserve = [c for c in working_data.columns if c.type_field == "string"]
        working_data.actions = [ActionScriptModel(**{"script": script})]
        working_data.checksum = self.core.get_data_checksum(df)
        self._method.working_data = working_data
        # Update the method with this change-event
        update = VersionModel(**{"description": "Build merged data."})
        self._method.version.append(update)

    #########################################################################################
    # IMPLEMENT TRANSFORMATIONS
    #########################################################################################

    def transform(self, data: DataSourceModel) -> pd.DataFrame:
        """Returns a transformed DataFrame after performing assigned action scripts, in order, to transform
        a data source.

        Parameters
        ----------
        data: DataSourceModel

        Returns
        -------
        Pandas DataFrame
        """
        # 1. Check that there are transformations to perform
        if not data.actions:
            raise ValueError("There are no transformation actions to perform.")
        data_actions = data.actions.copy()
        # Check if the first action is a MERGE
        if self.parser.get_anchor_action(data_actions[0].script).name == "MERGE":
            if not len(data.actions) > 1:
                raise ValueError("Merge is complete, but there are no further transformation actions to perform.")
            data_actions = data.actions[1:].copy()
        # 2. Morph ACTIONS change reference columns ... this causes the chaos you would expect ...
        # Reset column references BEFORE starting transform so that scripts run properly
        df = self.wrangle.get_dataframe(
            self.directory / data.source,
            filetype=data.mime,
            names=data.names,
            preserve=data.preserve,
        )
        if isinstance(df, dict):
            df = df[data.sheet_name]
        data.columns = self.wrangle.get_dataframe_columns(df)
        # 1. Parse all category assignment scripts
        category_assignments = []
        for script in data.actions:
            first_action = self.parser.get_anchor_action(script.script)
            if isinstance(first_action, CategoryActionModel) and first_action.name in [
                "ASSIGN_CATEGORY_UNIQUES",
                "ASSIGN_CATEGORY_BOOLEANS",
            ]:
                category_assignments.append(self.mthdprsr.parse_action_script(data, script))
        parsed = []
        # 3. Associate category ASSIGNMENTS to CATEGORISE & process MORPHS without trashing things
        for script in data_actions:
            first_action = self.parser.get_anchor_action(script.script)
            if isinstance(first_action, CategoryActionModel):
                continue
            p = self.mthdprsr.parse_action_script(data, script)
            if isinstance(p["action"], MorphActionModel):
                # Do a pre-transform up to this point to get the current column state ... only way without
                # massive refactoring ... will try come up with a more efficient way...
                # Currently, this is an abomination unto ... everything.
                pre_df = df.copy()
                pre_parsed = parsed.copy()
                pre_parsed.append(p)
                data.columns = self.wrangle.get_dataframe_columns(pre_df)
                for params in pre_parsed:
                    pre_df = self.mthdprsr.transform_df_from_source(pre_df, data, **params)
                    data.columns = self.wrangle.get_dataframe_columns(pre_df)
            elif p["action"].name == "CATEGORISE":
                p["assigned"] = []
                for a in category_assignments:
                    if a["destination"].name == p["destination"].name:
                        p["assigned"].append(a)
            parsed.append(p)
        # 4. Perform the transformations on the DataFrame
        #    These can be a mix of Schema and Morph Actions
        data.columns = self.wrangle.get_dataframe_columns(df)
        for params in parsed:
            df = self.mthdprsr.transform_df_from_source(df, data, **params)
            # And update the columns
            data.columns = self.wrangle.get_dataframe_columns(df)
        return df

    #########################################################################################
    # BUILD THE OUTPUT DATA ACCORDING TO THE SCHEMA
    #########################################################################################

    def build(self) -> None:
        """Merge input data to generate any required interim data. Will perform all actions on each interim data source.

        .. note:: Merging, or an interim data source, are not required to produce a schema-defined destination data
            output.

        .. warning:: There is only so much hand-holding possible:
            * If an interim data source already exists, and has existing actions, this function will reset the
            action list, placing this `script` first.
            * If further actions are added to input data, this function must be run again.
            * The first two points are, obviously, detrimental to each other.
            * And then there are 'filters' which are intrinsically destructive.
        """
        # Validate and restructure source data
        df_restructured = self._restructure_dataframes()
        # Establish the RESTRUCTURED DATA term in method
        # Get or create the restructured_file path
        if self._method.restructured_data:
            restructured_path = self._method.restructured_data.path
        else:
            restructured_file = (
                f"restructured_{'_'.join([m.lower() for m in self._method.name.split()])}_{self._method.uuid.hex}.xlsx"
            )
            restructured_path = self.directory / restructured_file
        df_restructured.to_excel(restructured_path, index=False)
        restructured_data = DataSourceModel(**{"path": restructured_path})
        restructured_data.columns = self.wrangle.get_dataframe_columns(df_restructured)
        restructured_data.preserve = [c for c in restructured_data.columns if c.type_field == "string"]
        restructured_data.checksum = self.core.get_data_checksum(df_restructured)
        self._method.restructured_data = restructured_data
        # Update the method with this change-event
        update = VersionModel(**{"description": "Build restructured data."})
        self._method.version.append(update)

    #########################################################################################
    # VALIDATE BUILD
    #########################################################################################

    def validate(self) -> bool:
        """Validate the build process and all data checksums. Will perform all actions on each interim data source.

        Raises
        ------
        ValueError if any steps fail to validate.

        Returns
        -------
        bool
        """
        if not isinstance(self._method.restructured_data, DataSourceModel):
            raise ValueError("Method build restructuring is not complete.")
        # Validate and restructure source data
        df_restructured = self._restructure_dataframes()
        # Validate RESTRUCTURED DATA checksums
        df_checksum = self.core.get_data_checksum(df_restructured)
        if self._method.restructured_data.checksum != df_checksum:
            raise ValueError("Method build of restructured source data does not validate.")
        return True

    #########################################################################################
    # SAVE UTILITIES
    #########################################################################################

    def get_json(self, hide_uuid: Optional[bool] = False) -> Union[Json, None]:
        """Get the json method model.

        Parameters
        ----------
        hide_uuid: str, default False
            Hide all UUIDs in the nested JSON output.

        Returns
        -------
        Json or None
        """
        if self._method and not hide_uuid:
            return self._method.json(by_alias=True, exclude_defaults=True, exclude_none=True)
        elif self._method and hide_uuid:
            exclude_schema_fields, exclude_input_data, exclude_working_data, exclude_restructured_data = (
                None,
                None,
                None,
                None,
            )
            if self._method.schema_fields:
                exclude_schema_fields = {
                    f_idx: (
                        {
                            "uuid": ...,
                            "constraints": {
                                "category": {c_idx: {"uuid"} for c_idx in range(len(f.constraints.category))}
                            },
                        }
                        if f.constraints
                        else {"uuid"}
                    )
                    for f_idx, f in enumerate(self._method.schema_fields)
                }
            # DataSourceModel: columns, preserve, key, actions all have UUID
            if self._method.input_data:
                exclude_input_data = {
                    i_idx: (
                        {
                            "uuid": ...,
                            "columns": ({c_idx: {"uuid"} for c_idx in range(len(i.columns))} if i.columns else None),
                            "preserve": (
                                {c_idx: {"uuid"} for c_idx in range(len(i.preserve))} if i.preserve else None
                            ),
                            "key": ({"uuid"} if i.key else None),
                            "actions": ({c_idx: {"uuid"} for c_idx in range(len(i.actions))} if i.actions else None),
                        }
                    )
                    for i_idx, i in enumerate(self._method.input_data)
                }
            if self._method.working_data:
                exclude_working_data = {
                    "uuid": ...,
                    "columns": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.working_data.columns))}
                        if self._method.working_data.columns
                        else None
                    ),
                    "preserve": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.working_data.preserve))}
                        if self._method.working_data.preserve
                        else None
                    ),
                    "key": ({"uuid"} if self._method.working_data.key else None),
                    "actions": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.working_data.actions))}
                        if self._method.working_data.actions
                        else None
                    ),
                }
            if self._method.restructured_data:
                exclude_restructured_data = {
                    "uuid": ...,
                    "columns": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.restructured_data.columns))}
                        if self._method.restructured_data.columns
                        else None
                    ),
                    "preserve": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.restructured_data.preserve))}
                        if self._method.restructured_data.preserve
                        else None
                    ),
                    "key": ({"uuid"} if self._method.restructured_data.key else None),
                    "actions": (
                        {c_idx: {"uuid"} for c_idx in range(len(self._method.restructured_data.actions))}
                        if self._method.restructured_data.actions
                        else None
                    ),
                }
            exclude = {
                "uuid": ...,
                "schema_fields": exclude_schema_fields,
                "input_data": exclude_input_data,
                "working_data": exclude_working_data,
                "restructured_data": exclude_restructured_data,
            }
            return self._method.json(by_alias=True, exclude_defaults=True, exclude_none=True, exclude=exclude)
        return None

    def save(
        self,
        directory: Optional[str] = None,
        filename: Optional[str] = None,
        created_by: Optional[str] = None,
        hide_uuid: Optional[bool] = False,
    ) -> bool:
        """Save schema as a json file.

        Parameters
        ----------
        directory: str
            Defaults to working directory
        filename: str
            Defaults to schema name
        created_by: string, default is None
            Declare the schema creator/updater
        hide_uuid: str, default False
            Hide all UUIDs in the nested JSON output.

        Returns
        -------
        bool True if saved
        """
        if not self._method:
            raise ValueError("Method does not exist.")
        if not directory:
            directory = self.directory
        else:
            directory = self.core.check_path(directory)
        if not filename:
            filename = self._method.name
        if filename.split(".")[-1] != "json":
            filename += ".json"
        path = directory / filename
        update = VersionModel(**{"description": "Save method."})
        if created_by:
            update.name = created_by
        self._method.version.append(update)
        return self.core.save_file(self.get_json(hide_uuid=hide_uuid), path)

    #########################################################################################
    # OTHER UTILITIES
    #########################################################################################

    def _rebuild_actions(self, data: DataSourceModel) -> None:
        """Rebuild all actions for any changes to the list of actions since they can have unexpected interactions."""
        actions = [d.script for d in data.actions]
        df = self.wrangle.get_dataframe(
            self.directory / data.source,
            filetype=data.mime,
            names=data.names,
            preserve=data.preserve,
        )
        if isinstance(df, dict):
            df = df[data.sheet_name]
        data.columns = self.wrangle.get_dataframe_columns(df)
        data.actions = []
        data.actions = self.add_actions(actions, data.uuid.hex, data.sheet_name)

    def _merge_dataframes(self, merge_list: List[DataSourceModel]) -> pd.DataFrame:
        """Return a merged dataframe by transforming and merging a list of source data.

        Parameters
        ----------
        merge_list: list of DataSourceModel

        Returns
        -------
        pd.DataFrame
        """
        df_base = pd.DataFrame()
        missing_keys = []
        for input_data in merge_list:
            # Perform all input data transforms and return the dataframe
            df = self.transform(input_data)
            if df_base.empty:
                df_base = df.copy()
                data_base = input_data.copy()
            else:
                df_base = pd.merge(
                    df_base, df, how="outer", left_on=data_base.key, right_on=input_data.key, indicator=False
                )
                missing_keys.append(input_data.key)
        # Deal with missing key values, and with duplicated columns ...
        # Where left key values null, copy any values in the right join-field (i.e. no key match)
        for key in missing_keys:
            df_base.loc[:, data_base.key] = np.where(
                df_base[data_base.key].isnull(), df_base[key], df_base[data_base.key]
            )
        # Deduplicate any columns after merge (and deduplicate the deduplicate in case of artifacts)
        df_base.columns = self.wrangle.deduplicate_columns(self.wrangle.deduplicate_columns(df_base.columns))
        return df_base

    def _restructure_dataframes(self) -> pd.DataFrame:
        """Return a restructured dataframe by transforming source data.

        Raises
        ------
        ValueError if any steps fail to validate.

        Returns
        -------
        pd.DataFrame
        """
        # Check this is a valid build ...
        if not self._method.input_data:
            raise ValueError("Method build error. No input data available in this method.")
        if len(self._method.input_data) > 1 and not isinstance(self._method.working_data, DataSourceModel):
            raise ValueError(
                f"Method build is unclear where there are multiple input source data ({len(self._method.input_data)}) but they have not been merged."
            )
        if len(self._method.input_data) == 1 and not isinstance(self._method.working_data, DataSourceModel):
            df_restructured = self.transform(self._method.input_data[0])
        else:
            # Recreate the merge from the input data ...
            merge_script = self._method.working_data.actions[0]
            merge_list = self.mthdprsr.parse_merge(merge_script, self._method.input_data)
            # Perform the merge and validate the merged DataFrame's checksum
            df_working = self._merge_dataframes(merge_list)
            df_checksum = self.core.get_data_checksum(df_working)
            if self._method.working_data.checksum != df_checksum:
                raise ValueError(
                    "Method build of merged source data does not validate. Check whether you added additional source data action scripts after your last merge."
                )
            # Create the restructured dataframe.
            df_restructured = self.transform(self._method.working_data)
        # Validate against the SCHEMA
        restructured_columns = set(df_restructured.columns)
        schema_required = set([f.name for f in self._schema.get.fields if f.constraints and f.constraints.required])
        if schema_required.difference(restructured_columns):
            raise ValueError(
                f"Method build restructured table is missing required schema fields ({schema_required.difference(restructured_columns)})"
            )
        # Keep only the columns from the schema, in that order
        restructured_keep_columns = set([f.name for f in self._schema.get.fields if f.name in restructured_columns])
        return df_restructured[restructured_keep_columns]
