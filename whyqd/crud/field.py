from __future__ import annotations
from uuid import UUID
import modin.pandas as pd

from whyqd.crud.base import CRUDBase
from whyqd.models import FieldModel, ConstraintsModel, CategoryModel
from whyqd.dtypes import FieldType


class CRUDField(CRUDBase[FieldModel]):
    """Create, Read, Update and Delete Field Models. Usually instantiated as part of a
    [SchemaDefinition](schema.md) and accessed as `.fields`.

    [Base CRUD operations](basecrud.md) are common for both `CRUDField` and `CRUDAction`.

    Example:
      ```python
      import whyqd as qd

      schema: qd.models.SchemaModel = {
          "name": "urban_population",
          "title": "Urban population",
          "description": "Urban population refers to people living in urban areas as defined by national statistical offices.",
      }
      fields: list[qd.models.FieldModel] = [
          {
              "name": "indicator_code",
              "title": "Indicator Code",
              "type": "string",
              "description": "World Bank code reference for Indicator Name.",
              "constraints": {"required": True},
          },
          {
              "name": "country_name",
              "title": "Country Name",
              "type": "string",
              "description": "Official country names.",
              "constraints": {"required": True},
          },
          {
              "name": "country_code",
              "title": "Country Code",
              "type": "string",
              "description": "UN ISO 3-letter country code.",
              "constraints": {"required": True},
          },
          {
              "name": "indicator_name",
              "title": "Indicator Name",
              "type": "string",
              "description": "Indicator described in the data series.",
              "constraints": {"required": True},
          },
          {
              "name": "year",
              "title": "Year",
              "type": "year",
              "description": "Year of release.",
              "constraints": {"required": True},
          },
          {
              "name": "values",
              "title": "Values",
              "type": "number",
              "description": "Value for the Year and Indicator Name.",
              "constraints": {"required": True},
          },
      ]
      schema_destination = qd.SchemaDefinition()
      schema_destination.set(schema=schema)
      schema_destination.fields.add_multi(terms=fields)
      ```

    Parameters:
      model: The Pydantic model on which CRUD operations are based.
    """

    def get_required(self) -> list[FieldModel]:
        """Return a list of all required fields.

        Returns:
          A list of required fields.
        """
        return [f for f in self.multi if f.constraints and f.constraints.required]

    def get_constraints(self, *, name: str | UUID) -> ConstraintsModel | None:
        """Get the constraint parameters for a specific field defined in this schema, called by a unique
        `name` already in the schema.

        Parameters:
          name: Specific name or reference UUID for a field already in the Schema.

        Returns:
          A ConstraintsModel or None.
        """
        field = self.get(name=name)
        if not field:
            raise ValueError(f"FieldModel {name} does not exist in the schema.")
        return field.constraints

    def set_constraints(self, *, name: str | UUID, constraints: ConstraintsModel | None) -> None:
        """Set the constraint parameters for a specific field to define this schema, called by a unique
        `name` already in the schema.

        Parameters:
          name: Specific name or reference UUID for a field already in the Schema
          constraints: A dictionary conforming to the ConstraintsModel, or None. If None, then constraints are deleted.
        """
        old_constraints = self.get_constraints(name=name)
        if not constraints:
            old_constraints = None
        else:
            new_constraints = ConstraintsModel(**constraints)
            if old_constraints:
                old_constraints = old_constraints.copy(update=new_constraints.model_dump(exclude_unset=True))
            else:
                old_constraints = new_constraints
        self.get(name=name).constraints = old_constraints

    def set_categories(
        self,
        *,
        name: str,
        terms: pd.DataFrame | pd.Series | list[str] | None = None,
        as_bool: bool = False,
        has_array: bool = False,
    ) -> None:
        """Derive unique category constraints from a data column for a specific field, called by a unique `name`
        already in the schema.

        Parameters:
          name:  Specific name for a field already in the Schema
          terms:  Data provided as a table or column containing string terms, as arrays or individual terms
          as_bool:  Set the category terms as booleans, `True` and `False`
          has_array:  Set `True` if data terms are arrays, or the Field is of type `FieldType.ARRAY`
        """
        field = self.get(name=name)
        if not field.constraints:
            field.constraints = ConstraintsModel()
        if as_bool:
            field.constraints.category = [CategoryModel(**{"name": term}) for term in [True, False]]
        else:
            if not isinstance(terms, list):
                terms = terms[name].unique()
            if has_array or field.dtype == FieldType.ARRAY:
                # Multiple categories in a row
                field.dtype = FieldType.ARRAY
                # This will only work where it's a 2D array, which it 'should' be
                # https://stackoverflow.com/a/38900498/295606
                terms = [
                    x for inner in [[item] if not isinstance(item, list) else item for item in terms] for x in inner
                ]
            field.constraints.category = [
                CategoryModel(**{"name": term})
                for term in terms
                if not (term is pd.NA or pd.isnull(term) or term is None)
            ]

    def get_category(self, *, name: str, category: bool | str) -> CategoryModel | None:
        """Get a specific field from the list of fields defining this schema, called by a unique `name`.

        Parameters:
          name:  Field names must be unique, so a valid `name` in the field list will have no collisions.
          category:  Category name for a destination category term from the schema.

        Raises:
          ValueError: If `FieldModel` has not `category` in `ConstraintModel`.

        Returns:
          A list of CategoryModel, or None of none are defined.
        """
        if self.multi:
            field_categories = self.get_constraints(name=name)
            if not field_categories and isinstance(category, bool):
                # Bools have default True, False categories
                # Create them now if they don't exist
                # TODO: put this somewhere more useful, and where the user can set default is True/False
                true = CategoryModel(**{"name": True})
                false = CategoryModel(**{"name": False})
                fld = self.get(name=name)
                fld.constraints = ConstraintsModel(**{"default": true, "enum": [true, false]})
            field_categories = self.get_constraints(name=name).category
            if not field_categories:
                raise ValueError(f"Field ({name}) has no `category` constraints.")
            # https://stackoverflow.com/a/31988734/295606
            return next((f for f in field_categories if f.name == category or f.uuid.hex == category), None)
        return None
