from __future__ import annotations
from pathlib import Path

from whyqd.models import SchemaModel, CrosswalkModel
from whyqd.core import SchemaDefinition
from whyqd.crud import CRUDAction
from whyqd.core.base import BaseDefinition


class CrosswalkDefinition(BaseDefinition):
    """Create and manage a method to perform a schema to schema crosswalk.

    !!! tip "Strategy"
        Guidance on how to use this definition is in the strategies section on
        [Crosswalk Strategies](/strategies/crosswalk).

    Parameters:
      crosswalk: A dictionary conforming to the CrosswalkModel, or a path to a saved definition.
      schema_source: Path to a json file containing a saved schema, or a dictionary conforming to one, or a definition.
      schema_destination: Path to a json file containing a saved schema, or a dictionary conforming to one, or a definition.

    Example:
      Create a new `CrosswalkDefinition` as follows:

      ```python
      import whyqd as qd

      crosswalk = qd.CrosswalkDefinition()
      crosswalk.set(schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION)
      ```
    """

    def __init__(
        self,
        *,
        crosswalk: CrosswalkModel | dict | Path | str | None = None,
        schema_source: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
        schema_destination: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
    ) -> None:
        super().__init__(model_name="crosswalk")
        self.crud = CRUDAction()
        self.schema_source = SchemaDefinition()
        self.schema_destination = SchemaDefinition()
        self.set(crosswalk=crosswalk, schema_source=schema_source, schema_destination=schema_destination)

    def _refresh_model_terms(self) -> None:
        """Refreshes the list of terms and connects them to the Form Model"""
        if self.model:
            self.model.actions = self.crud.get_all()

    def _refresh_model_fields(self) -> None:
        """Refreshes the list of terms and connects them to the Field CRUD"""
        if self.model and self.model.actions:
            self.crud.add_multi(terms=self.model.actions)
        if self.model and not self.model.actions:
            self.crud.reset()

    @property
    def get(self) -> CrosswalkModel | None:
        """Get the crosswalk model.

        Returns:
          A Pydantic CrosswalkModel or None
        """
        self._refresh_model_terms()
        return self.model

    def set(
        self,
        *,
        crosswalk: CrosswalkModel | dict | Path | str | None = None,
        schema_source: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
        schema_destination: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
    ) -> None:
        """Update or create the crosswalk.

        Parameters:
          crosswalk: A dictionary conforming to the CrosswalkModel, or a path to a saved definition.
          schema_source: Path to a json file containing a saved schema, or a dictionary conforming to one, or a definition.
          schema_destination: Path to a json file containing a saved schema, or a dictionary conforming to one, or a definition.
        """
        self.model = self.core.create_or_update_model(modelType=CrosswalkModel, source=crosswalk, model=self.model)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self.model.schemaSource and not schema_source:
            self.schema_source.set(schema=self.model.schemaSource)
        elif schema_source:
            if isinstance(schema_source, SchemaDefinition):
                self.schema_source = schema_source
            else:
                self.schema_source.set(schema=schema_source)
            self.model.schemaSource = self.schema_source.get
        if self.model.schemaDestination and not schema_destination:
            self.schema_destination.set(schema=self.model.schemaDestination)
        elif schema_destination:
            if isinstance(schema_destination, SchemaDefinition):
                self.schema_destination = schema_destination
            else:
                self.schema_destination.set(schema=schema_destination)
            self.model.schemaDestination = self.schema_destination.get
        if self.model.schemaSource and self.model.schemaDestination:
            self.crud.set_schema(schema_source=self.schema_source, schema_destination=self.schema_destination)
            self._refresh_model_fields()

    #########################################################################################
    # MANAGE ACTION SCRIPTS
    #########################################################################################

    @property
    def actions(self) -> CRUDAction:
        """Returns the active crud model for all Action operations. See [Action CRUD](/api/action) for API.

        Returns:
          For all Action CRUD behaviours.
        """
        if not self.model.schemaSource or not self.model.schemaDestination:
            raise ValueError("First set source and destination schemas before performing defining a crosswalk.")
        return self.crud

    #########################################################################################
    # VALIDATION UTILITIES
    #########################################################################################

    def validate(self) -> bool:
        """Validate that all required fields are returned from the crosswalk.

        Raises:
          ValueError: If required destination fields are not present in the crosswalk.

        Returns:
          A boolean `True` if successful.
        """
        required = self.crud.validate(required=True)
        if required:
            raise ValueError(
                f"Validation error. Required destination fields are not present in the crosswalk: {required}"
            )
