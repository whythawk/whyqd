from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING
import pandas as pd

from whyqd.base import BaseMorphAction

if TYPE_CHECKING:
    from ..models import ColumnModel


class Action(BaseMorphAction):
    """Delete columns provided in a list.

    Script::

        "DELETE_COLUMNS > ['source_column', 'source_column', etc.]"
    """

    def __init__(self) -> None:
        self.name = "DELETE_COLUMNS"
        self.title = "Delete columns"
        self.description = "Delete columns provided in a list."
        self.structure = ["columns"]

    def transform(self, df: pd.DataFrame, columns: List[ColumnModel], rows: Optional[None] = None) -> pd.DataFrame:
        """
        Delete columns provided in a list.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: List of ColumnModel
            List of column names to be deleted.
        rows: None
            Ignored for this ACTION.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        return df.drop(columns=[c.name for c in columns])
