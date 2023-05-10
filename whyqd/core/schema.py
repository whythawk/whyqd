from __future__ import annotations
from pathlib import Path

from whyqd.models import FieldModel, SchemaModel, DataSourceModel
from whyqd.crud.field import CRUDField
from whyqd.core.base import BaseDefinition


class SchemaDefinition(BaseDefinition):
    """Create and manage a metadata schema.

    !!! tip "Strategy"
        Guidance on how to use this definition is in the strategies section on
        [Schema Strategies](/strategies/schema).

    Parameters:
      source: A path to a json file containing a saved schema, or a dictionary conforming to the SchemaModel.

    Example:
      Create a new `SchemaDefinition` as follows:

      ```python
      import whyqd as qd

      schema: qd.models.SchemaModel = {
          "name": "urban_population",
          "title": "Urban population",
          "description": "Urban population refers to people living in urban areas as defined by national statistical offices.",
      }
      schema_destination = qd.SchemaDefinition()
      schema_destination.set(schema=schema)
      ```
    """

    def __init__(self, *, source: Path | str | SchemaModel | None = None) -> None:
        super().__init__(model_name="schema")
        self.crud = CRUDField(FieldModel)
        self.set(schema=source)

    def _refresh_model_terms(self) -> None:
        """Refreshes the list of terms and connects them to the Form Model"""
        if self.model:
            self.model.fields = self.crud.get_all()

    def _refresh_model_fields(self) -> None:
        """Refreshes the list of terms and connects them to the Field CRUD"""
        if self.model and self.model.fields:
            self.crud.reset()
            if isinstance(self.model.fields[0], dict):
                self.crud.add_multi(terms=self.model.fields)
            else:
                self.crud.add_multi(
                    terms=[f.dict(by_alias=True, exclude_defaults=True, exclude_none=True) for f in self.model.fields]
                )
        if self.model and not self.model.fields:
            self.crud.reset()

    @property
    def get(self) -> SchemaModel | None:
        """Get the schema model.

        Returns:
          Pydantic SchemaModel or None
        """
        self._refresh_model_terms()
        return self.model

    def set(self, *, schema: Path | str | SchemaModel | None = None) -> None:
        """Update or create the schema.

        Parameters:
          schema: A dictionary, or path to a dictionary or json file, conforming to the SchemaModel.
        """
        self.model = self.core.create_or_update_model(modelType=SchemaModel, source=schema, model=self.model)
        self._refresh_model_fields()

    @property
    def fields(self) -> CRUDField:
        """Returns the active crud model for all Field operations. See [Field CRUD](/api/field) for API.

        Returns:
          For all Field CRUD behaviours.
        """
        return self.crud

    #########################################################################################
    # DERIVE SCHEMA FROM TABULAR DATA
    #########################################################################################

    def derive_model(self, *, data: DataSourceModel | dict) -> None:
        """Derive a schema model from a data source model.

        Arguments:
            data: A model defining a single data source
        """
        if isinstance(data, dict):
            data = DataSourceModel(**data)
        if not self.model:
            self.set()
        for dc in data.columns:
            field = dc.dict(exclude={"uuid"}, by_alias=True)
            field["title"] = field["name"]
            self.fields.add(term=field)
        self._refresh_model_terms()
        if data.index:
            self.model.index = data.index
