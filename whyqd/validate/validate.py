"""
.. module:: validate
   :synopsis: Validate an existing method and restructured output data.

.. moduleauthor:: Gavin Chait <github.com/turukawa>

Validate
========

When we talk about **data probity**, we're referring to the following criteria:

* Identifiable input source data,
* Transparent methods for restructuring of that source data into the data used to support research analysis,
* Accessible restructured data used to support research conclusions,
* A repeatable, auditable curation process which produces the same data.

Researchers may disagree on conclusions derived from analytical results. What they should not have cause for
disagreement on is the underlying data used to produce those analytical results.

That's where validation comes in.

Perform validation
------------------

In the :doc:`method` documentation, you saw how you can produce shareable output: your `method.json` file, your
`restructured_table.xlsx`, and the original input source data.

These are all that's required to validate your methods and output::

    >>> import whyqd
    >>> validate = whyqd.Validate(directory=DIRECTORY)
    >>> validate.set(source=METHOD_SOURCE)
    >>> validate.import_input_data(path=INPUT_DATA)
    >>> validate.import_restructured_data(path=RESTRUCTURED_DATA)
    >>> assert validate.validate()

Where:

 * `DIRECTORY` is your working directory to run the validation,
 * `METHOD_SOURCE` is the path to the `method.json` file,
 * `INPUT_DATA` is a list of paths to input source data,
 * `RESTRUCTURED_DATA` is the path to the restructured output data file.

What gets validated
-------------------

The method contains a `checksum` - a hash based on `BLAKE2b <https://en.wikipedia.org/wiki/BLAKE_(hash_function)>`_ - is
generated for each input file. These input data are never changed, and the hash is based on the entire file. If anyone
opens these files and resaves them - even if they make no further changes - metadata and file structure will change,
and a later hash generated on the changed file will be different from the original.

The check will fail.

`whyqd` rebuilds the restructured output table, following all the action scripts provided in the :doc:`method`.

This produces a new restructued data table. This table's content should be absolutely identical to that of the provided
restructured data. `whyqd` hashes the content of this table (*not* the file) and compares these hashes.

If the provided restructured data, and the newly-generated data based on the method actions, both have the same
checksum, then - whether you agree with the analysis, or methods, or not - we can state that these input data, with
these restructuring actions applied **does** produce these restructured data.
"""

from __future__ import annotations
from typing import Optional, Union, List, Dict
from uuid import UUID
import pandas as pd

from ..models import MethodModel, DataSourceModel
from ..parsers import CoreScript, WranglingScript
from ..schema import Schema
from ..method import Method


