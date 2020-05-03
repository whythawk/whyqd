"""
Base class defining core functions to Morph a table in a dataframe.
"""
import random
import pandas as pd
import numpy as np
from string import ascii_letters

class BaseMorph:
    """
    Custom Morphs inherit from this base class which describes the core functions and methodology for a Morph.

    Morphs should redefine `name`, `id`, `structure`, and `parameters`, as well as produce a `transform` function. 
    Everything else will probably remain as defined, but particularly complex Morphs should modify as required.

    `parameters` can be an empty dict, but a morph may be defined by these parameters:

    * `rows`: the specific rows effected by the morph, a `list` of `int`
    * `columns`: the specific columns effected by the morph, a `list` of `string`

    A morph defined as JSON is, e.g.::

        {
            "name": "xxxxx",
            "parameters": {
                "rows": [1,2,3],
                "columns": ["column1"]
            }
        }

    In markup, the user codes::

        morph = ["MORPH_NAME", [rows], [columns]]
        method.set_morph(morph)

    Where the presence and order of the lists is set by `structure`.
    """
    def __init__(self):
        self.name = ""
        self.title = ""
        self.description = ""
        # `structure` defines the format in which parameters for a morph are written, and validated in 
        # `validate` can be any of `rows`, `columns` or `column_names`
        # additional terms will require overriding the `has_valid_structure` function
        self.structure = []

    @property
    def settings(self):
        """
        Returns the dict representation of the Morph.

        Raises
        ------
        NameError if parameters don't yet exist.

        Returns
        -------
        dict
            Dict representation of a Morph.
        """
        morph_settings = {
            "name": self.name,
            "title": self.title,
            "type": "morph",
            "description": self.description,
            "structure": self.structure
        }
        if self.structure:
            try:
                morph_settings["parameters"] = dict(zip(self.structure, self.parameters))
            except (NameError, AttributeError):
                morph_settings["parameters"] = {}
        return morph_settings

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
        rows: int or list of int
        columns: str or list of str
        column_names: str or list of str
        df: dataframe
            The source DataFrame.

        Returns
        -------
        bool
            True if valid
        """
        if not self.structure:
            return True
        self._set_parameters(rows, columns, column_names)
        for p in self.structure:
            if p == "rows":
                if all([isinstance(k, int) for k in self.settings["parameters"][p]]):
                    continue
                return False
            if p in ["columns", "column_names"]:
                if all([(not isinstance(k, list) and not isinstance(k, dict)) for k in self.settings["parameters"][p]]):
                    if (p == "columns" and 
                        set(self.settings["parameters"][p]) <= set(df.columns)):
                        # All columns are in df.columns
                        continue
                    elif p == "column_names":
                        # Ensure column_names are not in df.columns
                        column_names = self.settings["parameters"].get(p, [F"new_{self.name.lower()}"])
                        column_names = [self._set_unique_name(df, c) for c in column_names]
                        self._set_parameters(rows, columns, column_names)
                        continue
                return False
        return True

    def transform(self, df=pd.DataFrame(), **kwargs):
        """
        Perform a transformation. This function must be overridden by child Morphs and describe a unique
        new method.

        .. warning:: Assumes `validates` has been run.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        **kwargs: 
            Other fields which may be required in custom transforms

        Returns
        -------
        Dataframe
            Containing the implementation of the Morph
        """
        return df

    def _set_parameters(self, rows=None, columns=None, column_names=None):
        """
        Set the parameters for provided fields. Does not validate them.

        Parameters
        ----------
        rows: int or list of int
        columns: str or list of str
        column_names: str or list of str
        """
        self.parameters = []
        for c in [rows, columns, column_names]:
            if c is not None:
                if not isinstance(c, list): c = [c]
                self.parameters.append(c)

    def _set_unique_name(self, df=pd.DataFrame(), column_name=None):
        """
        Create an unique column name required by this Morph.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        column_name: str
            Preferred column name to be used, defaults to the morph name

        Returns
        -------
        str
            Unique column name
        """
        if not column_name:
            column_name = F"new_{self.name.lower()}"
        if column_name in df.columns:
            column_name += self._generate_unique_suffix(df.columns)
        return column_name

    def _generate_suffix(self):
        x = ascii_letters
        return "_" + "".join(list((random.choice(x) for num in range(3))))
    
    def _generate_unique_suffix(self, terms):
        suffix = self._generate_suffix()
        while suffix in [t[-4:] for t in terms]:
            suffix = self._generate_suffix()
        return suffix