from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING
import numpy as np

from whyqd.transform.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd
    from whyqd.metamodel.models import ColumnModel


class Action(BaseMorphAction):
    """Split the string values in a single column into any number of new columns on a specified key.

    Script::

        "SPLIT > 'by'::['source_column']"

    Where `'by'` can be any `string` with one **MAJOR** caveat. Since `::` is used in the query, you **cannot** use it
    for splitting.

    Example::

        == ========================
        ID split_column
        == ========================
        2  Dogs;;Cats;;Fish
        3  Cats;;Bats;;Hats;;Mats
        4  Sharks;;Crabs
        == ========================

        "SPLIT > ';;'::['source_column']"

        == ======================== ======= ======= ======= =======
        ID split_column             new_1   new_2   new_3   new_4
        == ======================== ======= ======= ======= =======
        2  Dogs;;Cats;;Fish         Dogs    Cats    Fish
        3  Cats;;Bats;;Hats;;Mats   Cats    Bats    Hats    Mats
        4  Sharks;;Crabs            Sharks  Crabs
        == ======================== ======= ======= ======= =======

    Will generate new columns `SPLIT_idx_<column.index>_<sequential_integer>`.
    """

    def __init__(self):
        self.name = "SPLIT"
        self.title = "Split strings"
        self.description = (
            "Split the string values in a single column into any number of new columns on a specified key."
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
        Split the string values in a single column into any number of new columns on a specified key.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: List of ColumnModel
            List of column names to be pivoted into long format.
        rows: list of integer
            List of row indices as integers for rows where categories are found.
        param: str
            String to split

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        # splitting indefinite numbers of items
        # https://stackoverflow.com/a/50459986/295606
        # https://stackoverflow.com/a/39358924/295606
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.str.extract.html
        if not param:
            raise ValueError("SPLIT morph action did not receive an expected split-by parameter.")
        hx = self._generate_hex()
        split_array = np.array([x.split(param) for x in df[columns[0].name].array.ravel()], dtype=object)
        num_columns = max(map(len, split_array))
        if num_columns == 1:
            return df
        new_columns = [f"{self.name}_{hx}_{i}" for i in range(num_columns)]
        df[new_columns] = df[columns[0].name].str.split(param, expand=True)
        return self._column_renames_to_index(df=df, columns=new_columns, hex=hx)
