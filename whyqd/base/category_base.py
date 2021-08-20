from __future__ import annotations
from typing import Dict, TYPE_CHECKING


if TYPE_CHECKING:
    from ..models import CategoryActionModel


class BaseCategoryAction:
    """Category Actions are support utilities for CATEGORY actions. These inherit from this base class which describes
    the core functions and methodology for this support Action.

    Actions should redefine `name`, `title`, `description`, and `structure`. There is no transform function.

    `structure` is defined by these parameters:

    * `boolean`: terms will be unique.
    * `unique`: the specific columns effected by the morph, a `list` of `ColumnModel` or, rarely, `FieldModel`.

    A standard script is::

        "ACTION > 'destination_column::destination_category' < ['unique_term', 'unique_term', ...]"

    Where the structure of the source array is defined by the ACTION.
    """

    def __init__(self) -> None:
        self.name = ""
        self.title = ""
        self.description = ""
        self.structure = None

    @property
    def settings(self) -> CategoryActionModel:
        """
        Returns the CategoryActionModel representation of the Action.

        Returns
        -------
        CategoryActionModel
            CategoryActionModel representation of an Action.
        """
        from whyqd.models import CategoryActionModel

        action_settings = {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "structure": self.structure,
        }
        return CategoryActionModel(**action_settings)

    def parse(self, script: str) -> Dict[str, str]:
        """Base parser for the CategoryAction script. Produces required terms and validates against this
        CategoryAction's structure requirements.

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
        from whyqd.parsers import ParserScript

        parser = ParserScript()
        parsed = {}
        # Get unique assignment terms
        root = parser.get_split_terms(script, "<")
        if len(root) != 2:
            raise ValueError(f"Category action script has no source terms ({script}).")
        # Extract source terms
        source_terms = parser.get_split_terms(root[1], "::")
        parsed["source"] = source_terms[0]
        if len(source_terms) == 2:
            parsed["source_category"] = source_terms[1]
        root = parser.get_split_terms(root[0], ">")
        # Extract destination terms
        if len(root) != 2:
            raise ValueError(f"Category action script has no destination terms ({script}).")
        destination_terms = parser.get_split_terms(root[1], "::")
        if len(destination_terms) != 2:
            raise ValueError(f"Category action script has no destination category term ({script}).")
        parsed["destination"] = destination_terms[0]
        parsed["category"] = destination_terms[1]
        # And the action term
        parsed["action"] = root[0]
        return parsed
