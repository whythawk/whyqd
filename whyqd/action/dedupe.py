from __future__ import annotations
from typing import Optional, TYPE_CHECKING

# import pandas as pd

from whyqd.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """Remove all duplicated rows from a DataFrame.

    Script::

        "DEDUPE"
    """

    def __init__(self) -> None:
        self.name = "DEDUPE"
        self.title = "Deduplicate"
        self.description = "Remove all duplicated rows from a DataFrame."
        self.structure = []

    def transform(self, df: pd.DataFrame, columns: Optional[None] = None, rows: Optional[None] = None) -> pd.DataFrame:
        """
        Remove all duplicated rows from a DataFrame.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: None
            Ignored for this ACTION.
        rows: None
            Ignored for this ACTION.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.drop_duplicates.html
        return df.drop_duplicates()
