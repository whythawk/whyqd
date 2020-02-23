"""
Base class defining core functions for an Action.
"""
from copy import deepcopy
from whyqd.core import common as _c

class BaseAction:
    """
    Custom Actions inherit from this base class which describes the core functions and methodology for an Action.

    Actions should redefine `name`, `title`, `description`, `modifiers` and `structure`, as well as produce a 
    `transform` function. Everything else will probably remain as defined, but particularly complex Actions should
    modify as required.
    """
    def __init__(self):
        self.name = ""
        self.title = ""
        self.description = ""
        # `structure` defines the format in which an action is written, and validated in `has_valid_structure`
        # can be - typically - any of `field`, `value` or `modifier`
        # additional terms will require overriding the `has_valid_structure` function
        self.structure = ["field"]

    @property
    def modifiers(self):
        """
        Describes the modifiers for the Action. Typical modifiers are `+` or `-` but the Action can implement any
        type of modifier as part of the `transform` function.

        As an example::

            [
                {
                    "name": "+",
                    "title": "Add",
                    "type": "modifier"
                },
                {
                    "name": "-",
                    "title": "Subtract",
                    "type": "modifier"
                }
            ]

        Returns
        -------
        None or dict
            Dict representation of the modifiers.
        """
        return None

    @property
    def modifier_names(self):
        if self.modifiers:
            return [modifier["name"] for modifier in self.modifiers]
        return []

    def has_modifier(self, term):
        if self.modifiers and term in self.modifier_names:
            return True
        return False

    def get_modifier(self, term):
        if self.modifiers:
            for modifier in self.modifiers:
                if modifier["name"] == term:
                    return deepcopy(modifier)
        return {}

    def validates(self, structure, working_columns=[]):
        """
        Traverses a list defined by `*structure`, ensuring that the terms conform to that action's
        default structural requirements. Nested structures are permitted. Note that the
        responsibility for digging in to the nested structures lies with the calling function.

        The format for defining a `structure` is as follows::

            [action, column_name, [action, column_name]]

        e.g.::

            ["CATEGORISE", "+", ["ORDER", "column_1", "column_2"]]

        A calling function would specify::

            Action.validates(structure[1:], working_columns)

        Parameters
        ----------
        structure: list
            Each structure list must conform to the requirements for that action. Nested actions
            defined by nested lists.
        working_columns: list
            List of valid field names from the working data columns.

        Returns
        -------
        bool
            True if valid
        """
        if not structure:
            e = "A structure must contain at least one `field`."
            raise ValueError(e)
        term_set = len(self.structure)
        for field in _c.chunks(structure, term_set):
            if len(field) != term_set:
                return False
            for i, term in enumerate(self.structure):
                if term == "field" and isinstance(field[i], list):
                    # The calling function needs to handle recursion through the list
                    continue
                if term == "value" and not _c.get_field_type(field[i]):
                    # Special case for actions where a new value is created 
                    # Response depends on the `transform`
                    return False
                if term == "field" and field[i] not in working_columns:
                    return False
                if term == "modifier" and not self.has_modifier(field[i]):
                    return False
        return True

    @property
    def settings(self):
        """
        Returns the dict representation of the Action.

        Returns
        -------
        dict
            Dict representation of an Action.
        """
        action_settings = {
            "name": self.name,
            "type": "action",
            "description": self.description,
            "structure": self.structure
        }
        if self.modifiers:
            action_settings["modifiers"] = self.modifiers
        return action_settings

    def transform(self, df, field_name, structure, **kwargs):
        """
        Perform a transformation. This function must be overridden by child Actions and describe a unique
        new method.

        .. warning:: Assumes `validates` has been run.

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
            Containing the implementation of the Action
        """
        return df