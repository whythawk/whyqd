from __future__ import annotations
from typing import List, TYPE_CHECKING
import modin.pandas as pd
import numpy as np

from whyqd.transform.base import BaseMorphAction

if TYPE_CHECKING:
    from whyqd.metamodel.models import ColumnModel


class Action(BaseMorphAction):
    """Convert row-level categories into column categorisations.

    Script::

        "PIVOT_CATEGORIES > ['source_column', 'source_column', etc.] < [int, int, int, etc.]"

    Where `int` contains the rows that define the categories, and `column` are the columns to include. Makes several
    assumptions:

    * Rows may contain more than one category
    * All terms in indexed rows in the same column are related
    * Categories are assigned downwards to all rows between indices
    * The last indexed category is assigned to all rows to the end of the table

    Example::

        == =====
        ID Term
        == =====
        1 Cat1
        2 Term2
        3 Term3
        4 Term4
        5 Cat2
        6 Term6
        7 Term7
        8 Term8
        == =====

        "PIVOT_CATEGORIES > ['Term'] < [1, 5]"

        == ===== ========================
        ID Term  PIVOT_CATEGORIES_idx_2_0
        == ===== ========================
        2 Term2 Cat1
        3 Term3 Cat1
        4 Term4 Cat1
        6 Term6 Cat2
        7 Term7 Cat2
        8 Term8 Cat2
        == ===== ========================

    Will generate new columns `PIVOT_CATEGORIES_idx_<column.index>_<sequential_integer>`.
    """

    def __init__(self):
        self.name = "PIVOT_CATEGORIES"
        self.title = "Pivot categories"
        self.description = "Convert row-level categories into column categorisations."
        self.structure = ["rows", "columns"]

    def transform(self, *, df: pd.DataFrame, columns: List[ColumnModel], rows: List[int]) -> pd.DataFrame:
        """
        Convert row-level categories into column categorisations.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        columns: List of ColumnModel
            List of column names to be pivoted into long format.
        rows: list of integer
            List of row indices as integers for rows where categories are found.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        new_columns = {}
        hx = self._generate_hex()
        columns = [c.name for c in columns]
        for i, idx in enumerate(rows):
            to_idx = df.index[-1] + 1
            if i + 1 < len(rows):
                to_idx = rows[i + 1]
            category_columns = {k: v for k, v in df.loc[idx].items() if pd.notnull(v) and k in columns}
            for k in category_columns:
                if k not in new_columns:
                    nc = f"{self.name}_{hx}_{i}"
                    new_columns[k] = nc
                    # Fix: Multiple arguments results in keyerror in Modin
                    df[nc] = None
                # https://stackoverflow.com/a/46307319
                idx_list = np.arange(idx + 1, to_idx)
                # Fix: Multiple arguments results in keyerror in Modin
                # https://github.com/modin-project/modin/issues/4354
                df.loc[df.index.intersection(idx_list), nc] = category_columns[k]
        df = df.drop(rows, errors="ignore")
        return self._column_renames_to_index(df=df, columns=list(new_columns.values()), hex=hx)
