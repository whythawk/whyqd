from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import UUID
import modin.pandas as pd

from whyqd.crud.base import CRUDBase
from whyqd.models import ActionScriptModel
from whyqd.parsers import ScriptParser, ActionParser, MorphParser, CategoryParser
from whyqd.crosswalk.base import BaseSchemaAction, BaseMorphAction, BaseCategoryAction

if TYPE_CHECKING:
    from whyqd.core import SchemaDefinition
    from whyqd.models import FieldModel


class CRUDAction(CRUDBase[ActionScriptModel]):
    """Create, Read, Update and Delete Field Models. Usually instantiated as part of a
    [CrosswalkDefinition](crosswalk.md) and accessed as `.actions`.

    [Base CRUD operations](basecrud.md) are common for both `CRUDField` and `CRUDAction`.

    Example:
      ```python
      import whyqd as qd

      crosswalk = qd.CrosswalkDefinition()
      crosswalk.set(schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION)
      # Create the crosswalk
      schema_scripts = [
          "DEBLANK",
          "DEDUPE",
          "DELETE_ROWS < [0, 1, 2, 3]",
          f"PIVOT_LONGER > ['year', 'values'] < {datasource.model[0].names[4:]}",
          "RENAME > 'indicator_code' < ['Indicator Code']",
          "RENAME > 'indicator_name' < ['Indicator Name']",
          "RENAME > 'country_code' < ['Country Code']",
          "RENAME > 'country_name' < ['Country Name']",
      ]
      crosswalk.actions.add_multi(terms=schema_scripts)
      ```

    Parameters:
      schema_source: A [SchemaDefinition](schema.md) for access to source schema definitions and operations.
      schema_destination: A [SchemaDefinition](schema.md) for access to destination schema definitions and operations.
    """

    def __init__(self, *, schema_source: SchemaDefinition = None, schema_destination: SchemaDefinition = None):
        super().__init__(ActionScriptModel)
        self.parser = ScriptParser()
        self.schema_source = None
        self.schema_destination = None
        self.uncrossed = []
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
            raise ValueError(f"ActionScriptModel {term.script} does not exist.")
        # And update the original data
        parsed = self.parse(script=term)
        # It parses, ensure reconciliation
        old_parsed = self.parse(script=old_term)
        self.reconcile_crosswalk(fields=old_parsed.get("destination", []), remove=True)
        old_term.script = term.script
        self.reconcile_crosswalk(fields=parsed.get("destination", []))

    def remove(self, *, name: str | UUID) -> None:
        """Remove a specific term, called by a unique `UUID`.

        Parameters:
          name: Unique model UUID for the script.
        """
        script = self.get(name=name)
        if script:
            parsed = self.parse(script=script)
            # https://stackoverflow.com/a/1235631/295606
            self.multi[:] = [m for m in self.multi if m.uuid.hex != script.uuid.hex]
            self.reconcile_crosswalk(fields=parsed.get("destination", []), remove=True)

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
        action_parser = self.get_action_parser(script=script, action=action)()
        action_parser.set_schema(schema_source=self.schema_source, schema_destination=self.schema_destination)
        return action_parser.parse(script=script, action=action)

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

    ###################################################################################################
    ### TABULAR DATA TRANSFORMATION UTILITIES
    ###################################################################################################

    def transform(self, *, df: pd.DataFrame, script: str | ActionScriptModel) -> pd.DataFrame:
        """Return a transformed dataframe according to a single script.

        Parameters:
          df: A Pandas (Modin) dataframe.
          script: A string term, or ActionScriptModel conforming to the script structure for a specific action.

        Returns:
          Transformed dataframe.
        """
        parsed = self.parse(script=script)
        action_parser = self.get_action_parser(script=script, action=parsed["action"])()
        action_parser.set_schema(schema_source=self.schema_source, schema_destination=self.schema_destination)
        return action_parser.transform(df=df, **parsed)

    def transform_all(self, *, df: pd.DataFrame) -> pd.DataFrame:
        """Return a transformed dataframe after processing all scripts.

        Parameters:
          df: A Pandas (Modin) dataframe.

        Returns:
          Transformed dataframe.
        """
        for script in self.get_all():
            df = self.transform(df=df, script=script)
        return df

    ###################################################################################################
    ### ACTION SUPPORT UTILITIES
    ###################################################################################################

    def set_schema(
        self, *, schema_source: SchemaDefinition = None, schema_destination: SchemaDefinition = None
    ) -> None:
        """Set SchemaDefinitions.

        Parameters:
          schema_source: A [SchemaDefinition](schema.md) for access to source schema definitions and operations.
          schema_destination: A [SchemaDefinition](schema.md) for access to destination schema definitions and operations.
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
        self, *, script: str, action: BaseSchemaAction | BaseMorphAction | BaseCategoryAction = None
    ) -> ActionParser | MorphParser | CategoryParser:
        """Return the ACTION parser for a script.

        Parameters:
          script: A string term conforming to the script structure for a specific action.
          action: The action model type conforming to the requirements for a script.

        Raises:
          ValueError: If the script can't be parsed.

        Returns:
          Parser for Action type, and used in [TransformDefinition](transform.md) and [CrosswalkDefinition](crosswalk.md).
        """
        if not action:
            action = self.get_action(script=script)
        # Test for each of BaseSchemaAction | BaseMorphAction | BaseCategoryAction
        if isinstance(action, BaseSchemaAction):
            return ActionParser
        if isinstance(action, BaseMorphAction):
            return MorphParser
        if isinstance(action, BaseCategoryAction):
            return CategoryParser
        # Action unknown
        raise ValueError(f"Script cannot be parsed ({script}).")

    def reconcile_crosswalk(self, *, fields: FieldModel | list[FieldModel], remove: bool = False) -> None:
        if fields is None:
            return
        if not isinstance(fields, list):
            fields = [fields]
        for f in fields:
            if remove:
                self.uncrossed = self.uncrossed ^ {f.uuid}
            else:
                self.uncrossed = self.uncrossed - {f.uuid}
