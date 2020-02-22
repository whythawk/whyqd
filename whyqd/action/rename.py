from whyqd.core import BaseAction

class Action(BaseAction):
    """
    Rename the field to the schema field.
    """
    def __init__(self):
        self.name = "RENAME"
        self.title = "Rename"
        self.description = "Rename an existing field to conform to a schema name. Only valid where a single field is provided."
        self.structure = ["field"]

    def transform(self, df, field_name, structure, **kwargs):
        """
        Rename the field to the schema field.

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
        # Rename, note, can only be one field if a rename ...
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rename.html
        # {'from': 'too'}
        df.rename(index=str,
                columns= {structure[0]["name"]: field_name},
                inplace=True)
        return df