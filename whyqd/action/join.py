from whyqd.core import BaseAction

class Action(BaseAction):
    """
    Join a list of columns together with a space (i.e. concatenating text in multiple fields).
    """
    def __init__(self):
        self.name = "JOIN"
        self.title = "Join"
        self.description = "Join values in different fields to create a new concatenated value. Each value will be converted to a string (e.g. A: 'Word 1' B: 'Word 2' => 'Word 1 Word 2')."
        self.structure = ["field"]

    def transform(df, field_name, structure, **kwargs):
        """
        Join a list of columns together with a space (i.e. concatenating text in multiple fields).

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
        # https://stackoverflow.com/a/45976632
        df.loc[:, field_name] = df.loc[:, fields].apply(lambda x: "" if x.isnull().all() else
                                                                " ".join(x.dropna().astype(str)).strip(),
                                                        axis=1)
        return df