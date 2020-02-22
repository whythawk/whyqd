from whyqd.core import BaseAction
import whyqd.common as _c

class Action(BaseAction):
    """
    Calculate the value of a field derived from the values of other fields. Requires a constraint
	indicating whether the fields should be ADD or SUB from the current total.

    .. note:: This is still very rudimentary. Enhancements should stick to basic `reverse Polish notation` arithmetic.
    """
    def __init__(self):
        self.name = "CALCULATE"
        self.title = "Calculate"
        self.description = "Derive a calculation from a list of fields. Each field must have a modifier, including the first (e.g. +A -B +C)."
        self.structure = ["modifier", "field"]

    @property
    def modifiers(self):
        """
        Describes the modifiers for calculations.

        Returns
        -------
        dict
            Dict representation of the modifiers.
        """
        modifiers = [
            {
                "name": "+",
                "title": "Add",
                "type": "modifier"
            },
            {
                "name": "-",
                "title": "Subtract",
                "type": "modifier"
            }
        ]
        return modifiers

    def transform(self, df, field_name, structure, **kwargs):
        """
        Calculate the value of a field derived from the values of other fields. Requires a constraint
	    indicating whether the fields should be ADD or SUB from the current total.

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
        term_set = len(self.structure)
        add_fields = [field["name"] for modifier, field in _c.chunks(structure, term_set)
                      if modifier["name"] == "+"]
        sub_fields = [field["name"] for modifier, field in _c.chunks(structure, term_set)
                      if modifier["name"] == "-"]
        for field in add_fields + sub_fields:
            df.loc[:, field] = df.loc[:, field].apply(lambda x: _c.parse_float(x))
        df.loc[:, field_name] = df[add_fields].abs().sum(axis=1) - df[sub_fields].abs().sum(axis=1)
        return df