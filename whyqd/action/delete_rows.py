from __future__ import annotations
from typing import Optional, List, TYPE_CHECKING

# import pandas as pd

from whyqd.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """Delete rows and provided in a list. They don't have to be contiguous.

    Script::

        "DELETE_ROWS < [int, int, int, etc.]"

    Where `int` are  specific integer row references / indices. Delete specifically does *not* reindex the rows so
    that future reference calls will reference a static index.
    """

    def __init__(self) -> None:
        self.name = "DELETE_ROWS"
        self.title = "Delete rows"
        self.description = "Delete rows provided in a list. They don't have to be contiguous."
        self.structure = ["rows"]

    def transform(
        self, df: pd.DataFrame, columns: Optional[None] = None, rows: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Delete rows provided in a list. They don't have to be contiguous.

        If you specifically wish to provide a range, then provide rows as::

            np.arange(start,end+1)

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: None
            Ignored for this ACTION.
        rows: list of integer
            Rows to be deleted. Do not need to be contiguous. Pandas rows start at 0.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        return df.drop(df.index.intersection(rows))