class Validate:
    """Validate an existing method.

    Parameters
    ----------
    directory: str
        Working path for validating methods, interim data files and final output.
    source: str, default None
        Path to a json file containing a saved method.
    method: MethodModel, default None
        A json file containing a saved method.
    """

    def __init__(
        self,
        directory: str,
        source: Optional[str] = None,
        method: Optional[MethodModel] = None,
    ) -> None:
        self._method = None
        self._schema = None
        self._validated_input_data = set()
        self._validate_restructured_data = False
        if source or method:
            self.set(source=source, method=method)
        # Initialise Parsers
        self.core = CoreScript()
        self.wrangle = WranglingScript()
        # Set working directory
        self.directory = self.core.check_path(directory)

    def __repr__(self) -> str:
        """Returns the string representation of the model."""
        if self._method:
            return f"Validate: `{self._method.name}`"
        return "Validate"

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

    def set(self, source: Optional[str] = None, method: Optional[MethodModel] = None) -> None:
        """Initialise an existing method for validation.

        Parameters
        ----------
        source: str, default None
            Path to a json file containing a saved method.
        method: MethodModel, default None
            A json file containing a saved method.
        """
        self._method = None
        if source:
            self._method = self.core.load_json(source)
        elif method:
            self._method = method
        if not self._method:
            raise ValueError(
                "Please provide at least one of either a path to a method file, or a `json` object, to initialise validation."
            )
        self._method = MethodModel.construct(**self._method)
        self._schema = Schema(schema={"name": f"schema_for_{self._method.name}", "fields": self._method.schema_fields})

    #########################################################################################
    # IMPORT SOURCE DATA
    #########################################################################################

    def import_input_data(self, path: Union[str, List[str]]) -> None:
        """Import a list of paths to input data to be used for build validation.

        Parameters
        ----------
        path: str or list of str
            Full path to associated source data.

        Raises
        ------
        ValueError if checksums fail to match.
        """
        self._has_method
        if isinstance(path, str):
            path = [path]
        for p in path:
            self.core.check_source(p)
            checksum = self.core.get_checksum(p)
            input_data = next((i for i in self._method.input_data if checksum == i["checksum"]), None)
            if not input_data:
                raise ValueError(
                    f"Imported source data fails checksum test and is not the same as the original source. (source: {p}, checksum: {checksum})"
                )
            if input_data.get("sheet_name"):
                for id_sheet in [i for i in self._method.input_data if checksum == i["checksum"]]:
                    id_sheet["path"] = p
            else:
                input_data["path"] = p
            self._validated_input_data.add(checksum)

    def import_restructured_data(self, path: str) -> None:
        """Import restructured data to be used for build validation.

        Parameters
        ----------
        path: str
            Full path to associated source data.
        """
        # Input data have whole-file checksums
        self._has_method
        self.core.check_source(path)
        restructured_data = self._method.restructured_data.copy()
        restructured_data["path"] = path
        df = self.wrangle.get_dataframe_from_datasource(DataSourceModel(**restructured_data))
        checksum = self.core.get_data_checksum(df)
        if checksum != self._method.restructured_data["checksum"]:
            # Try an alternative header in Schema order
            df_columns = [d["name"] for d in restructured_data["columns"]]
            header_order = [c.name for c in self._schema.get.fields if c.name in df_columns]
            checksum = self.core.get_data_checksum(df[header_order])
            if checksum != self._method.restructured_data["checksum"]:
                raise ValueError(
                    f"Imported source data fails checksum test and is not the same as the original source. (source: {self._method.restructured_data['checksum']}, import: {checksum})"
                )
        self._method.restructured_data["path"] = path
        self._validate_restructured_data = True

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
        if not (self._has_method and self._validate_input_data and self._validate_restructured_data):
            raise ValueError("Please ensure all requirements and source data are met before performing validation.")
        # The source dictionaries should all be validated now, so it should be possible to build the model.
        # Reset any working data
        merge_script = None
        if self._method.working_data:
            merge_script = self._method.working_data["actions"][0]["script"]
            working_scripts = []
            if len(self._method.working_data["actions"]) > 1:
                working_scripts = [s["script"] for s in self._method.working_data["actions"][1:]]
            self._method.working_data = None
        # Generate the Method
        method = Method(directory=self.directory, schema=self._schema, method=self._method.dict())
        if merge_script:
            method.merge(merge_script)
            working_data = method.get.working_data
            if working_scripts:
                method.add_actions(working_scripts, working_data.uuid.hex)
        # method.build()
        return method.validate()

    #########################################################################################
    # UTILITIES
    #########################################################################################

    def _get_input_data(self, uid: UUID, sheet_name: Optional[str] = None) -> dict:
        """Return original method source data model as a dict.

        Parameters
        ----------
        uid: UUID
            Unique uuid4 for an input data source. View all input data from method `input_data`.
        sheet_name: str, default None
            If the data source has multiple sheets, provide the specific sheet to update.

        Raises
        ------
        ValueError if a sheet_name exists without a sheet_name being provided.
        """
        if sheet_name:
            ds = next(
                (d for d in self._method.input_data if d["uuid"] == uid and d.get("sheet_name") == sheet_name),
                None,
            )
        else:
            ds = next((d for d in self._method.input_data if d["uuid"] == uid), None)
            if ds.get("sheet_name"):
                raise ValueError("Data source has multiple sheets. Specify which one to modify.")
        if not ds:
            raise ValueError(f"Data source cannot be found ({uid} {sheet_name}).")
        return ds

    # def _get_dataframe(self, data: dict) -> pd.DataFrame:
    #     """Return the dataframe for a data source.

    #     Parameters
    #     ----------
    #     data: dict

    #     Returns
    #     -------
    #     pd.DataFrame
    #     """
    #     df_columns = [d["name"] for d in data["columns"]]
    #     names = [d["name"] for d in data["names"]] if data.get("names") else None
    #     df = self.wrangle.get_dataframe(
    #         data["path"],
    #         filetype=data["mime"],
    #         names=names,
    #         preserve=[d["name"] for d in data.get("preserve", []) if d["name"] in df_columns],
    #     )
    #     if isinstance(df, dict):
    #         df = df[data["sheet_name"]]
    #     return df

    @property
    def _validate_input_data(self) -> bool:
        """Test if all input data has been imported for build validation."""
        all_inputs = set([ds["checksum"] for ds in self._method.input_data])
        if all_inputs.difference(self._validated_input_data):
            raise ValueError(
                f"There are still ({len(all_inputs.difference(self._validated_input_data))}) outstanding input data to import."
            )
        return True

    @property
    def _has_method(self) -> bool:
        """Check that a method has been imported."""
        if not self._method:
            raise ValueError("Please import a method before performing this task.")
        return True
