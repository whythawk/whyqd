import pandas as pd
import numpy as np
from whyqd.core import BaseMorph

class Morph(BaseMorph):
    """
    Rebase the header row at an indexed row and drop rows above that point.
    """
    def __init__(self):
        self.name = "REBASE"
        self.title = "Rebase"
        self.description = "Rebase the header row at an indexed row and drop rows above that point."
        self.structure = ["rows"]

    def transform(self, df=pd.DataFrame(), rows=None):
        """
        Rebase the header row at an indexed row and drop rows above that point.

        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        rows: integer or list of integer
            Row to be set as new header. Pandas rows start at 0.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        df.rename(columns=df.loc[rows[0]], inplace = True)
        idx_list = np.arange(0,rows[0]+1)
        return df.drop(df.index.intersection(idx_list))