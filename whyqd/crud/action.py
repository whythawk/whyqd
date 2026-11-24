# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID

from whyqd.crud.base import CRUDBase
from whyqd.models import ActionScriptModel
from whyqd.parsers.action import ActionParser
from whyqd.parsers.category import CategoryParser
from whyqd.parsers.morph import MorphParser
from whyqd.parsers.script import ScriptParser
from whyqd.crosswalk.base import BaseSchemaAction, BaseMorphAction, BaseCategoryAction

if TYPE_CHECKING:
    import pandas as pd
    from whyqd.core import SchemaDefinition
    from whyqd.models import FieldModel


class CRUDAction(CRUDBase[ActionScriptModel]):
    """Create, read, update, and delete a crosswalk's steps. Usually instantiated as part of a
    [CrosswalkDefinition](crosswalk.md) and accessed as `.actions`.

    [Base CRUD operations](basecrud.md) are common for both `CRUDField` and `CRUDAction`.

    Examples:
      ```python
      import whyqd as qd

      crosswalk = qd.CrosswalkDefinition()
      crosswalk.set(schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION)
      # Create the crosswalk
      schema_scripts = [
          "DEBLANK",
          "DEDUPE",
          "DELETE_ROWS < [0, 1, 2, 3]",
          "PIVOT_LONGER > ['year', 'values'] < ['1960', '1961', '1962']",
          "RENAME > 'indicator_code' < ['Indicator Code']",
          "RENAME > 'indicator_name' < ['Indicator Name']",
          "RENAME > 'country_code' < ['Country Code']",
          "RENAME > 'country_name' < ['Country Name']",
      ]
      crosswalk.actions.add_multi(terms=schema_scripts)
      ```

    Parameters:
      schema_source: A [SchemaDefinition](schema.md) for access to source schema definitions and operations.
      schema_destination: A [SchemaDefinition](schema.md) for access to destination schema definitions.
    """

    def __init__(
        self, *, schema_source: SchemaDefinition | None = None, schema_destination: SchemaDefinition | None = None
    ):
        super().__init__(ActionScriptModel)
        self.parser = ScriptParser()
        self.schema_source = None
        self.schema_destination = None
        self.uncrossed = set()
        if schema_source and schema_destination:
            self.set_schema(schema_source=schema_source, schema_destination=schema_destination)

    def get(self, *, name: str | UUID) -> ActionScriptModel | None:
        """Get a specific script from the list of scripts, called by a unique id.

        Parameters:
          name: Scripts may be duplicated, but UUIDs will be unique.

        Returns:
          An ActionScriptModel or None, of no such script is found.
        """
        uid = self.get_hex(name=name)
        if self.multi:
            return next((m for m in self.multi if m.uuid.hex == uid), None)
        return None

    def add(self, *, term: str | ActionScriptModel) -> None:
        """Add the string term for an action script. Validate as well. Does not test for uniqueness.

        Parameters:
          term: A string term, or ActionScriptModel conforming to the script structure for a specific action.

        Raises:
          ValueError: If script is invalid. In most cases, you should get reasonable feedback from the error message
                      as to how to fix the problem.
        """
        # Validate the script

        if isinstance(term, (dict, ActionScriptModel)):
            if isinstance(term, dict):
                term = ActionScriptModel(**term)
            parsed = self.parse(script=term.script)
            self.multi.append(term)
        else:
            parsed = self.parse(script=term)
            self.multi.append(ActionScriptModel(**{"script": term}))
        self.reconcile_crosswalk(fields=parsed.get("destination", []))

    def update(self, *, term: ActionScriptModel | dict) -> None:
        """Update the parameters for a specific term, called by a unique `UUID`. If the `UUID` does not exist, then this
        will raise a `ValueError`.

        Parameters:
          term: A dictionary conforming to the ActionScriptModel.

        Raises:
          ValueError: If the term does not exist.
        """
        if isinstance(term, dict):
            term = self.model(**term)
        # Create a temporary FieldModel
        old_term = self.get(name=term.uuid.hex)
        if not old_term:
            raise ValueError(
                f"No step `{term.uuid}` is in the crosswalk to update (`{term.script}`). Add it first. "
                "[whyqd:term-missing]"
            )
        self.parse(script=term)
        old_term.script = term.script
        self.recount()

    def remove(self, *, name: str | UUID) -> None:
        """Remove a specific term, called by a unique `UUID`.

        Parameters:
          name: Unique model UUID for the script.
        """
        script = self.get(name=name)
        if script:
            self.multi[:] = [m for m in self.multi if m.uuid.hex != script.uuid.hex]
            self.recount()

    def parse(self, *, script: str | ActionScriptModel) -> dict:
        """Parse a script for any action, of any type, and return the corresponding transformation dictionary structure.
        Can also be used as a validation step.

        Parameters:
          script: A string term, or ActionScriptModel conforming to the script structure for a specific action.

        Raises:
          ValueError: If the script term is not valid, or if the schemas are not set.

        Returns:
         ```python
          # A dictionary of the appropriate form for the ACTION
          {
              "action": BaseSchemaAction,
              "destination": FieldModel,
              "source": list[ModifierModel | FieldModel]
          }

          {
              "action": BaseMorphAction,
              "destination": FieldModel | list[FieldModel],
              "source": list[FieldModel],
              "rows": list[int],
              "source_param": str,
              "destination_param": str
          }

          {
              "action": BaseCategoryAction,
              "destination": FieldModel,
              "category": CategoryModel,
              "source": list[FieldModel],
              "assigned": list[CategoryModel],
              "unassigned": list[CategoryModel],
          }
          ```
        """
        if isinstance(script, ActionScriptModel):
            script = script.script
        action = self.get_action(script=script)
        return self.get_action_parser(script=script, action=action).parse(script=script, action=action)

    def validate(self, *, required: bool = False) -> list[FieldModel]:
        """Return the list of destination schema fields which are still to be crosswalked.

        Parameters:
          required: Limit the unreconciled crosswalk fields to only those which are required.

        Returns:
          List of FieldModels which are required but are still undefined by an ActionScriptModel.
        """
        if required:
            return [
                f
                for f in self.schema_destination.get.fields
                if f.uuid in self.uncrossed and f.constraints and f.constraints.required
            ]
        return [f for f in self.schema_destination.get.fields if f.uuid in self.uncrossed]

    def transform(self, *, df: pd.DataFrame, script: str | ActionScriptModel) -> pd.DataFrame:
        """Return a transformed dataframe according to a single script.

        Parameters:
          df: A pandas dataframe.
          script: A string term, or ActionScriptModel conforming to the script structure for a specific action.

        Returns:
          Transformed dataframe.
        """
        if isinstance(script, ActionScriptModel):
            script = script.script
        action = self.get_action(script=script)
        action_parser = self.get_action_parser(script=script, action=action)
        return action_parser.transform(df=df, **action_parser.parse(script=script, action=action))

    def rows(self) -> list[int]:
        """Every row a row-level action names, in script order."""
        return [r for script in self.get_all() for r in self.parse(script=script).get("rows") or []]

    def transform_all(self, *, df: pd.DataFrame) -> pd.DataFrame:
        """Return a transformed dataframe after processing all scripts.

        Parameters:
          df: A pandas dataframe.

        Returns:
          Transformed dataframe.
        """
        for script in self.get_all():
            df = self.transform(df=df, script=script)
        return df

    def set_schema(
        self, *, schema_source: SchemaDefinition | None = None, schema_destination: SchemaDefinition | None = None
    ) -> None:
        """Set the schemas the steps map between, every destination field unmapped until a step builds it.

        Parameters:
          schema_source: The source [SchemaDefinition](schema.md).
          schema_destination: The destination [SchemaDefinition](schema.md).
        """
        if not schema_source or not schema_destination:
            raise ValueError("Schema for both source and destination has not been provided.")
        self.schema_source = schema_source
        self.schema_destination = schema_destination
        self.uncrossed = {field.uuid for field in self.schema_destination.get.fields}

    def get_action(self, *, script: str) -> BaseSchemaAction | BaseMorphAction | BaseCategoryAction:
        """Return the first action term from a script as its Model type.

        Parameters:
          script: A string term conforming to the script structure for a specific action.

        Raises:
          ValueError: If not a valid ACTION.

        Returns:
          The action model type conforming to the requirements for a script.
        """
        action = self.parser.get_action_from_script(script=script)
        return self.parser.get_action_class(actn=action)()

    def get_action_parser(
        self, *, script: str, action: BaseSchemaAction | BaseMorphAction | BaseCategoryAction | None = None
    ) -> ActionParser | MorphParser | CategoryParser:
        """Return the parser for a script's kind of action, its schemas set.

        Parameters:
          script: A string term conforming to the script structure for a specific action.
          action: The action model type conforming to the requirements for a script.

        Raises:
          ValueError: If the script can't be parsed.

        Returns:
          An `ActionParser`, `MorphParser`, or `CategoryParser`, as [TransformDefinition](transform.md) and
          [CrosswalkDefinition](crosswalk.md) use it.
        """
        if not action:
            action = self.get_action(script=script)
        parsers = {BaseSchemaAction: ActionParser, BaseMorphAction: MorphParser, BaseCategoryAction: CategoryParser}
        kind = next((parser for base, parser in parsers.items() if isinstance(action, base)), None)
        if kind is None:
            raise ValueError(f"Script cannot be parsed ({script}).")
        parser = kind()
        parser.set_schema(schema_source=self.schema_source, schema_destination=self.schema_destination)
        return parser

    def reconcile_crosswalk(self, *, fields: FieldModel | list[FieldModel] | None) -> None:
        """Mark the destination fields a step builds as mapped."""
        if fields is None:
            return
        if not isinstance(fields, list):
            fields = [fields]
        for f in fields:
            # A script's name finds the source field first, where both schemas have one of that name
            target = self.schema_destination.fields.get(name=f.name) or f
            self.uncrossed = self.uncrossed - {target.uuid}

    def recount(self) -> None:
        """Count again, from every step, the destination fields none builds, as a removal or change needs: a field
        two steps build stays mapped while either remains."""
        self.uncrossed = {field.uuid for field in self.schema_destination.get.fields}
        for step in self.multi:
            self.reconcile_crosswalk(fields=self.parse(script=step).get("destination", []))
