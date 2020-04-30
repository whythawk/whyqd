"""
.. module:: morph
:synopsis: Create and manage a method to morph a table in a dataframe.

.. moduleauthor:: Gavin Chait <github.com/turukawa>

Morph
=====

Create and manage a method to morph a table in a dataframe.

Methods include:

* remove_blanks: Remove all blank columns and rows from a DataFrame.
* remove_duplicates: Remove all duplicated rows from a DataFrame.
* rebase_header: Rebase the header row at index and drop rows above that point.
* rename_header: Rename header columns listed in a dict.
* drop_rows: Delete rows between two indices.
* category_rows_to_columns: Convert row-level categories into column categorisations.
* pivot_long: Transform a DataFrame from wide to long format.
"""

import pandas as pd
import numpy as np
import random, uuid
from copy import deepcopy
from string import ascii_letters

class Morph:
    """
    Create and manage a method to morph a table in a dataframe.
    
    Could be done with pandas, but the objective is to have an audit trail
    of specific transformations performed on each table. Note, some things
    still cannot be reduce to simple, auditable morphs.
    
    Parameters
    ----------
    df: pandas dataframe
        DataFrame for implementation of method.
    method: list
        List of dictionary objects each defining a step in the method.
    """
    
    def __init__(self, df, method=None):
        self.df = df.copy()
        self.method = method
        if not self.method:
            self.reset()
            
    @property
    def _get_id(self):
        """
        Return a unique a id for reference in each morph method. Permits editing / deletion.
        """
        return str(uuid.uuid4())
            
    def remove_blanks(self):
        """
        Append `remove_blanks` method to remove all blank columns and rows from a DataFrame.
        """
        self.method.append({
            "id": self._get_id,
            "name": "remove_blanks"
        })
        
    def remove_duplicates(self):
        """
        Append `remove_duplicates` method to remove all duplicate rows from a DataFrame.
        """
        self.method.append({
            "id": self._get_id,
            "name": "remove_duplicates"
        })
        
    def rebase_header(self, index):
        """
        Append `rebase_header` method to rebase the header row at index and drop rows above that point.
        
        Parameters
        ----------
        index: integer
            Row to be set as new header. Pandas rows start at 0.
        """
        self.method.append({
            "id": self._get_id,
            "name": "rebase_header",
            "parameters": {
                "index": index
            }
        })
        
    def rename_header(self, columns):
        """
        Append `rename_header` method to rename header columns listed in a dict.
        
        Parameters
        ----------
        columns: dict, list
            Keys are columns to be changed, values are new column names.
        """
        if isinstance(columns, list):
            # If list, check if == length of existing columns
            df = self.transform(reset_index=False)
            if len(df.columns) != len(columns):
                e = F"Number of terms in list is not equal to DataFrame columns: {df.columns}."
                raise KeyError(e)
            columns = dict(zip(df.columns, columns))
        self.method.append({
            "id": self._get_id,
            "name": "rename_header",
            "parameters": {
                "columns": columns
            }
        })
        
    def drop_rows(self, from_index, to_index):
        """
        Append `drop_rows` method to delete rows between two indices.
        
        Parameters
        ----------
        from_index: integer
            Start-row for deletion. Pandas rows start at 0.
        to_index: integer
            End-row for deletion.
            
        Raises
        ------
        ValueError if from_index >= to_index or if either are not integers.
        """
        if not isinstance(from_index, int) or not isinstance(to_index, int):
            e = F"'from_index' and 'to_index' must be integers."
            raise ValueError(e)
        if from_index >= to_index:
            e = F"'from_index' ({from_index}) must be less than 'to_index' ({to_index})."
            raise ValueError(e)
        self.method.append({
            "id": self._get_id,
            "name": "drop_rows",
            "parameters": {
                "from_index": from_index,
                "to_index": to_index
            }
        })

        
    def category_rows_to_columns(self, indices, column_name="New_category"):
        """
        Append `category_rows_to_columns` method to convert row-level categories 
        into column categorisations. Makes several assumptions:
        
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
        indices: list
            List of row indices as integers for rows where categories are found.
        column_name: str
            Base name for new category column(s).
        """
        df = self.transform(reset_index=False)
        # Get all columns with category-terms in each indexed row
        new_columns = {}
        for idx in indices:
            category_columns = {k: v for k,v in df.loc[idx].items() if pd.notnull(v)}
            for k in category_columns:
                if k not in new_columns:
                    nc = column_name
                    if nc in df.columns:
                        id_terms = [t[-4:] for t in df.columns]
                        nc += _generate_unique_suffix(id_terms)
                    new_columns[k] = nc
        self.method.append({
            "id": self._get_id,
            "name": "category_rows_to_columns",
            "parameters": {
                "indices": indices,
                "new_columns": new_columns
            }
        })
        
    def pivot_long(self, value_columns, var_name="Long_variable", value_name="Long_value"):
        """
        Append `pivot_long` method to transform a DataFrame from wide to long format.
        
        Parameters
        ----------
        value_columns: list
            List of column names as strings to be transformed.
        var_name: string
            Column name for list of value_columns to be transformed.
        value_name: string
            Column name for values from value_columns being transformed.
            
        Raises
        ------
        ValueError if value_columns not in dataframe column list.
        """
        df = self.transform(reset_index=False)
        malformed = set(value_columns).difference(set(df.columns))
        if malformed:
            e = F"Column names not present in dataframe: {malformed}"
            raise ValueError(e)
        id_columns = set(df.columns).difference(set(value_columns))
        id_terms = [t[-4:] for t in id_columns]
        if var_name in id_columns:
            var_name += self._generate_unique_suffix(id_terms)
        if value_name in id_columns:
            value_name += self._generate_unique_suffix(id_terms)
        self.method.append({
            "id": self._get_id,
            "name": "pivot_long",
            "parameters": {
                "id_columns": id_columns,
                "value_columns": value_columns,
                "var_name": var_name,
                "value_name": value_name
            }
        })
        
    @property
    def settings(self):
        """
        Method settings returned as a list.

        Returns
        -------
        list: settings
        """
        return deepcopy(self.method)
    
    @property
    def view(self):
        """
        Return copy of dataframe.

        Returns
        -------
        dataframe
        """
        return self.df.copy()
    
    def transform(self, reset_index=True):
        """
        Implements the morph described in the method. Does not check if it has been
        run before, so may wreck your table entirely.
        
        Returns
        -------
        dataframe: morphed
        """
        morph_methods = {
            "remove_blanks": self._remove_blanks,
            "remove_duplicates": self._remove_duplicates,
            "rebase_header": self._rebase_header,
            "rename_header": self._rename_header,
            "drop_rows": self._drop_rows,
            "category_rows_to_columns": self._category_rows_to_columns,
            "pivot_long": self._pivot_long
        }
        df = self.df.copy()
        for m in self.method:
            morph = morph_methods[m["name"]]
            if m.get("parameters"):
                df = morph(df, **m["parameters"])
            else:
                df = morph(df)
        if reset_index:
            df.reset_index(drop=True, inplace=True)
        return df
    
    def delete(self, _id):
        """
        Delete morph method by id.
        
        Parameters
        ----------
        _id: string        
        """
        self.method = [m for m in self.method if not(m["id"] == _id)]
        
    def reset(self, empty=False):
        """
        Reset list of morph methods to base.      
        """
        self.method = []
        if not empty:
            self.remove_blanks()
            self.remove_duplicates()

    def reorder(self, order):
        """
        Reorder morph methods.
        
        Parameters
        ----------
        order: list
            List of id strings.
            
        Raises
        ------
        ValueError if not all ids in list, or duplicates in list.
        """
        if len(order) > len(self.method):
            e = F"List of ids is longer than list of methods."
            raise ValueError(e)
        if set([i["id"] for i in self.method]).difference(set(order)):
            e = F"List of ids must contain all method ids."
            raise ValueError(e)
        self.method = sorted(self.method, key = lambda item: order.index(item["id"]))
    
    def _remove_blanks(self, df):
        """
        Remove all blank columns and rows from a DataFrame.
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        """
        # https://stackoverflow.com/a/51794989
        # First remove all columns (axis=1) with no values
        df = df.dropna(how="all", axis=1)
        # Remove all rows (axis=0) with no values
        return df.dropna(how="all", axis=0)
    
    def _remove_duplicates(self, df):
        """
        Remove all duplicated rows from a DataFrame.
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        """
        #https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.drop_duplicates.html
        return df.drop_duplicates()
        
    def _rebase_header(self, df, index):
        """
        Rebase the header row at index and drop rows above that point.
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        index: integer
            Row to be set as new header. Pandas rows start at 0.
        """
        df.rename(columns=df.loc[index], inplace = True)
        idx_list = np.arange(0,index+1)
        return df.drop(df.index.intersection(idx_list))
        
    def _rename_header(self, df, columns):
        """
        Rename header columns listed in a dict.
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        columns: dict
            Keys are columns to be changed, values are new column names.
        """
        return df.rename(columns=columns)

    def _drop_rows(self, df, from_index, to_index):
        """
        Delete rows between two indices.
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        from_index: integer
            Start-row for deletion. Pandas rows start at 0.
        to_index: integer
            End-row for deletion.
        """
        idx_list = np.arange(from_index,to_index+1)
        return df.drop(df.index.intersection(idx_list))

    def _category_rows_to_columns(self, df, indices, new_columns):
        """
        Convert row-level categories into column categorisations. Makes several
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
        indices: list
            List of row indices as integers for rows where categories are found.
        new_columns: dict
            Keys are columns with categories, values are new columns to be created.
        """
        # Get all columns with category-terms in each indexed row
        for i, idx in enumerate(indices):
            to_idx = len(df)
            if i+1 < len(indices):
                to_idx = indices[i+1]
            category_columns = {k: v for k,v in df.loc[idx].items() if pd.notnull(v)}
            for k in category_columns:
                nc = new_columns[k]
                # https://stackoverflow.com/a/46307319
                idx_list = np.arange(idx+1,to_idx)
                df.loc[df.index.intersection(idx_list), nc] = category_columns[k]
        df = df.drop(indices, errors="ignore")
        return df

    def _pivot_long(self, df, id_columns, value_columns, var_name, value_name):
        """
        Transform a DataFrame from wide to long format.
        
        Parameters
        ----------
        df: dataframe
            DataFrame must be explicitly provided. Permits action on copy.
        id_columns: list
            List of column names as strings to be maintained.
        value_columns: list
            List of column names as strings to be transformed.
        var_name: string
            Column name for list of value_columns to be transformed.
        value_name: string
            Column name for values from value_columns being transformed.
        """
        # https://pandas.pydata.org/docs/reference/api/pandas.melt.html
        return pd.melt(df, id_vars=id_columns, value_vars=value_columns,
                    var_name=var_name, value_name=value_name)
        
    def _generate_suffix(self):
        x = ascii_letters
        return "_" + "".join(list((random.choice(x) for num in range(3))))
    
    def _generate_unique_suffix(self, terms):
        suffix = _generate_suffix()
        while suffix in in_list:
            suffix = _generate_suffix()
        return suffix