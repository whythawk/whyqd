import pandas as pd
from whyqd.core import BaseMorph

class Morph(BaseMorph):
    """
    Delete rows provided in a list. They don't have to be contiguous.
    """
    def __init__(self):
        self.name = "DELETE"
        self.title = "Delete"
        self.description = "Delete rows provided in a list. They don't have to be contiguous."
        self.structure = ["rows"]

    def transform(self, df=pd.DataFrame(), rows=None):
        """
        Delete rows provided in a list. They don't have to be contiguous.

        If you specifically wish to provide a range, then provide rows as::

            np.arange(start,end+1)

        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        rows: list of integer
            Rows to be deleted. Do not need to be contiguous. Pandas rows start at 0.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        return df.drop(df.index.intersection(rows))