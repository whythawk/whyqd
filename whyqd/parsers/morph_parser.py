from __future__ import annotations
from typing import Dict, List, Union, Optional, Type, TYPE_CHECKING
import pandas as pd
import numpy as np

from . import CoreScript, ParserScript, WranglingScript

if TYPE_CHECKING:
    from ..models import ColumnModel, MorphActionModel, DataSourceModel
    from ..schema import Schema
    from ..base import BaseMorphAction


class MorphScript:
    """Parsing functions for morph implementations of action scripts.

    Can process and validate any morphs script. Scripts must be 'flat' and are of the form:

        "ACTION > [columns] < [rows]"

    Where:

    * the presence and order of the arrays is set by ACTION `structure`,
    * `columns` are indicated by `>`, and
    * `rows` are indicated by `<`.

    Parameters
    ----------
    df: DataFrame
    data: DataSourceModel
    schema: Schema
    """

    def __init__(self, data: DataSourceModel, schema: Schema, df: Optional[pd.DataFrame] = None) -> None:
        self.core = CoreScript()
        self.parser = ParserScript()
        self.wrangle = WranglingScript()
        self.data = data
        if not isinstance(df, pd.DataFrame):
            df = self.wrangle.get_dataframe_from_datasource(data=data)
        self.df = df
        self.source_columns = data.columns
        self.row_indices = list(self.df.index)
        self.schema = schema

    ###################################################################################################
    ### PARSE TRANSFORM SCRIPT
    ###################################################################################################

    def parse(
        self, script: str
    ) -> Dict[str, Union[MorphActionModel, Optional[List[ColumnModel]], Optional[List[int]]]]:
        """Generate the parsed dictionary of an initialised morph action script.

        Parameters
        ----------
        script: str
            An action script.

        Raises
        ------
        ValueError for any parsing errors.

        Returns
        -------
        dict
            Parsed dictionary of an initialised morph action script.
        """
        first_action = self.parser.get_anchor_action(script)
        param = None
        rename_all = first_action.name == "RENAME_ALL"
        if not rename_all:
            script = self.parser.get_normalised_script(script, self.source_columns)
        columns, rows = None, None
        root = self.parser.get_split_terms(script, "<")
        if len(root) == 2:
            # Parsing "< [rows]"
            # Must all be of type `int`
            rows = [int(i) for i in self.get_morph_struts(root[1])]
        root = self.parser.get_split_terms(root[0], ">")
        if len(root) == 2:
            # Parsing "> 'param'::[columns]" - this is a term some morphs can request
            optional = self.parser.get_split_terms(root[1], "::")
            if len(optional) == 2:
                # Must be a string
                param = self.parser.get_literal(optional[0])
            morph_terms = self.get_morph_struts(root[1])
            # These must all be of ColumnModel, unless ACTION is RENAME_ALL
            columns = []
            for m in morph_terms:
                c = self.parser.get_literal(m)
                if rename_all:
                    columns.append(c)
                else:
                    c = self.parser.get_field_from_script(c, self.source_columns, self.schema)
                    columns.append(c)
            if rename_all and first_action.name == "RENAME_ALL":
                if len(columns) != len(self.source_columns):
                    raise ValueError(
                        "Can only `RENAME_ALL` if the number of new column names equals the number of existing columns."
                    )
        action = self.parser.get_action_model(root[0])
        if not action:
            raise ValueError("Morph action not found.")
        # Validate structure
        if columns and "columns" not in action.structure:
            raise ValueError(f"Script error for {action.name} Morph. Columns are not a valid input.")
        if not columns and "columns" in action.structure:
            raise ValueError(f"Script error for {action.name} Morph. No valid input columns provided.")
        if rows:
            if "rows" not in action.structure:
                raise ValueError(f"Script error for {action.name} Morph. Rows are not a valid input.")
            elif not np.in1d(rows, self.row_indices).all():
                raise ValueError("Not all row indices found in source data.")
        else:
            if "rows" in action.structure:
                raise ValueError(f"Script error for {action.name} Morph. No valid input rows provided.")
        if param:
            return {
                "action": action,
                "columns": columns,
                "rows": rows,
                "param": param,
            }
        return {
            "action": action,
            "columns": columns,
            "rows": rows,
        }

    ###################################################################################################
    ### IMPLEMENT VALIDATED SCRIPT
    ###################################################################################################

    def transform(
        self,
        action: MorphActionModel,
        columns: Optional[List[ColumnModel]] = None,
        rows: Optional[List[int]] = None,
        param: Optional[str] = None,
    ) -> pd.DataFrame:
        """Transform a dataframe according to a morph script.

        .. warning:: Morphs can change the table columns, effecting referencing. This will be captured into the
            `DataSourceModel` and will effect Schema ACTION ColumnModel references. User beware.

        Parameters
        ----------
        action: MorphActionModel
        columns: list of ColumnModel, default None
        rows: list of int, default None

        Returns
        -------
        Dataframe
            Containing the implementation of all transformations
        """
        action: Type[BaseMorphAction]
        action = self.parser.get_action_class(action)()
        if param:
            return action.transform(self.df, columns=columns, rows=rows, param=param)
        return action.transform(self.df, columns=columns, rows=rows)

    ###################################################################################################
    ### SUPPORT UTILITIES
    ###################################################################################################

    def get_morph_struts(self, text):
        terms = list(self.parser.generate_contents(text))
        if len(terms) != 1:
            raise ValueError(f"Morph actions must not be nested. ({text}).")
        return self.parser.get_split_terms(terms[0][1], ",")
