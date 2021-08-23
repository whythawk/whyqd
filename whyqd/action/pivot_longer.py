from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING
import pandas as pd

from whyqd.base import BaseMorphAction

if TYPE_CHECKING:
    from ..models import ColumnModel


class Action(BaseMorphAction):
    """Pivot a list of columns to create a new long table format.

    Script::

        "PIVOT_LONGER > ['source_column', 'source_column', etc.]"

    Will generate two new columns:

    * PIVOT_LONGER_names_idx_<column.index>: containing the original column names, as appropriate,
    * PIVOT_LONGER_values_idx_<column.index>: containing the original values on those columns.
    """

    def __init__(self):
        self.name = "PIVOT_LONGER"
        self.title = "Pivot longer"
        self.description = "Transform a DataFrame from wide to long format."
        self.structure = ["columns"]

    def transform(self, df: pd.DataFrame, columns: List[ColumnModel], rows: Optional[None] = None) -> pd.DataFrame:
        """
        Pivot a list of columns to create a new long table format.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: List of ColumnModel
            List of column names to be pivoted into long format.
        rows: None
            Ignored for this ACTION.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        columns = [c.name for c in columns]
        id_columns = list(set(df.columns.values.tolist()).difference(set(columns)))
        hx = self._generate_hex()
        var_name, value_name = f"{self.name}_names_{hx}", f"{self.name}_values_{hx}"
        # https://pandas.pydata.org/docs/reference/api/pandas.melt.html
        df = pd.melt(df, id_vars=id_columns, value_vars=columns, var_name=var_name, value_name=value_name)
        return self._column_renames_to_index(df, [var_name, value_name], hx)
