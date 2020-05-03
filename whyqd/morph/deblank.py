import pandas as pd
from whyqd.core import BaseMorph

class Morph(BaseMorph):
    """
    Remove all blank columns and rows from a DataFrame.
    """
    def __init__(self):
        self.name = "DEBLANK"
        self.title = "De-blank"
        self.description = "Remove all blank columns and rows from a DataFrame."
        self.structure = []

    def transform(self, df=pd.DataFrame()):
        """
        Remove all blank columns and rows from a DataFrame.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed

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