from __future__ import annotations
from typing import Union, Optional, TYPE_CHECKING
import pandas as pd

from whyqd.base import BaseFilterAction

if TYPE_CHECKING:
    from ..models import FieldModel, ColumnModel


class Action(BaseFilterAction):
    """Filter a table for the latest row in a specified filter column, and within an optional set of groups.

    Script is::

        "FILTER_LATEST > 'filter_column' < 'source_column'"

    Where 'source_column' defines the groups from which to extract the latest row.
    """

    def __init__(self) -> None:
        self.name = "FILTER_LATEST"
        self.title = "Filter latest"
        self.description = (
            "Filter a table for the latest row in a specified filter column, and within an optional set of groups."
        )
        self.structure = ["column"]

    def transform(
        self,
        df: pd.DataFrame,
        filter_column: Union[FieldModel, ColumnModel],
        date_term: Optional[None] = None,
        column: Optional[Union[FieldModel, ColumnModel]] = None,
    ) -> pd.DataFrame:
        """Filter a table for the latest row in a specified filter column, and within an optional set of groups.

        Script is::

            "FILTER_LATEST > 'filter_column' < 'source_column'"

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        filter_column: FieldModel or ColumnModel
            A date-field column to use to filter the table. Column values will be coerced to date-type.
        column: FieldModel or ColumnModel, default None
            A column which defines the groups from which to extract the latest row.
        date_term: None
            Ignored for this transform.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        # Maintaining the original table column format. For better or worse.
        from whyqd.parsers import WranglingScript

        wrangle = WranglingScript()
        df_filter = df.copy()
        df_filter[filter_column.name] = df_filter[filter_column.name].apply(lambda x: wrangle.parse_dates(x))
        df_filter.sort_values(by=[filter_column.name], ascending=False, inplace=True)
        # Clever time-saving
        # https://stackoverflow.com/a/20069379/295606
        # https://stackoverflow.com/a/20067665/295606 & https://stackoverflow.com/a/36073837/295606
        rows = df_filter.groupby(column.name).head(1).index.values
        return df.loc[rows]
