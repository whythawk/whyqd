from __future__ import annotations

# import pandas as pd
import modin.pandas as pd
import numpy as np
from typing import List, Union, TYPE_CHECKING

from whyqd.base import BaseSchemaAction

if TYPE_CHECKING:
    from ..models import ColumnModel, ModifierModel, FieldModel


class Action(BaseSchemaAction):
    """
    Create a new field by iterating over a list of fields and picking the newest value in the list.

    Script::

        "ORDER_NEW > 'destination_field' < ['source_column' + 'source_column_date', 'source_column' + 'source_column_date', etc.]"

    Where `+` links two columns together, explicitly declaring that the date in `source_column_date` is used to
    assign the order to the values in `source_column`. Unlike the ORDER ACTION, ORDER_NEW takes its ordering from
    this date assignment.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "ORDER_NEW"
        self.title = "Order by newest"
        self.description = "Use sparse data from a list of fields to populate a new field order by most recent value. Field-pairs required, with the first containing the values, and the second the dates for comparison, linked by a '+' modifier (e.g. A+dA, B+dB, C+dC, values with the most recent associated date will have precedence over other values)."
        self.structure = ["field", "modifier", "field"]

    @property
    def modifiers(self) -> List[ModifierModel]:
        """
        Describes the modifiers for order by newest.

        Returns
        -------
        List of ModifierModel
            ModifierModel representation of the modifiers.
        """
        return [{"name": "+", "title": "Links"}]

    def transform(
        self,
        df: pd.DataFrame,
        destination: Union[FieldModel, ColumnModel],
        source: List[Union[ColumnModel, ModifierModel]],
    ) -> pd.DataFrame:
        """Create a new field by iterating over a list of fields and picking the newest value in the list.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        destination: FieldModel or ColumnModel, default None
            Destination column for the result of the Action.
        source: list of ColumnModel and / or ModifierModel
            List of source columns and modifiers for the action.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        base_date = None
        # Requires sets of 3 terms: field, +, date_field
        term_set = len(self.structure)
        for data, modifier, date in self.core.chunks(source, term_set):
            if modifier.name != "+":
                raise ValueError(f"Field `{source}` has invalid ORDER_BY_NEW script. Please review.")
            if not base_date:
                # Start the comparison on the next round
                df.rename(index=str, columns={data.name: destination.name}, inplace=True)
                base_date = date.name
                if data.name == date.name:
                    # Just comparing date columns
                    base_date = destination.name
                df[base_date] = df[base_date].apply(self.wrangle.parse_dates_coerced)
                continue
            # np.where date is <> base_date and don't replace value with null
            # logic: if test_date not null & base_date <> test_date
            # False if (test_date == nan) | (base_date == nan) | base_date >< test_date
            # Therefore we need to test again for the alternatives
            df[date.name] = df[date.name].apply(self.wrangle.parse_dates_coerced)
            df[destination.name] = np.where(
                df[date.name].isnull() | (df[base_date] > df[date.name]),
                np.where(df[destination.name].notnull(), df[destination.name], df[data.name]),
                np.where(df[data.name].notnull(), df[data.name], df[destination.name]),
            )
            if base_date != destination.name:
                df[base_date] = np.where(
                    df[date.name].isnull() | (df[base_date] > df[date.name]),
                    np.where(df[base_date].notnull(), df[base_date], df[date.name]),
                    np.where(df[date.name].notnull(), df[date.name], df[base_date]),
                )
        return df
