from __future__ import annotations
from typing import List, Iterator, Type, Tuple, Union, TYPE_CHECKING
import ast

from ..action import default_actions, actions

if TYPE_CHECKING:
    from ..models import (
        SchemaActionModel,
        MorphActionModel,
        CategoryActionModel,
        ColumnModel,
        CategoryModel,
        FieldModel,
    )
    from ..base import BaseSchemaAction, BaseMorphAction, BaseCategoryAction
    from ..schema import Schema


class ParserScript:
    """Parsing utility functions for all types of action scripts.

    Supports parsing and validation of any action script of the form:

        "ACTION > [term] < [term]"

    Where term fields are optional. Has no opinion on what the terms are, or whether they are nested.
    """

    ###################################################################################################
    ### ACTION UTILITIES
    ###################################################################################################

    def get_action_model(self, action: str) -> Union[SchemaActionModel, MorphActionModel, CategoryActionModel, None]:
        """Return a specific set of Action definitions in response to an Action name.

        Parameters
        ----------
        action: str
            An Action name.

        Returns
        -------
        SchemaActionModel, MorphActionModel, CategoryActionModel or None.
            For the requested Action name. Or None, if it doesn't exist.
        """
        return next((da for da in default_actions if da.name == action.upper()), None)

    def get_anchor_action(self, script: str) -> Union[SchemaActionModel, MorphActionModel, CategoryActionModel, None]:
        """Return the first action term from a script as its Model type.

        Parameters
        ----------
        script: str
            Action script, defined as "ACTION > TERM < TERM"

        Raises
        ------
        ValueError if not a valid ACTION.

        Returns
        -------
        SchemaActionModel, MorphActionModel, or CategoryActionModel.
        """
        # Get the action, where any of the `<` or `>` referenced terms may be absent.
        root = self.get_split_terms(script, "<")
        # There must always be a first term and it must *always* be an ACTION. Everything else is optional.
        root = self.get_split_terms(root[0], ">")
        action = self.get_action_model(root[0])
        if not action:
            raise ValueError(f"Term '{root[0]} is not a recognised ACTION.")
        return action

    def get_action_class(
        self, actn: Union[SchemaActionModel, MorphActionModel, CategoryActionModel]
    ) -> Type[Union[BaseSchemaAction, BaseMorphAction, BaseCategoryAction]]:
        """Return the ACTION class for an ACTION model.

        Parameters
        ----------
        action: SchemaActionModel, MorphActionModel, CategoryActionModel

        Returns
        -------
        class of Action
        """
        return actions[actn.name]

    ###################################################################################################
    ### FIELD UTILITIES
    ###################################################################################################

    def get_field_model(
        self, name: str, fields: List[Union[ColumnModel, CategoryModel, FieldModel]]
    ) -> Union[ColumnModel, CategoryModel, FieldModel]:
        """Recover a field model from a string.

        Parameters
        ----------
        name: str
        fields: list of ColumnModel, CategoryModel, FieldModel

        Returns
        -------
        Union[ColumnModel, CategoryModel, FieldModel]
        """
        # It is statistically almost impossible to have a field name that matches a randomly-generated UUID
        # Can be used to recover fields from hex
        return next((f for f in fields if f.name == name or f.uuid.hex == name), None)

    def get_field_from_script(
        self, name: str, fields: List[Union[ColumnModel, FieldModel]], schema: Type[Schema]
    ) -> Union[ColumnModel, FieldModel]:
        """Recover a field model from a string.

        Parameters
        ----------
        name: str
        fields: list of ColumnModel, FieldModel
        schema: schema

        Raises
        ------

        Returns
        -------
        Union[ColumnModel, CategoryModel, FieldModel]
        """
        # If a column name is the same as a schema name, it's probably best to get the schema first...
        # Is it in the schema?
        field = schema.get_field(name)
        if not field:
            # Is it a ColumnModel?
            field = self.get_field_model(name, fields)
        if not field:
            raise ValueError(
                f"Field name is not recognised from either of the table columns, or the schema fields ({name})."
            )
        return field

    ###################################################################################################
    ### SCRIPT PARSING UTILITIES
    ###################################################################################################

    def generate_contents(self, text) -> Iterator[Tuple[int, str]]:
        """Generate parenthesized contents in string as pairs (level, contents).

        Parameters
        ----------
        text: str

        Returns
        -------
        Generator

        References
        ----------
        https://stackoverflow.com/a/4285211/295606
        """
        stack = []
        for i, c in enumerate(text):
            if c == "[":
                stack.append(i)
            elif c == "]" and stack:
                start = stack.pop()
                yield (len(stack), text[start + 1 : i])

    def get_split_terms(self, script: str, by: str) -> List[str]:
        return [s.strip() for s in script.split(by)]

    def get_literal(self, text: str) -> str:
        literal = text
        try:
            literal = ast.literal_eval(text)
        except ValueError:
            pass
        return literal

    def get_listed_literal(self, text: str) -> List[str]:
        listed_literal = []
        for t in text.split(","):
            try:
                listed_literal.append(self.get_literal(t))
            except SyntaxError:
                if t:
                    listed_literal.append(t)
        return listed_literal

    def get_normalised_script(self, script: str, fields: List[Union[ColumnModel, CategoryModel, FieldModel]]) -> str:
        """Replace field names with its hex. Ensures that any fruity characters literals don't cause havoc during
        parsing.

        Parameters
        ----------
        script: str
        fields: list of ColumnModel, CategoryModel, FieldModel

        Returns
        -------
        str
        """
        # Going to sort these so the longest is first to avoid replacing partial matches
        # https://docs.python.org/3/howto/sorting.html
        for f in sorted(fields, key=lambda f: len(f.name), reverse=True):
            if f.name in script:
                script = script.replace(f.name, f.uuid.hex)
        return script
