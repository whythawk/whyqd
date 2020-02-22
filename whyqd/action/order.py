import pandas as pd

from whyqd.core import BaseAction

class Action(BaseAction):
    """
    Create a new field by iterating over a list of fields and picking the next value in the list.
    """
    def __init__(self):
        self.name = "ORDER"
        self.title = "Order"
        self.description = "Use sparse data from a list of fields to populate a new field. Order is important, each successive field in the list have priority over the ones before it (e.g. for columns A, B & C, values in C will have precedence over values in B and A)."
        self.structure = ["field"]

    def transform(self, df, field_name, structure, **kwargs):
        """
        Create a new field by iterating over a list of fields and picking the next value in the list.

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
        fields = [field["name"] for field in structure]
        df.rename(index=str, columns= {fields[0]: field_name}, inplace=True)
        for field in fields[1:]:
            df.loc[:, field_name] = df.apply(lambda x: (x[field]
                                                        if pd.notnull(x[field])
                                                        else x[field_name]),
                                            axis=1)
        return df