from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING

# import pandas as pd
import numpy as np
import itertools

from whyqd.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """Rebase the header row at an indexed row and drop rows above that point.

    Script::

        "REBASE < [int]"

    Where `int` is the  specific integer row to set as the header, changing the column labels to those in this row.
    Rebase specifically does *not* reindex the rows so that future reference calls will reference a static index.
    """

    def __init__(self) -> None:
        self.name = "REBASE"
        self.title = "Rebase"
        self.description = "Rebase the header row at an indexed row and drop rows above that point."
        self.structure = ["rows"]

    def transform(
        self, df: pd.DataFrame, columns: Optional[None] = None, rows: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Rebase the header row at an indexed row and drop rows above that point.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: None
            Ignored for this ACTION.
        rows: list of integer
            Row to be set as new header. Pandas rows start at 0. Only the first listed int will be used.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        df.rename(columns=df.loc[rows[0]].to_dict(), inplace=True)
        idx_list = np.arange(0, rows[0] + 1)
        df = df.drop(df.index.intersection(idx_list))
        df.columns = df.columns.map(str)
        # Rebasing can introduce duplicated column names, and 'nan' column names
        if df.columns.duplicated().any():
            excluded = df.columns[~df.columns.duplicated(keep=False)]
            increment = itertools.count().__next__
            columns = [f"{c}{increment()}" if c not in excluded else c for c in df.columns]
            df.columns = columns
        return df
