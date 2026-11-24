# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from collections.abc import Iterator
from typing import ClassVar, Type, TYPE_CHECKING
import ast

if TYPE_CHECKING:
    from whyqd.models import CategoryActionModel, CategoryModel, FieldModel, MorphActionModel, SchemaActionModel
    from whyqd.crosswalk.base import BaseSchemaAction, BaseMorphAction, BaseCategoryAction
    from whyqd.core import SchemaDefinition


class ScriptParser:
    """The grammar every action script shares, `ACTION > destination < source`, each term but the action optional.

    It splits a script into its terms, reads their literals, finds the fields they name, and looks up an action by
    name. It has no opinion on what the terms mean, or whether they are nested: each action's parser decides that.

    Examples:
      ```python
      from whyqd.parsers.script import ScriptParser

      parser = ScriptParser()
      parser.get_action_name(script="RENAME > 'name' < ['Name']")  # "RENAME"
      ```
    """

    DESTINATION: ClassVar[str] = ">"
    SOURCE: ClassVar[str] = "<"
    PARAMETER: ClassVar[str] = "::"
    OPEN: ClassVar[str] = "["
    CLOSE: ClassVar[str] = "]"

    def get_action_model(self, *, action: str) -> SchemaActionModel | MorphActionModel | CategoryActionModel | None:
        """An action's settings, by its name in any case, or `None` where no action has it."""
        from whyqd.crosswalk.actions import default_actions

        return next((da for da in default_actions if da.name == action.upper()), None)

    def get_action_from_script(
        self, *, script: str
    ) -> SchemaActionModel | MorphActionModel | CategoryActionModel | None:
        """The settings of the action a script names.

        Raises:
          ValueError: If its first term names no action.
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
        """The class that runs the action whose settings are `actn`."""
        from whyqd.crosswalk.actions import actions

        return actions[actn.name]

    def get_schema_field(self, *, term: str, schema: SchemaDefinition | list[SchemaDefinition]) -> FieldModel:
        """The field a term names, by its name or its hex, from the first schema that has it.

        Parameters:
          term: A field's name or hex.
          schema: One schema, or the source and destination, in the order they are searched.

        Raises:
          ValueError: If no schema has the field.
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

    def generate_contents(self, *, text: str) -> Iterator[tuple[int, str]]:
        """Each bracketed part of `text`, as its depth and contents, innermost and rightmost first, after
        [Stack Overflow, answer 4285211](https://stackoverflow.com/a/4285211/295606)."""
        stack = []
        for i, c in enumerate(text):
            if c == self.OPEN:
                stack.append(i)
            elif c == self.CLOSE and stack:
                start = stack.pop()
                yield (len(stack), text[start + 1 : i])

    def get_split_terms(self, *, script: str, by: str, maxsplit: int = 1) -> list[str]:
        """`script` split at `by`, `maxsplit` times (`-1` for every one), each part stripped."""
        return [s.strip() for s in script.split(sep=by, maxsplit=maxsplit)]

    def get_literal(self, *, text: str) -> str | int | float | bool | list | tuple:
        """The Python literal `text` writes, or a quoted term its quotes removed where it is not one; otherwise the
        text as it is."""
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

    def get_listed_literal(self, *, text: str) -> list:
        """Each comma-separated part of `text` as `get_literal` reads it."""
        return [self.get_literal(text=t) for t in text.split(",")]

    def get_hexed_script(self, *, script: str, fields: list[CategoryModel | FieldModel]) -> str:
        """The script with each quoted name of `fields` as its hex, so a name holding the grammar's own characters
        cannot break a split."""
        # Longest first, so a name inside another is not replaced within it; a boolean category's name is not text
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
