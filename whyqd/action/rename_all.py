from __future__ import annotations
from typing import Optional, List

# import pandas as pd
import modin.pandas as pd

from whyqd.base import BaseMorphAction


class Action(BaseMorphAction):
    """Rename all header column labels.

    Script::

        "RENAME_ALL > ['column_name', 'column_name', etc.]"

    Where `column_name` is a new `string` column name, and the length of the array must equal the length of the
    number of columns in the table.

    .. warning:: Get the order right. This is a one-for-one replacement of the existing column labels.
    """

    def __init__(self) -> None:
        self.name = "RENAME_ALL"
        self.title = "Rename all"
        self.description = "Rename header columns listed in a dict."
        self.structure = ["columns"]

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

    def transform(self, df: pd.DataFrame, columns: List[str], rows: Optional[None] = None) -> pd.DataFrame:
        """
        Rename header columns listed in a dict.

        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        columns: list of str
            List of new column names.
        rows: None
            Ignored for this ACTION.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        df.columns = columns
        return df
