# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar, Type, TYPE_CHECKING
import ast

if TYPE_CHECKING:
    from whyqd.models import CategoryActionModel, CategoryModel, FieldModel, MorphActionModel, SchemaActionModel
    from whyqd.crosswalk.base import BaseSchemaAction, BaseMorphAction, BaseCategoryAction
    from whyqd.core import SchemaDefinition


class ScriptParser:
    """Parsing utility functions for all types of action scripts.

    Supports parsing and validation of any action script of the form:

        "ACTION > [term] < [term]"

    Where term fields are optional. Has no opinion on what the terms are, or whether they are nested.
    """

    DESTINATION: ClassVar[str] = ">"
    SOURCE: ClassVar[str] = "<"
    PARAMETER: ClassVar[str] = "::"
    OPEN: ClassVar[str] = "["
    CLOSE: ClassVar[str] = "]"

    ###################################################################################################
    ### ACTION UTILITIES
    ###################################################################################################

    def get_action_model(self, *, action: str) -> SchemaActionModel | MorphActionModel | CategoryActionModel | None:
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
        from whyqd.crosswalk.actions import default_actions

        return next((da for da in default_actions if da.name == action.upper()), None)

    def get_action_from_script(
        self, *, script: str
    ) -> SchemaActionModel | MorphActionModel | CategoryActionModel | None:
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
        name = self.get_action_name(script=script)
        action = self.get_action_model(action=name)
        if not action:
            raise ValueError(f"Term '{name} is not a recognised ACTION.")
        return action

    def get_action_name(self, *, script: str) -> str:
        """The action a script names: its first term, which is always there, before any destination or source."""
        root = self.get_split_terms(script=script, by=self.SOURCE)
        return self.get_split_terms(script=root[0], by=self.DESTINATION)[0]

    def get_action_class(
        self, *, actn: SchemaActionModel | MorphActionModel | CategoryActionModel
    ) -> Type[BaseSchemaAction | BaseMorphAction | BaseCategoryAction]:
        """Return the ACTION class for an ACTION model.

        Parameters
        ----------
        action: SchemaActionModel, MorphActionModel, CategoryActionModel

        Returns
        -------
        class of Action
        """
        from whyqd.crosswalk.actions import actions

        return actions[actn.name]

    ###################################################################################################
    ### FIELD UTILITIES
    ###################################################################################################

    def get_schema_field(self, *, term: str, schema: SchemaDefinition | list[SchemaDefinition]) -> FieldModel:
        """Recover a field model from a string.

        Parameters
        ----------
        term: str
        schema: SchemaDefinition, or a list of SchemaDefinition comprising of the source and destination schemas.

        Raises
        ------
        ValueError if the field term is not recognised.

        Returns
        -------
        FieldModel
        """
        if not isinstance(schema, list):
            schema = [schema]
        field = None
        for s in schema:
            field = s.fields.get(name=term)
            if field:
                break
        if not field:
            e = f"Field name is not recognised from either of the source or destination schema fields ({term})."
            if len(schema) == 1:
                e = f"Field name is not recognised from the schema fields ({term})."
            raise ValueError(e)
        return field

    ###################################################################################################
    ### SCRIPT PARSING UTILITIES
    ###################################################################################################

    def generate_contents(self, *, text) -> list[tuple[int, str]]:
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
            if c == self.OPEN:
                stack.append(i)
            elif c == self.CLOSE and stack:
                start = stack.pop()
                yield (len(stack), text[start + 1 : i])

    def get_split_terms(self, *, script: str, by: str, maxsplit: int = 1) -> list[str]:
        # https://docs.python.org/3/library/stdtypes.html#str.split
        # str.split(sep=None, maxsplit=-1)
        return [s.strip() for s in script.split(sep=by, maxsplit=maxsplit)]

    def get_literal(self, *, text: str) -> str:
        literal = text
        try:
            literal = ast.literal_eval(text)
        except (ValueError, TypeError):
            pass
        except SyntaxError:
            # `literal_eval` strips special characters, leading to syntax errors
            if text.startswith("'") and text.endswith("'"):
                literal = text[1:-1]
        return literal

    def get_listed_literal(self, *, text: str) -> list[str]:
        return [self.get_literal(text=t) for t in text.split(",")]

    def get_hexed_script(self, *, script: str, fields: list[CategoryModel | FieldModel]) -> str:
        """Replace field names with its hex. Ensures that any fruity characters literals don't cause havoc during
        parsing.

        Parameters
        ----------
        script: str
        fields: list of CategoryModel, FieldModel

        Returns
        -------
        str
        """
        # Going to sort these so the longest is first to avoid replacing partial matches
        # https://docs.python.org/3/howto/sorting.html
        # Bool category names need to be converted to strings
        for f in sorted(fields, key=lambda f: len(str(f.name)), reverse=True):
            if f"'{f.name}'" in script:
                script = script.replace(f"'{f.name}'", f"'{f.uuid.hex}'")
        return script


class SchemaPairParser:
    """What every action script's parser shares: the source and destination schemas its terms are found in."""

    def __init__(self) -> None:
        self.parser = ScriptParser()
        self.schema_source = None
        self.schema_destination = None

    @property
    def schemas(self) -> list[SchemaDefinition]:
        """The schemas set, source first."""
        return [s for s in (self.schema_source, self.schema_destination) if s]

    def set_schema(
        self, *, schema_source: SchemaDefinition | None = None, schema_destination: SchemaDefinition | None = None
    ) -> None:
        """Set the schemas a script's terms are found in.

        Parameters:
          schema_source: The source schema.
          schema_destination: The destination schema.

        Raises:
          ValueError: If either is missing.
        """
        if not schema_source or not schema_destination:
            raise ValueError("Schema for both source and destination has not been provided.")
        self.schema_source = schema_source
        self.schema_destination = schema_destination
