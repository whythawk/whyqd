from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from whyqd.transform.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """Remove all blank columns and rows from a DataFrame.

    Script::

        "DEBLANK"
    """

    def __init__(self) -> None:
        self.name = "DEBLANK"
        self.title = "De-blank"
        self.description = "Remove all blank columns and rows from a DataFrame."
        self.structure = []

    def transform(self, *, df: pd.DataFrame, columns: Optional[None] = None, rows: Optional[None] = None) -> pd.DataFrame:
        """
        Remove all blank columns and rows from a DataFrame.

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
        # https://stackoverflow.com/a/51794989
        # First remove all columns (axis=1) with no values
        df = df.dropna(how="all", axis=1)
        # Remove all rows (axis=0) with no values
        return df.dropna(how="all", axis=0)
