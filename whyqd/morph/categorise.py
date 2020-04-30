import pandas as pd
import numpy as np
from whyqd.core import BaseMorph

class Morph(BaseMorph):
    """
    Convert row-level categories into column categorisations.
    """
    def __init__(self):
        self.name = "CATEGORISE"
        self.title = "Categorise"
        self.description = "Convert row-level categories into column categorisations."
        self.structure = ["rows", "column_names"]

    def transform(self, df=pd.DataFrame(), rows=None, column_names=None):
        """
        Convert row-level categories into column categorisations. Makes several assumptions:
        
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

            indices = [1, 5]
            
            == ===== ============
            ID Term  New_category
            == ===== ============
            2 Term2 Cat1
            3 Term3 Cat1
            4 Term4 Cat1
            6 Term6 Cat2
            7 Term7 Cat2
            8 Term8 Cat2
            == ===== ============
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        rows: list
            List of row indices as integers for rows where categories are found.
        column_names: list of str
            List of unique column names to use. Optional, will be created if not provided.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        if not column_names:
            column_names = [self._set_unique_name(df)]
        first_column = column_names[0]
        new_columns = {}
        # Get all columns with category-terms in each indexed row
        for i, idx in enumerate(rows):
            to_idx = len(df)
            if i+1 < len(rows):
                to_idx = rows[i+1]
            category_columns = {k: v for k,v in df.loc[idx].items() if pd.notnull(v)}
            for k in category_columns:
                if k not in new_columns:
                    if not column_names: nc = F"{first_column}_{i}"
                    else: nc = column_names.pop(0)
                    new_columns[k] = nc
                nc = new_columns[k]
                # https://stackoverflow.com/a/46307319
                idx_list = np.arange(idx+1,to_idx)
                df.loc[df.index.intersection(idx_list), nc] = category_columns[k]
        df = df.drop(rows, errors="ignore")
        return df