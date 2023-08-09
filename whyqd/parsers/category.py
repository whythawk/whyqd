from __future__ import annotations
from typing import Type, TYPE_CHECKING
import modin.pandas as pd

from whyqd.parsers import CoreParser, ScriptParser
from whyqd.models import CategoryModel

if TYPE_CHECKING:
    from whyqd.models import FieldModel, CategoryActionModel
    from whyqd.core import SchemaDefinition
    from whyqd.crosswalk.base import BaseCategoryAction


class CategoryParser:
    """Parsing functions for category implementations of action scripts. These are support actions which must be run
    before `CATEGORISE`.

    This is a hybrid function:

    * *Get* a list of unique values from a source column, if categorising by unique. This step isn't necessary for
      boolean assignment,
    * `ASSIGN` subset of unique values (or all booleans) to a specified `CategoryModel` in a destination `FieldModel`.

    Scripts must be 'flat' and are of the forms::

        "ASSIGN_CATEGORY_UNIQUES > FieldModel::CategoryModel < FieldModel::[CategoryModel, etc.]"
        "ASSIGN_CATEGORY_UNIQUES > FieldModel::bool < FieldModel::[CategoryModel, etc.]"
        "ASSIGN_CATEGORY_BOOLEANS > FieldModel::bool < FieldModel"

    Where:

    * `FieldModel` is the destination column and the `::` linked `CategoryModel` defines what term the source values
      are to be assigned. This is defined in the `Schema`.
    * For `ASSIGN_CATEGORY_UNIQUES` the `list` of `CategoryModel` - unique values from `FieldModel` - will be assigned
      `::CategoryModel`.
    * For `ASSIGN_CATEGORY_BOOLEANS` values from the FieldModel are treated as boolean `True` or `False`, defined by `::bool`.
    """

    def __init__(self, *, schema_source: SchemaDefinition = None, schema_destination: SchemaDefinition = None) -> None:
        """
        Parameters
        ----------
        schema_source: SchemaDefinition, optional
        schema_destination: SchemaDefinition, optional
        """
        self.core = CoreParser()
        self.parser = ScriptParser()
        self.schema_source = None
        self.schema_destination = None
        if schema_source and schema_destination:
            self.set_schema(schema_source=schema_source, schema_destination=schema_destination)

    def parse(
        self,
        *,
        script: str,
        action: BaseCategoryAction,
    ) -> dict[str, CategoryActionModel | FieldModel | CategoryModel | list[CategoryModel]]:
        """Generate the parsed dictionary of an initialised category action script.

        Parameters
        ----------
        script: str
            An action script.
        action: BaseCategoryAction

        Raises
        ------
        ValueError for any parsing errors.

        Returns
        -------
        dict
            Parsed dictionary of an initialised category action script.
        """
        # Will hex both fields and category terms ...
        if not self.schema_source or not self.schema_destination:
            raise ValueError("Schema for both source and destination has not been provided.")
        script = self.get_hexed_script(script=script)
        parsed = action.parse(script=script)
        # Validate the category script and get the required compone
        destination, category, source, assigned, unassigned = None, None, None, None, None
        # Get source and source category terms
        source = self.parser.get_literal(text=parsed["source"])
        source = self.get_schema_field(term=source, is_source=True)
        # Get category terms from the field if the action.structure requires it
        if action.structure and (not source.constraints or not source.constraints.category):
            raise ValueError(f"Source field ({source.name}) is invalid since it has no assigned category constraints.")
        if parsed.get("source_category"):
            if action.structure:
                all_uniques = source.constraints.category
                assigned = []
                failed = []
                assigned_uniques = self.get_assigned_uniques(text=parsed["source_category"])
                for c in assigned_uniques:
                    category = self.get_schema_field_category(field=source, term=c, is_source=True)
                    if category:
                        assigned.append(category)
                    elif not category and isinstance(c, bool) and len(assigned_uniques) == 1:
                        # Coercing a column to a boolean field based on presence or absence of values
                        # Can't assign more than True or False
                        # Create a temporary category
                        assigned.append(CategoryModel(**{"name": c}))
                    else:
                        failed.append(c)
                    if failed:
                        raise ValueError(f"Assigned category not found in source field categories {set(failed)}.")
                unassigned = [c for c in all_uniques if c.uuid.hex not in assigned_uniques]
            else:
                assigned = parsed["source_category"]
        # Get destination column and assigned category term
        destination = self.parser.get_literal(text=parsed["destination"])
        destination = self.schema_destination.fields.get(name=destination)
        if parsed.get("category"):
            parsed_category = self.parser.get_literal(text=parsed["category"])
            category = self.get_schema_field_category(field=destination, term=parsed_category, is_source=False)
        if not destination and category:
            raise ValueError(
                f"Destination field and category are not valid for this category action script ({parsed['destination']}, {parsed['category']})."
            )
        # Return validated terms
        return {
            "action": action,
            "destination": destination,
            "category": category,
            "source": source,
            "assigned": assigned,
            "unassigned": unassigned,
        }

    ###################################################################################################
    ### IMPLEMENT VALIDATED SCRIPT
    ###################################################################################################

    def transform(
        self,
        *,
        df: pd.DataFrame,
        action: Type[BaseCategoryAction],
        destination: FieldModel,
        source: FieldModel,
        category: CategoryModel = None,
        assigned: list[CategoryModel] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Transform a dataframe according to a categorisation script.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        action: SchemaActionModel
        destination: FieldModel
        source: list of ModifierModel, and dicts of nested transforms, default None
        assigned: list of dict
            Specific to CATEGORISE actions. Each dict has values for: Assignment ACTION, destination schema field,
            schema category, source data column, and a list of source data column category terms assigned to that
            schema category.

        Returns
        -------
        Dataframe
            Containing the implementation of all nested transformations
        """
        return action.transform(df=df, destination=destination, source=source, category=category, assigned=assigned)

    ###################################################################################################
    ### SUPPORT UTILITIES
    ###################################################################################################

    def set_schema(
        self, *, schema_source: SchemaDefinition = None, schema_destination: SchemaDefinition = None
    ) -> None:
        """Set SchemaDefinitions for the parser.

        Parameters
        ----------
        schema_source: SchemaDefinition
        schema_destination: SchemaDefinition
        """
        if not schema_source or not schema_destination:
            raise ValueError("Schema for both source and destination has not been provided.")
        self.schema_source = schema_source
        self.schema_destination = schema_destination


    def get_schema_field_category(self, *, field: FieldModel, term: str, is_source: bool = True) -> CategoryModel | None:
        """
        Recover a field category model from a string. It is possible that source and destination schema category share 
        a common name, so we need to check all possibilities.

        Parameters
        ----------
        field: FieldModel
        term: str
        is_source: bool
            Boolean True for source schema, False for destination schema

        Returns
        -------
        CategoryModel | None
        """
        if not field:
            return None
        schema = self.schema_destination
        alt_schema = self.schema_source
        if is_source:
            schema = self.schema_source
            alt_schema = self.schema_destination
        category = schema.fields.get_category(name=field.uuid.hex, category=term)
        # Disambiguation step ...
        if not category:
            # Any schema field
            for schema_field in schema.fields.get_all():
                if schema_field.constraints and schema_field.constraints.category:
                    category = schema.fields.get_category(name=schema_field.uuid.hex, category=term)
                    if category:
                        category = schema.fields.get_category(name=field.uuid.hex, category=category.name)
                        break
        if not category:
            # Any alt schema field
            for schema_field in alt_schema.fields.get_all():
                if schema_field.constraints and schema_field.constraints.category:
                    category = alt_schema.fields.get_category(name=schema_field.uuid.hex, category=term)
                    if category:
                        category = schema.fields.get_category(name=field.uuid.hex, category=category.name)
                        break
        return category

    def get_schema_field(self, *, term: str, is_source: bool = True) -> FieldModel:
        """
        Recover a field model from a string. It is possible that source and destination schema share a common name,
        so we need to check both, but the categorical terms must come from the correct field. Raise an error if we
        can't identify appropriately.

        Parameters
        ----------
        term: str
        is_source: bool
            Boolean True for source schema, False for destination schema

        Raises
        ------
        ValueError if the field term is not recognised from the appropriate schema.

        Returns
        -------
        FieldModel
        """
        schema = self.schema_destination
        alt_schema = self.schema_source
        if is_source:
            schema = self.schema_source
            alt_schema = self.schema_destination
        field = schema.fields.get(name=term)
        if not field:
            field = alt_schema.fields.get(name=term)
            field = schema.fields.get(name=field.name)
        if not field:
            s = "destination"
            if is_source:
                s = "source"
            raise ValueError(f"Field name is not recognised from the {s} schema fields ({term}).")
        return field

    def get_hexed_script(self, *, script: str) -> str:
        # Changes fields to uuid hexes
        all_fields = [field for s in [self.schema_source, self.schema_destination] for field in s.get.fields]
        all_categories = [
            category
            for f in all_fields
            if (f.constraints and f.constraints.category)
            for category in f.constraints.category
        ]
        script = self.parser.get_hexed_script(script=script, fields=all_fields + all_categories)
        return ",".join([s.strip() for s in script.split(",") if s.strip()])

    def get_assigned_uniques(self, *, text: str) -> list[str]:
        terms = list(self.parser.generate_contents(text=text))
        if len(terms) != 1:
            raise ValueError(f"Category assignment actions must not be nested. ({text}).")
        return [self.parser.get_literal(text=t) for t in self.parser.get_split_terms(script=terms[0][1], by=",")]
