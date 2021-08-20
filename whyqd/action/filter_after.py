from __future__ import annotations
from typing import Union, Optional, TYPE_CHECKING
import pandas as pd

from whyqd.base import BaseFilterAction

if TYPE_CHECKING:
    from ..models import FieldModel, ColumnModel


class Action(BaseFilterAction):
    """Filter a table by a date column after to a specified date.

    Script is::

        "FILTER_BEFORE > 'filter_column'::'date'"

    Where `date` is the specific date reference, in ISO `YYYY-MM-DD` format.
    """

    def __init__(self) -> None:
        self.name = "FILTER_BEFORE"
        self.title = "Filter before"
        self.description = "Filter a table by a date column after to a specified date."
        self.structure = ["date"]

    def transform(
        self,
        df: pd.DataFrame,
        filter_column: Union[FieldModel, ColumnModel],
        date_term: str,
        column: Optional[None] = None,
    ) -> pd.DataFrame:
        """Filter a table by a date column after to a specified date.

        Script is::

            "FILTER_BEFORE > 'filter_column'::'date'"

        Where `date` is the specific date reference, in ISO `YYYY-MM-DD` format.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        filter_column: FieldModel or ColumnModel
            A date-field column to use to filter the table. Column values will be coerced to date-type.
        column: None, default None
            Columns not used in this filter.
        date_term: str
            A specific date in ISO format 'yyyy-mm-dd' for filtering.

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
        rows = df_filter[df_filter[filter_column.name] > date_term].index.values
        return df.loc[rows]
