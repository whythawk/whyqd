import pandas as pd
from whyqd.core import BaseMorph

class Morph(BaseMorph):
    """
    Remove all blank columns and rows from a DataFrame.
    """
    def __init__(self):
        self.name = "DEDUPE"
        self.title = "Deduplicate"
        self.description = "Remove all duplicated rows from a DataFrame."
        self.structure = []

    def transform(self, df=pd.DataFrame()):
        """
        Remove all duplicated rows from a DataFrame.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        #https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.drop_duplicates.html
        return df.drop_duplicates()