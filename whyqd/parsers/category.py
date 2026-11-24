# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Type, TYPE_CHECKING

from whyqd.parsers.script import SchemaPairParser
from whyqd.models import CategoryModel

if TYPE_CHECKING:
    import pandas as pd
    from whyqd.models import FieldModel, CategoryActionModel
    from whyqd.crosswalk.base import BaseCategoryAction


class CategoryParser(SchemaPairParser):
    """The parser of a category action's script, `CATEGORISE` or `PIVOT_CATEGORIES`, each list flat:

        "CATEGORISE > 'destination'::'term' < 'source'::['source term', ...]"
        "CATEGORISE > 'destination'::True < 'source'"
        "PIVOT_CATEGORIES > 'destination' < 'source'::[row, ...]"

    A `CATEGORISE` assigns the source field's listed terms, or with a boolean term any value of its type, to one term
    of the destination field; each term is found in its own schema's field, which must hold categories.
    """

    def parse(
        self,
        *,
        script: str,
        action: BaseCategoryAction,
    ) -> dict[str, CategoryActionModel | FieldModel | CategoryModel | list[CategoryModel]]:
        """A category script's action, fields, and terms, each found in its schema.

        Returns:
          `{"action", "destination", "category", "source", "assigned", "unassigned"}`: the destination field and its
          term, the source field, and the source terms assigned and those left.

        Raises:
          ValueError: If a field or term is not in its schema, or a source field the action needs to hold categories
            holds none.
        """
        if not self.schema_source or not self.schema_destination:
            raise ValueError("Schema for both source and destination has not been provided.")
        script = self.hexed_by_part(script=script)
        parsed = action.parse(script=script)
        destination, category, source, assigned, unassigned = None, None, None, None, None
        # Get source and source category terms
        source = self.parser.get_literal(text=parsed["source"])
        source = self.get_category_field(term=source, is_source=True)
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
            if category is None:
                terms = "`, `".join(str(c.name) for c in destination.constraints.category)
                raise ValueError(
                    f"`{parsed_category}` is not a term of destination field `{destination.name}`, whose terms are "
                    f"`{terms}`. Name one of them. [whyqd:category-unknown]"
                )
        return {
            "action": action,
            "destination": destination,
            "category": category,
            "source": source,
            "assigned": assigned,
            "unassigned": unassigned,
        }

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
        """The table with the category action run on it.

        Parameters:
          df: The table.
          action: The category action to run.
          destination: The field it writes.
          source: The field it reads.
          category: The destination's term it assigns.
          assigned: The source's terms assigned to it.
        """
        return action.transform(df=df, destination=destination, source=source, category=category, assigned=assigned)

    def get_schema_field_category(
        self, *, field: FieldModel, term: str, is_source: bool = True
    ) -> CategoryModel | None:
        """A field's term, by name or hex; where the field has none of that name, the term of that name from any
        field of its own schema, then of the other, mapped back to the field's own.

        Parameters:
          field: The field whose term is wanted.
          term: The term's name or hex.
          is_source: Whether the field is in the source schema, else the destination.
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

    def get_category_field(self, *, term: str, is_source: bool = True) -> FieldModel:
        """The field a category term names, from its own schema, since its terms must come from that field even where
        both schemas have a field of the name.

        Parameters:
          term: The field's name or hex.
          is_source: Whether to find it in the source schema, else the destination.

        Raises:
          ValueError: If its schema has no such field.
        """
        schema = self.schema_source if is_source else self.schema_destination
        field = schema.fields.get(name=term)
        if not field:
            s = "destination"
            if is_source:
                s = "source"
            raise ValueError(f"Field name is not recognised from the {s} schema fields ({term}).")
        return field

    def hexed_by_part(self, *, script: str) -> str:
        """The script with each part's names as hexes, as `ScriptParser.get_hexed_script` gives them: the destination
        field and its categories from the destination schema, the source field and its categories from the source."""
        d, s, p = self.parser.DESTINATION, self.parser.SOURCE, self.parser.PARAMETER
        root_split = self.parser.get_split_terms(script=script, by=d, maxsplit=1)
        # ['ACTION', "DESTINATION < SOURCE"] => ["DESTINATION", "SOURCE"]
        hexing_script = self.parser.get_split_terms(script=root_split[-1], by=s, maxsplit=1)
        # ["DESTINATION", "SOURCE"] => ["DESTINATION_FIELD", "DESTINATION_CATEGORY"],
        #   ["SOURCE_FIELD", "SOURCE_CATEGORIES"]
        if not len(hexing_script) == 2:
            raise ValueError(f'Script is not well formed: "{script}"')
        source_script = self.parser.get_split_terms(script=hexing_script[1], by=p, maxsplit=1)
        hexing_script = self.parser.get_split_terms(script=hexing_script[0], by=p, maxsplit=1)

        def field_name(term: str) -> str:
            return term.strip()[1:-1]

        def hexing_categories(field: FieldModel | None) -> list:
            return field.constraints.category if field and field.constraints and field.constraints.category else []

        destination_field = self.schema_destination.fields.get(name=field_name(hexing_script[0]))
        if not destination_field:
            raise ValueError(f'Destination field not found: "{script}"')
        hexing_terms = [[destination_field]]
        if len(hexing_script) == 2:
            hexing_terms.append(hexing_categories(destination_field))
        hexing_script.extend(source_script)
        source_field = self.schema_source.fields.get(name=field_name(source_script[0]))
        if not source_field:
            raise ValueError(f'Source field not found: "{script}"')
        hexing_terms.extend([[source_field], hexing_categories(source_field)])
        hexed = []
        for x, f in zip(hexing_script, hexing_terms, strict=False):
            hexed.append(self.parser.get_hexed_script(script=x, fields=f))
        if len(hexed) == 3:
            return f"{root_split[0]} {d} {hexed[0]} {s} {hexed[1]}{p}{hexed[2]}"
        return f"{root_split[0]} {d} {hexed[0]}{p}{hexed[1]} {s} {hexed[2]}{p}{hexed[3]}"

    def get_assigned_uniques(self, *, text: str) -> list[str]:
        """The terms of a flat bracketed list, each as its literal.

        Raises:
          ValueError: If the list is nested.
        """
        terms = list(self.parser.generate_contents(text=text))
        if len(terms) != 1:
            raise ValueError(f"Category assignment actions must not be nested. ({text}).")
        return [
            self.parser.get_literal(text=t)
            for t in self.parser.get_split_terms(script=terms[0][1], by=",", maxsplit=-1)
        ]
