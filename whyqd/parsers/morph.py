# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Type, TYPE_CHECKING

from whyqd.parsers.script import SchemaPairParser

if TYPE_CHECKING:
    import pandas as pd
    from whyqd.models import MorphActionModel, FieldModel
    from whyqd.crosswalk.base import BaseMorphAction


class MorphParser(SchemaPairParser):
    """Parsing functions for morph implementations of action scripts.

    Can process and validate any morphs script. Scripts must be 'flat' and are of the form:

        "ACTION > [fields] < [rows]"

    Where:

    * the presence and order of the arrays is set by ACTION `structure`,
    * `fields` are indicated by `>`, and
    * `rows` are indicated by `<`.
    """

    ###################################################################################################
    ### PARSE TRANSFORM SCRIPT
    ###################################################################################################

    def parse(
        self,
        *,
        script: str,
        action: BaseMorphAction,
    ) -> dict[str, MorphActionModel | list[FieldModel] | list[int] | str]:
        """Generate the parsed dictionary of an initialised action script.

        Parameters
        ----------
        script: str
            An action script.
        action: BaseSchemaAction

        Raises
        ------
        ValueError for any parsing errors.

        Returns
        -------
        dict
            Parsed dictionary of an initialised action script. Of the form::
        """
        source, destination, rows, source_param, destination_param = None, None, None, None, None
        # Parse source terms
        root = self.parser.get_split_terms(script=script, by="<")
        if len(root) == 2:
            # Parsing "> 'param'::[terms]" - this is an attribute some morphs can request
            optional = self.parser.get_split_terms(script=root[1], by="::")
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
        root = self.parser.get_split_terms(script=root[0], by=">")
        if len(root) == 2:
            # Parsing "> 'param'::[fields]" - this is a term some morphs can request
            optional = self.parser.get_split_terms(script=root[1], by="::")
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

    ###################################################################################################
    ### IMPLEMENT VALIDATED SCRIPT
    ###################################################################################################

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
        """Transform a dataframe according to a morph script.

        .. warning:: Morphs can change the table columns, effecting referencing. This will be captured into the
            `DataSourceModel` and will effect Schema ACTION ColumnModel references. User beware.

        Parameters
        ----------
        action: MorphActionModel
        source: list of FieldModel or a FieldModel
            List of source fields for the action, default None.
        destination: list of FieldModel
            List of destination fields for the action, default None.
        rows: list of int, default None.
        source_param: str
            Additional parameters for a specific action, default None.
        destination_param: str
            Additional parameters for a specific action, default None.

        Returns
        -------
        Dataframe
            Containing the implementation of all transformations
        """
        return action.transform(
            df=df,
            source=source,
            destination=destination,
            rows=rows,
            source_param=source_param,
            destination_param=destination_param,
        )

    ###################################################################################################
    ### SUPPORT UTILITIES
    ###################################################################################################

    def get_hexed_script(self, *, script: str) -> str:
        # Changes fields to uuid hexes
        all_fields = [field for s in self.schemas for field in s.get.fields]
        script = self.parser.get_hexed_script(script=script, fields=all_fields)
        return ",".join([s.strip() for s in script.split(",") if s.strip()])

    def get_morph_struts(self, *, term: str) -> list[str]:
        terms = list(self.parser.generate_contents(text=term))
        if not terms:
            # It wasn't a list
            return [term]
        if len(terms) != 1:
            raise ValueError(f"Morph actions must not be nested. ({term}).")
        return self.parser.get_split_terms(script=terms[0][1], by=",", maxsplit=-1)
