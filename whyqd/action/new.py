from whyqd.core import BaseAction

class Action(BaseAction):
    """
    Add a new field to the dataframe, populated with a single value.
    """
    def __init__(self):
        self.name = "NEW"
        self.title = "New"
        self.description = "Create a new field and assign a set value."
        self.structure = ["value"]

    def transform(df, field_name, structure, **kwargs):
        """
        Add a new field to a dataframe and set its value to the default provided.

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
        df.loc[:, field_name] = structure[1]["value"]
        return df