import pandas as pd
import numpy as np
import uuid

from whyqd.core import BaseAction
from whyqd.core import common as _c

class Action(BaseAction):
    """
    Produce categories from terms or headers. There are three categorisation options:

		1. Term-data are categories derived from values in the data,
		2. Header-data are terms derived from the header name and boolean True for any value,
		3. "Boolean"-data, the category itself is True/False. Default in a boolean is True.

	Categorisation is a special case, requiring both method fields, and method categories, along
	with the schema field_name field to lookup the required term definitions.
    """
    def __init__(self):
        self.name = "CATEGORISE"
        self.title = "Categorise"
        self.description = "Apply categories to a list of columns. Each field must have a modifier, including the first (e.g. +A -B +C). '-' modifier indicates presence/absence of values as true/false for a specific term. '+' modifier indicates that the unique terms in the field must be matched to the unique terms defined in the schema. This is a two-step process, first requiring listing the columns effected, then applying the terms."
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
                "title": "Uniques",
                "type": "modifier"
            },
            {
                "name": "-",
                "title": "Values",
                "type": "modifier"
            }
        ]
        return modifiers

    def transform(self, df, field_name, structure, **kwargs):
        """
        Produce categories from terms or headers. There are three categorisation options:

            1. Term-data are categories derived from values in the data,
            2. Header-data are terms derived from the header name and boolean True for any value,
            3. "Boolean"-data, the category itself is True/False. Default in a boolean is True.

        Categorisation is a special case, requiring both method fields, and method categories, along
        with the schema field_name field to lookup the required term definitions.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        field_name: str
            Name of the target schema field
        structure: list
            List of fields with restructuring action defined by term 0 (i.e. `this` action)
        **kwargs: 
            Requires `category=` & `field_type=` in kwargs, with the appropriate definition.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        # Fields are in sets of 2 terms: + or -, field
        # The modifier defines one of two approaches:
        #   '+': The terms in the field are used to identify the schema category
        #   '-': Non-null terms indicate presence of a schema category
        # If field type is 'array', then the destination terms are lists;
        # If field type is 'boolean', then the default term is True;
        is_array = True if kwargs["field_type"] == "array" else False
        is_boolean = True if kwargs["field_type"] == "boolean" else False
        # Sort out boolean term names before they cause further pain, correct later ...
        if is_boolean:
            for c in kwargs["category"]:
                if c["name"]: c["name"] = "true"
                else: c["name"] = "false"
        default = "None" if is_array else is_boolean
        # Set the field according to the default
        #https://stackoverflow.com/a/31469249
        df[field_name] = [[] for _ in range(len(df))] if is_array else default
        # Develop the terms and conditions to assess membership of a category
        # Requires sets of 2 terms: + or -, field
        new_field = []
        term_set = len(self.structure)
        all_terms = [c["name"] for c in kwargs["category"]]
        # Any fields modified below must be restored: (tmp_column, original_column)
        modified_fields = []
        for modifier, field in _c.chunks(structure, term_set):
            # https://docs.scipy.org/doc/numpy/reference/generated/numpy.select.html
            # Extract only the terms valid for this particular field
            terms = []
            for field_term in all_terms:
                for f in kwargs["category"]:
                    if f["name"] == field_term:
                        for c in f["category_input"]:
                            if c["column"] == field["name"]:
                                terms.extend([field_term for t in c["terms"]])
                        break
            if modifier["name"] == "+":
                conditions = [df[field["name"]].isin([t for subterms in
                                                    [item["terms"] for category_input in kwargs["category"]
                                                    for item in category_input["category_input"]
                                                    if category_input["name"] == field_term]
                                                    for t in subterms])
                            for field_term in terms]
            else:
                # Modifier is -, so can make certain assumptions
                # - Terms are categorised as True or False, so choices are only True or False
                # - However, all terms allocated to 'true' will fail (since True on default is True no matter)
                # - User may return both True / False or only one
                # - If both True and False, keep False. If True, convert the True to False
                # Create temporary column to preserve data
                if df[field["name"]].dtype in ["float64", "int64", "datetime64[ns]"]:
                    tmp = "tmp_" + str(uuid.uuid4())
                    modified_fields.append((tmp, field["name"]))
                    df[tmp] = df[field["name"]].copy()
                # Ensure any numerical zeros are nan'ed +
                if df[field["name"]].dtype in ["float64", "int64"]:
                    df[field["name"]] = df[field["name"]].replace({0:np.nan, 0.0:np.nan})
                if df[field["name"]].dtype in ["datetime64[ns]"]:
                    df.loc[:, field["name"]] = df.loc[:, field["name"]].apply(lambda x: pd.to_datetime(_c.parse_dates(x),
                                                                                                    errors="coerce"))
                conditions = [pd.notnull(df[field["name"]])
                            if kwargs["category"]["fields"][field_term]["fields"][0]["name"] else
                            ~pd.notnull(df[field["name"]])
                            for field_term in terms]
            if is_boolean and modifier["name"] == "-":
                # if len(terms) == 1 and 'false', do nothing; if 'true', invert;
                # if len(terms) == 2, use 'false' only
                if "true" in terms:
                    # We need to correct for the disaster of 'true'
                    invrt = dict(zip(terms, conditions))
                    if len(terms) == 1:
                        invrt["false"] = ~invrt["true"]
                    terms = [t for t in invrt.keys() if t != "true"]
                    conditions = [invrt["false"]]
            # Only two terms, True or False. Reset the dictionary names
            if is_boolean and "false" in terms:
                terms = [False if t == "false" else t for t in terms]
            if not is_array:
                # Set the field terms immediately for membership, note, if no data defaults to current
                # i.e. this is equivalent to order, but with category data
                df[field_name] = np.select(conditions, terms, default=df[field_name])
            else:
                if terms and conditions:
                    new_field.append(np.select(conditions, terms, default="none").tolist())
        # If a list of terms, organise the nested lists and then set the new field
        if is_array:
            # Sorted to avoid hashing errors later ...
            new_field = [sorted(list(set(x))) for x in zip(*new_field)]
            for n in new_field:
                if "none" in n: n.remove("none")
            if new_field:
                df[field_name] = new_field
        # Finally, fix the artifact columns introduced in the dataframe in case these are used elsewhere
        for tmp, original in modified_fields:
            df[original] = df[tmp].copy()
            del df[tmp]
        return df