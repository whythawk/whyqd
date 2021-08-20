from __future__ import annotations
from typing import Dict

from whyqd.base import BaseCategoryAction


class Action(BaseCategoryAction):
    """`CATEGORISE` support function which must be run *before* it to derive boolean category terms from
    values in a source data column.

    Scripts must be 'flat' and are of the form::

        "ASSIGN_CATEGORY_BOOLEANS > 'destination_field'::bool < 'source_column'"

    Where:

    * `destination_field` is a `FieldModel` and is the destination column. The `::` linked `CategoryModel` defines
      what term the source values are to be assigned.
    * Values from the `source_column` `ColumnModel` are treated as boolean `True` or `False`, defined by `::bool`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "ASSIGN_CATEGORY_BOOLEANS"
        self.title = "Assign category booleans"
        self.description = "Assign values in a source data column as categorical boolean terms based on whether values are present, or are null."
        self.structure = "boolean"

    def parse(self, script: str) -> Dict[str, str]:
        """Validates term requirements for this category action script.

        Script is of the form::

            "ACTION > 'destination_column'::term < 'source_column'"

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
        parsed = super().parse(script)
        # Class-based term validation
        if parsed["action"] != "ASSIGN_CATEGORY_BOOLEANS":
            raise ValueError(f"Action not valid for 'ASSIGN_CATEGORY_BOOLEANS' parser ({parsed['action']}).")
        if parsed.get("source_category"):
            raise ValueError("'ASSIGN_CATEGORY_BOOLEANS' category assignment does not need unique references.")
        return parsed
