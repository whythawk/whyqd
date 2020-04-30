import pandas as pd
from whyqd.core import BaseMorph

class Morph(BaseMorph):
    """
    Rename header columns listed in a dict.
    """
    def __init__(self):
        self.name = "RENAME"
        self.title = "Rename"
        self.description = "Rename header columns listed in a dict."
        self.structure = ["column_names"]

    def validates(self, df=pd.DataFrame(), rows=None, columns=None, column_names=None):
        """
        Tests whether length of column_names is the same as that of the columns in the DataFrame. Replaces default test.

        Parameters
        ----------
        column_names: list
        df: dataframe
            The source DataFrame.

        Returns
        -------
        bool
            True if valid
        """
        self._set_parameters(column_names=column_names)
        if isinstance(column_names, list) and (len(column_names) == len(df.columns)):
            return True
        return False

    def transform(self, df=pd.DataFrame(), column_names=None):
        """
        Rename header columns listed in a dict.

        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        columns: list
            List of new column names.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        df.columns = column_names
        return df