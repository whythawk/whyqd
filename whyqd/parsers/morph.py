# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Type, TYPE_CHECKING

from whyqd.parsers.script import SchemaPairParser

if TYPE_CHECKING:
    import pandas as pd
    from whyqd.models import MorphActionModel, FieldModel
    from whyqd.crosswalk.base import BaseMorphAction


class MorphParser(SchemaPairParser):
    """The parser of a morph's script, `ACTION > [fields] < [rows]`, each list flat, never nested.

    Which lists a morph takes, and in what order, is its `structure`; either may open with a `'parameter'::`.
    """

    def parse(
        self,
        *,
        script: str,
        action: BaseMorphAction,
    ) -> dict[str, MorphActionModel | list[FieldModel] | list[int] | str]:
        """A morph script's action, fields, rows, and parameters, checked against the morph's structure.

        Returns:
          `{"action", "destination", "source", "rows", "source_param", "destination_param"}`, each `None` where the
          script has none.

        Raises:
          ValueError: If a list is nested, a field is in neither schema, or a list the structure needs is missing.
        """
        source, destination, rows, source_param, destination_param = None, None, None, None, None
        # Parse source terms
        root = self.parser.get_split_terms(script=script, by=self.parser.SOURCE)
        if len(root) == 2:
            # Parsing "> 'param'::[terms]" - this is an attribute some morphs can request
            optional = self.parser.get_split_terms(script=root[1], by=self.parser.PARAMETER)
            if len(optional) == 2:
                # Must be a string
                source_param = self.parser.get_literal(text=optional[0])
                root[1] = optional[1]
            if "rows" in action.structure:
                # Parsing "< [rows]"
                # Must all be of type `int`
                rows = [int(i) for i in self.get_morph_struts(term=root[1])]
            if "fields" in action.structure:
                # Parsing "< [fields]"
                # Can be either of `schema_source` or `schema_destination`
                source = self.get_morph_struts(term=root[1])
                source = [self.parser.get_literal(text=f) for f in source]
                source = [self.parser.get_schema_field(term=f, schema=self.schemas) for f in source]
        # Parse destination terms
        root = self.parser.get_split_terms(script=root[0], by=self.parser.DESTINATION)
        if len(root) == 2:
            # Parsing "> 'param'::[fields]" - this is a term some morphs can request
            optional = self.parser.get_split_terms(script=root[1], by=self.parser.PARAMETER)
            if len(optional) == 2:
                # Must be a string
                destination_param = self.parser.get_literal(text=optional[0])
                root[1] = optional[1]
            # Can be either of `schema_source` or `schema_destination`
            destination = self.get_morph_struts(term=root[1])
            destination = [self.parser.get_literal(text=f) for f in destination]
            destination = [self.parser.get_schema_field(term=f, schema=self.schemas) for f in destination]
        # Validate structure
        if (source or destination) and "fields" not in action.structure:
            raise ValueError(f"Script error for {action.name} Morph. Fields are not a valid input.")
        if not (source or destination) and "fields" in action.structure:
            raise ValueError(f"Script error for {action.name} Morph. No valid input fields provided.")
        # The rows are checked against the data source's row count where the crosswalk meets it, in the transform
        if rows:
            if "rows" not in action.structure:
                raise ValueError(f"Script error for {action.name} Morph. Rows are not a valid input.")
        else:
            if "rows" in action.structure:
                raise ValueError(f"Script error for {action.name} Morph. No valid input rows provided.")
        return {
            "action": action,
            "destination": destination,
            "source": source,
            "rows": rows,
            "source_param": source_param,
            "destination_param": destination_param,
        }

    def transform(
        self,
        *,
        df: pd.DataFrame,
        action: Type[BaseMorphAction],
        source: list[FieldModel] | FieldModel | None = None,
        destination: list[FieldModel] | FieldModel | None = None,
        rows: list[int] | None = None,
        source_param: str | None = None,
        destination_param: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """The table with the morph run on it, which may add, remove, or reshape its columns and rows.

        Parameters:
          df: The table.
          action: The morph to run.
          source: The fields it reads.
          destination: The fields it writes.
          rows: The rows it names, by row key.
          source_param: The parameter before its source list.
          destination_param: The parameter before its destination list.
        """
        return action.transform(
            df=df,
            source=source,
            destination=destination,
            rows=rows,
            source_param=source_param,
            destination_param=destination_param,
        )

    def get_morph_struts(self, *, term: str) -> list[str]:
        """A bracketed list's terms, or a lone term as a list of one.

        Raises:
          ValueError: If the list is nested.
        """
        terms = list(self.parser.generate_contents(text=term))
        if not terms:
            # It wasn't a list
            return [term]
        if len(terms) != 1:
            raise ValueError(f"Morph actions must not be nested. ({term}).")
        return self.parser.get_split_terms(script=terms[0][1], by=",", maxsplit=-1)
