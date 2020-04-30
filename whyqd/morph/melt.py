import pandas as pd
import numpy as np
from whyqd.core import BaseMorph

class Morph(BaseMorph):
    """
    Transform a DataFrame from wide to long format.
    """
    def __init__(self):
        self.name = "MELT"
        self.title = "Melt"
        self.description = "Transform a DataFrame from wide to long format."
        self.structure = ["columns", "column_names"]

    def validates(self, df=pd.DataFrame(), rows=None, columns=None, column_names=None):
        """
        Traverses a list defined by `*structure`, ensuring that the terms conform to that morph's
        default structural requirements.

        The format for defining a `structure` is as follows::

            [morph, [rows], [columns], [column_names]]

        e.g.::

            ["RENAME", ["column_1", "column_2"]]

        A calling function would specify something like::

            Morph.validates(df, **dict((zip(['rows','columns','column_names'], structure[1:])))

        Parameters
        ----------
        columns: list
            Two lists of column names: 
                columns[0] is id_columns to be maintained.
                columns[1] is value_columns to be transformed.
            If only a list of str is provided, assumed to be value_columns only
        column_names: list
            Two column names: 
                columns[0] is var_name for list of value_columns to be transformed.
                columns[1] is value_name for values from value_columns being transformed.
        df: dataframe
            The source DataFrame.

        Returns
        -------
        bool
            True if valid
        """
        self._set_parameters(rows, columns, column_names)
        for p in self.structure:
            if p == "columns":
                if ((len(self.settings["parameters"][p]) == 2) and 
                    all([not all([isinstance(k, list) or isinstance(k, dict) for k in l]) 
                         if isinstance(l, list) else False 
                         for l in self.settings["parameters"][p]]) and
                    all((set(c) <= set(df.columns)) for c in self.settings["parameters"][p])):
                    continue
                elif (not all([isinstance(k, list) or isinstance(k, dict) for k in self.settings["parameters"][p]]) and
                      set(self.settings["parameters"][p]) <= set(df.columns)):
                    # Only a list of `value_columns` have been provided. Extract the id_columns
                    id_columns = list(set(df.columns) - set(self.settings["parameters"][p]))
                    columns = [id_columns, self.settings["parameters"][p]]
                    self._set_parameters(rows, columns, column_names)
                    continue
                return False
            if p == "column_names":
                # Ensure column_names are not in df.columns
                column_names = self.settings["parameters"].get(p, [F"new_{self.name.lower()}_var", 
                                                                   F"new_{self.name.lower()}_values"])
                if len(column_names) == 1:
                    column_names = [F"{column_names[0]}_var", F"{column_names[0]}_values"]
                column_names = [self._set_unique_name(df, c) for c in column_names]
                self._set_parameters(rows, columns, column_names)
                continue
        return True

    def transform(self, df=pd.DataFrame(), columns=None, column_names=None):
        """
        Transform a DataFrame from wide to long format.
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        columns: list
            Two lists of column names: 
                columns[0] is id_columns to be maintained.
                columns[1] is value_columns to be transformed.
        column_names: list
            Two column names: 
                columns[0] is var_name for list of value_columns to be transformed.
                columns[1] is value_name for values from value_columns being transformed.

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        id_columns, value_columns = columns
        var_name, value_name = column_names
        # https://pandas.pydata.org/docs/reference/api/pandas.melt.html
        return pd.melt(df, id_vars=id_columns, value_vars=value_columns,
                    var_name=var_name, value_name=value_name)