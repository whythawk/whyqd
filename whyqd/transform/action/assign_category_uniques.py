from __future__ import annotations
from typing import Dict

from whyqd.transform.base import BaseCategoryAction


class Action(BaseCategoryAction):
    """`CATEGORISE` support function which must be run *before* it to derive unique category terms from unique
    values in a source data column.

    `ASSIGN` subset of unique values (or all booleans) to a specified `CategoryModel` in a destination `ColumnModel`.

    Scripts must be 'flat' and are of the form::

        "ASSIGN_CATEGORY_UNIQUES > 'destination_field'::'destination_category' < 'source_column'::['unique_source_term', 'unique_source_term', etc.]"

    Where:

    * `destination_field` is a `FieldModel` and is the destination column. The `::` linked `CategoryModel` defines what
       term the source values are to be assigned.
    * `list` of `CategoryModel` - unique values from `ColumnModel` - will be assigned `::CategoryModel`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "ASSIGN_CATEGORY_UNIQUES"
        self.title = "Assign category uniques"
        self.description = (
            "Assign unique values in a source data column as categorical unique terms defined in the Schema."
        )
        self.structure = "unique"

    def parse(self, *, script: str) -> Dict[str, str]:
        """Validates term requirements for this category action script.

        Script is of the form::

            "ACTION > 'destination_column'::term < 'source_column'::[term]"

        Which is inherited as::

            {
                "action": ACTION,
                "destination": 'destination_column',
                "category": term,
                "source": 'source_column',
                "source_category": [term]
            }

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
            Parsed dictionary of validated split strings for further processing.
        """
        parsed = super().parse(script=script)
        # Class-based term validation
        if parsed["action"] != "ASSIGN_CATEGORY_UNIQUES":
            raise ValueError(f"Action not valid for this 'ASSIGN_CATEGORY_UNIQUES' parser ({parsed['action']}).")
        if not parsed.get("source_category"):
            raise ValueError(
                "'ASSIGN_CATEGORY_UNIQUES' category assignment requires unique source category references."
            )
        return parsed
