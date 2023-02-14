from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

from whyqd.transform.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd
    from whyqd.metamodel.models import ColumnModel


class Action(BaseMorphAction):
    """Rename a column outside of the schema or existing column definitions. To be used with caution.

    Script::

        "RENAME_NEW > 'new_column'::['source_column']"

    Where `'new_column'` can be any `string` with one **MAJOR** caveat. Since `::` is used in the query, you **cannot** use it
    in the string.
    """

    def __init__(self):
        self.name = "RENAME_NEW"
        self.title = "Rename new"
        self.description = (
            "Rename a column outside of the schema or existing column definitions. To be used with caution."
        )
        self.structure = ["columns"]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        columns: Optional[List[ColumnModel]] = None,
        rows: Optional[List[None]] = None,
        param: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Rename a column outside of the schema or existing column definitions. To be used with caution.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: List of ColumnModel
            List of column names to be pivoted into long format.
        rows: list of integer
            List of row indices as integers for rows where categories are found.
        param: str
            String as new column

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        if not param:
            raise ValueError("RENAME_NEW morph action did not receive an expected new column parameter.")
        # {'from': 'too'}
        return df.rename(index=str, columns={columns[0].name: param})
