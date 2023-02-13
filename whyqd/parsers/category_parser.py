from __future__ import annotations
from typing import Dict, List, Union, TYPE_CHECKING

# import pandas as pd
import modin.pandas as pd
import numpy as np

from . import CoreScript, ParserScript, WranglingScript
from ..models import CategoryModel

if TYPE_CHECKING:
    from ..models import ColumnModel, FieldModel, CategoryActionModel, DataSourceModel
    from ..schema import Schema


class CategoryScript:
    """Parsing functions for category implementations of action scripts. These are support actions which must be run
    before `CATEGORISE`.

    This is a hybrid function:

    * *Get* a list of unique values from a source column, if categorising by unique. This step isn't necessary for
      boolean assignment,
    * `ASSIGN` subset of unique values (or all booleans) to a specified `CategoryModel` in a destination `ColumnModel`.

    Scripts must be 'flat' and are of the form::

        "ASSIGN_CATEGORY_UNIQUES > FieldModel::CategoryModel < ColumnModel::[CategoryModel.etc.]"

    Or::

        "ASSIGN_CATEGORY_BOOLEANS > FieldModel::bool < ColumnModel"

    Where:

    * `FieldModel` is the destination column and the `::` linked `CategoryModel` defines what term the source values
      are to be assigned. This is defined in the `Schema`.
    * For `ASSIGN_CATEGORY_UNIQUES` the `list` of `CategoryModel` - unique values from `ColumnModel` - will be assigned
      `::CategoryModel`.
    * For `ASSIGN_CATEGORY_BOOLEANS` values from the ColumnModel are treated as boolean `True` or `False`, defined by `::bool`.

    Parameters
    ----------
    column: Numpy Array
        Values from the source column as an array.
    source_columns: list of ColumnModel
        Source columns upon which the script will be applied.
    schema: Schema
        Destination Schema. Contains destination columns and category constraints.
    """

    def __init__(self, source_data: DataSourceModel, schema: Schema) -> None:
        self.core = CoreScript()
        self.parser = ParserScript()
        self.wrangle = WranglingScript()
        self.source_data = self.wrangle.get_dataframe_from_datasource(data=source_data)
        self.source_columns = source_data.columns
        self.schema = schema

    def parse(
        self, script: str
    ) -> Dict[str, Union[CategoryActionModel, FieldModel, ColumnModel, CategoryModel, List[CategoryModel]]]:
        """Generate the parsed dictionary of an initialised morph action script.

        Parameters
        ----------
        script: str
            An action script.

        Raises
        ------
        ValueError for any parsing errors.

        Returns
        -------
        dict
            Parsed dictionary of an initialised morph action script.
        """
        script = self.parser.get_normalised_script(script, self.source_columns)
        action_model = self.parser.get_anchor_action(script)
        if action_model.name not in ["ASSIGN_CATEGORY_UNIQUES", "ASSIGN_CATEGORY_BOOLEANS"]:
            raise ValueError(f"Invalid action ({action_model.name}) for this parser.")
        # Validate the category script and get the required components
        parsed = self.parser.get_action_class(action_model)().parse(script)
        destination, category, source, assigned, unassigned = None, None, None, None, None
        # Get source and source category terms
        source = self.parser.get_literal(parsed["source"])
        source = self.parser.get_field_model(source, self.source_columns)
        if not source:
            raise ValueError(f"Source column is not recognised ({parsed['source']}).")
        # Get values from source column as a numpy array
        column = self.source_data[source.name].array
        if parsed.get("source_category"):
            all_uniques = set(np.unique(column[~pd.isnull(column)]))
            assigned = self.get_assigned_uniques(parsed["source_category"])
            if set(assigned).difference(all_uniques):
                raise ValueError(
                    f"Assigned terms not found in source data column ({set(assigned).difference(all_uniques)})"
                )
            unassigned = [CategoryModel(**{"name": a}) for a in all_uniques.difference(set(assigned))]
            assigned = [CategoryModel(**{"name": a}) for a in assigned]
        # Get destination column and assigned category term
        destination = self.parser.get_literal(parsed["destination"])
        destination = self.schema.get_field(destination)
        category = self.parser.get_literal(parsed["category"])
        category = self.schema.get_field_category(field=destination.name, category=category)
        if not destination and category:
            raise ValueError(
                f"Destination field and category are not valid for this category action script ({parsed['destination']}, {parsed['category']})."
            )
        # Return validated terms
        return {
            "action": action_model,
            "destination": destination,
            "category": category,
            "source": source,
            "assigned": assigned,
            "unassigned": unassigned,
        }

    def get_unique_categories(self, script: str, column: np.array) -> List[CategoryModel]:
        """Get a list of unique categories from a source data array of values.

        Parameters
        ----------
        script: str
            An action script.

        Raises
        ------
        ValueError if the ACTION is not `ASSIGN_CATEGORY_UNIQUES`.

        Returns
        -------
        list of CategoryModel
        """
        action_model = self.parser.get_anchor_action(script)
        if action_model.name != "ASSIGN_CATEGORY_UNIQUES":
            raise ValueError("Boolean category assignment does not need unique references.")
        return [CategoryModel(**{"name": u}) for u in np.unique(column)]

    ###################################################################################################
    ### SUPPORT UTILITIES
    ###################################################################################################

    def get_assigned_uniques(self, text: str) -> List[str]:
        terms = list(self.parser.generate_contents(text))
        if len(terms) != 1:
            raise ValueError(f"Category assignment actions must not be nested. ({text}).")
        return [self.parser.get_literal(t) for t in self.parser.get_split_terms(terms[0][1], ",")]
