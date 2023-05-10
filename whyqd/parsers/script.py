from __future__ import annotations
from typing import Type, TYPE_CHECKING
import ast

from whyqd.models import SchemaActionModel, MorphActionModel, CategoryActionModel

if TYPE_CHECKING:
    from whyqd.models import CategoryModel, FieldModel
    from whyqd.crosswalk.base import BaseSchemaAction, BaseMorphAction, BaseCategoryAction
    from whyqd.core import SchemaDefinition


class ScriptParser:
    """Parsing utility functions for all types of action scripts.

    Supports parsing and validation of any action script of the form:

        "ACTION > [term] < [term]"

    Where term fields are optional. Has no opinion on what the terms are, or whether they are nested.
    """

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
        # Get the action, where any of the `<` or `>` referenced terms may be absent.
        root = self.get_split_terms(script=script, by="<")
        # There must always be a first term and it must *always* be an ACTION. Everything else is optional.
        root = self.get_split_terms(script=root[0], by=">")
        action = self.get_action_model(action=root[0])
        if not action:
            raise ValueError(f"Term '{root[0]} is not a recognised ACTION.")
        return action

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
            if c == "[":
                stack.append(i)
            elif c == "]" and stack:
                start = stack.pop()
                yield (len(stack), text[start + 1 : i])

    def get_split_terms(self, *, script: str, by: str) -> list[str]:
        return [s.strip() for s in script.split(by)]

    def get_literal(self, *, text: str) -> str:
        literal = text
        try:
            literal = ast.literal_eval(text)
        except ValueError:
            pass
        return literal

    def get_listed_literal(self, *, text: str) -> list[str]:
        listed_literal = []
        for t in text.split(","):
            try:
                listed_literal.append(self.get_literal(text=t))
            except SyntaxError:
                if t:
                    listed_literal.append(t)
        return listed_literal

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
