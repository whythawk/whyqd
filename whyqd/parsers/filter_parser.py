from __future__ import annotations
from typing import Dict, List, Union, Optional, Type, TYPE_CHECKING
import pandas as pd
from datetime import date

from . import CoreScript, ParserScript, WranglingScript

if TYPE_CHECKING:
    from ..models import ColumnModel, FieldModel, FilterActionModel
    from ..schema import Schema
    from ..base import BaseFilterAction


class FilterScript:
    """Parsing functions for filter implementations of action scripts.

    Can process and validate any filters script. Scripts must be 'flat' and are of the form:

        "ACTION > 'filter_column'::'date' < ['source_column', 'source_column', etc.]"

    Parameters
    ----------
    source_columns: list of ColumnModel
        Source columns upon which the script will be applied.
    schema: Schema
        Destination Schema
    """

    def __init__(self, source_columns: List[ColumnModel], schema: Schema) -> None:
        self.core = CoreScript()
        self.parser = ParserScript()
        self.wrangle = WranglingScript()
        self.source_columns = source_columns
        self.schema = schema

    ###################################################################################################
    ### PARSE TRANSFORM SCRIPT
    ###################################################################################################

    def parse(self, script: str) -> Dict[str, Union[FilterActionModel, Optional[List[ColumnModel]], Optional[date]]]:
        """Generate the parsed dictionary of an initialised filter action script.

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
            Parsed dictionary of an initialised filter action script.
        """
        script = self.parser.get_normalised_script(script, self.source_columns)
        action_model = self.parser.get_anchor_action(script)
        if not isinstance(action_model, FilterActionModel):
            raise ValueError(f"Invalid action ({action_model.name}) for this parser.")
        # Validate the filter script and get the required components
        parsed = self.parser.get_action_class(action_model)().parse(script)
        # Filter column
        filter_column = self.parser.get_literal(parsed["filter"])
        filter_column = self.parser.get_field_model(filter_column, self.source_columns)
        if not filter_column:
            raise ValueError(f"Filter column is not recognised ({parsed['filter']}).")
        # Column
        column = None
        if parsed.get("column"):
            column = self.parser.get_literal(parsed["column"])
            column = self.parser.get_field_model(column, self.source_columns)
            if not column:
                raise ValueError(f"Grouped filter column is not recognised ({parsed['column']}).")
        # Date term
        date_term = None
        if parsed.get("date"):
            date_term = self.parser.get_literal(parsed["date"])
            date_term = self.wrangle.parse_dates(date_term)
            if pd.isnull(date_term):
                raise ValueError(f"Filter date is not recognised ({parsed['date']}).")
        return {
            "action": action_model,
            "filter": filter_column,
            "date": date_term,
            "column": column,
        }

    ###################################################################################################
    ### IMPLEMENT VALIDATED SCRIPT
    ###################################################################################################

    def transform(
        self,
        df: pd.DataFrame,
        action: FilterActionModel,
        filter_column: Union[FieldModel, ColumnModel],
        column: Optional[Union[FieldModel, ColumnModel]] = None,
        date_term: Optional[date] = None,
    ) -> pd.DataFrame:
        """Perform a filter transform.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        filter_column: FieldModel or ColumnModel
            A date-field column to use to filter the table. Column values will be coerced to date-type.
        column: FieldModel or ColumnModel, default None
            A column which defines the groups from which to extract the latest row.
        date_term: date, default None
            A specific date for filtering.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        action: Type[BaseFilterAction]
        action = self.parser.get_action_class(action)()
        return action.transform(df, filter_column, column, date_term)