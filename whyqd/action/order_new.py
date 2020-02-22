import pandas as pd
import numpy as np

from whyqd.core import BaseAction

class Action(BaseAction):
    """
    Create a new field by iterating over a list of fields and picking the newest value in the list.
    """
    def __init__(self):
        self.name = "ORDER_NEW"
        self.title = "Order by newest"
        self.description = "Use sparse data from a list of fields to populate a new field order by most recent value. Field-pairs required, with the first containing the values, and the second the dates for comparison, linked by a '+' modifier (e.g. A+dA, B+dB, C+dC, values with the most recent associated date will have precedence over other values)."
        self.structure = ["field", "modifier", "field"]

    @property
    def modifiers(self):
        """
        Describes the modifiers for order by newest.

        Returns
        -------
        dict
            Dict representation of the modifiers.
        """
        modifiers = [
            {
                "name": "+",
                "title": "Links",
                "type": "modifier"
            }
        ]
        return modifiers

    def transform(df, field_name, structure, **kwargs):
        """
        Create a new field by iterating over a list of fields and picking the newest value in
	    the list. Requires a "datename" constraint, otherwise it raise a ValueError.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        field_name: str
            Name of the target schema field
        structure: list
            List of fields with restructuring action defined by term 0 (i.e. `this` action)
        **kwargs: 
            Other fields which may be required in custom transforms

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        fields = [field["name"] for field in structure[1:]]
        base_date = None
        # Requires sets of 3 terms: field, +, date_field
        term_set = len(self.structure)
        for data, modifier, date in _c.chunks(fields, term_set):
            if modifier != "+":
                e = "Field `{}` has invalid ORDER_BY_NEW method. Please review.".format(field_name)
                raise ValueError(e)
            if not base_date:
                # Start the comparison on the next round
                df.rename(index=str, columns= {data: field_name}, inplace=True)
                base_date = date
                if data == date:
                    # Just comparing date columns
                    base_date = field_name
                df.loc[:, base_date] = df.loc[:, base_date].apply(lambda x: pd.to_datetime(_c.parse_dates(x),
                                                                                        errors="coerce"))
                continue
            # np.where date is <> base_date and don't replace value with null
            # logic: if test_date not null & base_date <> test_date
            # False if (test_date == nan) | (base_date == nan) | base_date >< test_date
            # Therefore we need to test again for the alternatives
            df.loc[:, date] = df.loc[:, date].apply(lambda x: pd.to_datetime(_c.parse_dates(x),
                                                                            errors="coerce"))
            df.loc[:, field_name] = np.where(~pd.notnull(df[date]) | (df[base_date] > df[date]),
                                            np.where(pd.notnull(df[field_name]),
                                                    df[field_name], df[data]),
                                            np.where(pd.notnull(df[data]),
                                                    df[data], df[field_name]))
            if base_date != field_name:
                df.loc[:, base_date] = np.where(~pd.notnull(df[date]) | (df[base_date] > df[date]),
                                                np.where(pd.notnull(df[base_date]),
                                                        df[base_date], df[date]),
                                                np.where(pd.notnull(df[date]),
                                                        df[date], df[base_date]))
        return df