from __future__ import annotations
from typing import List, Union, Optional, TYPE_CHECKING


if TYPE_CHECKING:
    import modin.pandas as pd
    from whyqd.models import ModifierModel, FieldModel, SchemaActionModel, ColumnModel


class BaseSchemaAction:
    """Actions inherit from this base class which describes the core functions and methodology for an Action.

    Actions should redefine `name`, `title`, `description`, `modifiers` and `structure`, as well as produce a
    `transform` function. Everything else will probably remain as defined, but particularly complex Actions should
    modify as required.

    `structure` can be an empty list, but an Action may be defined by these parameters:

    * `modifier`: modifiers, of type `ModifierModel` defined by the ACTION and defining a `transform`.
    * `field`: the specific columns effected by the morph, a `list` of `ColumnModel` or, rarely, `FieldModel`.

    A standard script is::

        "ACTION > 'destination_field' < [modifier 'source_field', modifier 'source_field']"

    Where the structure of the source array is defined by the ACTION.
    """

    def __init__(self) -> None:
        from whyqd.parsers import CoreParser, DataSourceParser

        self.reader = DataSourceParser()
        self.core = CoreParser()
        self.name = ""
        self.title = ""
        self.description = ""
        # `structure` defines the format in which an action is written, and validated
        # can be - typically - any of `ColumnModel`, `ModifierModel`
        # additional terms will require overriding the `has_valid_structure` function
        self.structure = []

    @property
    def modifiers(self) -> Union[None, List[ModifierModel]]:
        """
        Describes the ModifierModels for the Action. Typical modifiers are `+` or `-` but the Action can implement any
        type of modifier as part of the `transform` function.

        As an example::

            [
                ModifierModel(**{
                    "name": "+",
                    "title": "Add",
                    "type": "modifier"
                }),
                ModifierModel(**{
                    "name": "-",
                    "title": "Subtract",
                    "type": "modifier"
                })
            ]

        Returns
        -------
        None or ModifierModel
            ModifierModel representation of the modifiers.
        """
        return None

    @property
    def modifier_terms(self) -> list[str]:
        if self.modifiers:
            return [m.name for m in self.modifiers]
        return []

    def get_modifier(self, *, term: str) -> Union[ModifierModel, None]:
        """Return a specific set of Modifier definitions in response to an Modifier name.

        Parameters
        ----------
        term: str
            A Modifier name.

        Returns
        -------
        ModifierModel, or None
            For the requested Modifier name. Or None, if it doesn't exist.
        """
        return next((m for m in self.modifiers if m.name == term), None)

    @property
    def settings(self) -> SchemaActionModel:
        """
        Returns the dict representation of the Action.

        Returns
        -------
        dict
            Dict representation of an Action.
        """
        from whyqd.models import SchemaActionModel

        action_settings = {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "structure": self.structure,
        }
        if self.modifiers:
            action_settings["modifiers"] = self.modifiers
        return SchemaActionModel(**action_settings)

    def validate(self, *, destination: FieldModel, source: list) -> bool:
        """
        Validate that script source structure conforms to the ACTION structure.

        Returns
        -------
        bool
        """
        if not isinstance(source, list):
            raise ValueError(f"Action source script does not conform to required structure. ({source})")
        for chunk in self.core.chunks(lst=source, n=len(self.structure)):
            # Loops through the phrasing of the structure, and checks that each term is as expected
            # e.g. [ModifierModel, FieldModel] for [modifier1, field1, modifier2, field2]
            # does not check that the actual terms match, though
            for i, term in enumerate(self.structure):
                if isinstance(chunk[i], term):
                    continue
                elif isinstance(chunk[i], dict):
                    # Nested source
                    if not chunk[i].get("action") and not not chunk[i].get("source"):
                        raise ValueError(f"Nested script does not conform to required structure. ({chunk[i]})")
                    chunk[i]["action"].validate(source=chunk[i]["source"])
                else:
                    raise ValueError(
                        f"Source structure ({chunk}) doesn't conform to ACTION structure requirements ({self.structure})."
                    )
        return True

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: Optional[Union[FieldModel, ColumnModel]] = None,
        source: Optional[List[Union[ColumnModel, ModifierModel]]] = None,
    ) -> pd.DataFrame:
        """
        Perform a transformation. This function must be overridden by child Actions and describe a unique
        new method.

        .. warning:: Assumes that is a valid call. Will raise exceptions from inside Pandas if not.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        destination: FieldModel or ColumnModel, default None
            Destination column for the result of the Action. If required.
        source: list of ColumnModel and / or ModifierModel
            List of source columns and modifiers for the action. If required.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        return df
