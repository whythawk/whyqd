from __future__ import annotations
import modin.pandas as pd
import numpy as np
from typing import List, Dict, Union, TYPE_CHECKING

from whyqd.transform.base import BaseSchemaAction

if TYPE_CHECKING:
    from whyqd.metamodel.models import ColumnModel, ModifierModel, FieldModel, CategoryModel, CategoryActionModel


class Action(BaseSchemaAction):
    """
    Produce categories from terms or headers. There are three categorisation options:

                1. Term-data are categories derived from values in the data,
                2. Header-data are terms derived from the header name and boolean True for any value,
                3. "Boolean"-data, the category itself is True/False.

    Script::

        "CATEGORISE > 'destination_field' < [modifier 'source_column', modifier 'source_column', etc.]"

    Where a `-` modifier indicates that some or all values in the column are coerced to `boolean`, and `+` indicates
    that specific values in the column are to be assigned to a defined `schema` `category`. This ACTION requires that
    `values` in `columns` be ASSIGNED to the appropriate `schema` `category`::

        "ASSIGN_CATEGORY_BOOLEANS > 'destination_field'::bool < 'source_column'"

    or::

        "ASSIGN_CATEGORY_UNIQUES > 'destination_field'::'destination_category' < 'source_column'::['unique_source_term', 'unique_source_term', etc.]"

    .. note:: Categorisation requires that the destination `schema` `field` is assigned appropriate `category` `constraints`.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "CATEGORISE"
        self.title = "Categorise"
        self.description = "Apply categories to a list of columns. Each field must have a modifier, including the first (e.g. +A -B +C). '-' modifier indicates presence/absence of values as true/false for a specific term. '+' modifier indicates that the unique terms in the field must be matched to the unique terms defined in the schema. This is a two-step process, first requiring listing the columns effected, then applying the terms."
        self.structure = ["modifier", "field"]

    @property
    def modifiers(self) -> List[ModifierModel]:
        """
        Describes the modifiers for calculations.

        Returns
        -------
        list of ModifierModel
            ModifierModel representation of the modifiers.
        """
        return [
            {"name": "+", "title": "Uniques"},
            {"name": "-", "title": "Values"},
        ]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: List[Union[ColumnModel, ModifierModel]],
        assigned: List[
            Dict[str, Union[CategoryActionModel, FieldModel, CategoryModel, ColumnModel, List[CategoryModel]]]
        ],
    ) -> pd.DataFrame:
        """
        Produce categories from terms or headers. There are three categorisation options:

            1. Term-data are categories derived from values in the data,
            2. Header-data are terms derived from the header name and boolean True for any value,
            3. "Boolean"-data, the category itself is True/False. Default in a boolean is True.

        .. note:: Categorisation is a special case, requiring both method fields, and method categories, which it can do
        only if the `destination` is a schema field, which has the required term definitions.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        destination: FieldModel
            Destination FieldModel for the result of the Action.
        source: list of ColumnModel and / or ModifierModel
            List of source columns and modifiers for the action.
        assigned: list of dict
            Each dict has values for: Assignment ACTION, destination schema field, schema category, source data column,
            and a list of source data column category terms assigned to that schema category.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        # This is a complex algorith, and so there are LOTS of comments to explain each step.
        # 1. The source list terms are in sets of two: + or - modifier, field
        # The modifier defines one of two approaches:
        #   '+': The terms in the field are used to identify the schema category. This is used when the column values
        #        represent multiple terms.
        #   '-': Non-null terms indicate presence of a schema category. This is used when values represent a
        #        boolean True, and NaNs or voids represent False. The user must decide if zeros (0) are null or a value.
        # If the schema field type is 'array', then the destination category terms are lists.
        # If field type is 'boolean', then the default term is True.
        # The default category term is assigned for any null values.
        is_array = True if destination.type_field == "array" else False
        is_boolean = True if destination.type_field == "boolean" else False
        # Sort out boolean term names and defaults before they cause further pain ...
        if destination.constraints:
            # Boolean categories can only be True or False, but the user can set a default
            default = None if not destination.constraints.default else destination.constraints.default.name
        elif is_boolean:
            default = True
        # Get all the assigned Schema Categories
        destination_schema_categories = [assigned_category["category"].name for assigned_category in assigned]
        if is_boolean:
            # Can only be True/False, and we'll be resolving a text version of the names later, so ...
            destination_schema_categories = [str(c).lower() for c in destination_schema_categories]
        # Set the field according to the default
        # https://stackoverflow.com/a/31469249
        df[destination.name] = [[] for _ in range(len(df))] if is_array else default
        # Develop the terms and conditions to assess membership of a category
        # As per structure, requires sets of two terms: + or - modifier, field
        new_field = []
        term_set = len(self.structure)
        # Annotate before the loop https://stackoverflow.com/a/41641489/295606
        modifier: ModifierModel
        source_column: ColumnModel
        for modifier, source_column in self.core.chunks(lst=source, n=term_set):
            # https://docs.scipy.org/doc/numpy/reference/generated/numpy.select.html
            # Extract only the terms valid for this particular field
            # With list of action scripts::
            #     "ACTION > 'schema_field' < [modifier 'source_column1', modifier 'source_column2']"
            # for modifier, source_column in chunks[2, source_terms]:
            # GENERATE: np.selection(conditions, category_terms, default)
            # GENERATE CATEGORY TERMS
            # With list of category action assignment scripts::
            #     ["ASSIGN_CATEGORY_UNIQUES > 'schema_field'::'schema_category1' < 'source_column1'::['source_category_term1',etc.]",
            #      "ASSIGN_CATEGORY_UNIQUES > 'schema_field'::'schema_category2' < 'source_column1'::['source_category_term2',etc.]",
            #      "ASSIGN_CATEGORY_UNIQUES > 'schema_field'::'schema_category1' < 'source_column2'::['source_category_term3',etc.]"
            #      ...]
            category_terms = []
            # for schema_category in list of all schema_categories for this field
            for schema_category in destination_schema_categories:
                # for source_category_term in assigned source_categories from the list of all unique source terms in source_column
                for assigned_category in assigned:
                    # if this 'source_column' (from the looped list of all source_columns) == 'source_column'
                    if assigned_category["source"].name == source_column.name:
                        # Extend [schema_category for _source_category in source_categories]
                        # Creating a matrix for np.select where::
                        #     category_terms = [schema_category1, schema_category1, schema_category2, schema_category2, ...]
                        # Where the lengths of the two lists are identical, and the terms are allocated such that::
                        #     Len(category_terms) == len(source_categories)
                        category_terms.extend([schema_category for _ in assigned_category.get("assigned", [])])
            # From here, things depend on the modifier.
            if modifier.name == "+":
                conditions = self._get_unique_conditions(df=df, source=source_column, category_terms=category_terms, assigned=assigned)
            elif modifier.name == "-":
                conditions = self._get_boolean_conditions(df=df, source=source_column, category_terms=category_terms, assigned=assigned)
                if is_boolean:
                    # if len(category_terms) == 1 and 'false', do nothing; if 'true', invert;
                    # if len(category_terms) == 2, use 'false' only
                    if "true" in category_terms:
                        # We need to correct for the disaster of 'true'
                        invrt = dict(zip(category_terms, conditions))
                        if len(category_terms) == 1:
                            invrt["false"] = ~invrt["true"]
                        category_terms = [t for t in invrt.keys() if t != "true"]
                        conditions = [invrt["false"]]
            # Only two terms, True or False. Reset the dictionary names
            if is_boolean and "false" in category_terms:
                category_terms = [False if t == "false" else t for t in category_terms]
            if not is_array:
                # Set the field category_terms immediately for membership, note, if no data defaults to current
                # i.e. this is equivalent to order, but with category data
                df[destination.name] = np.select(conditions, category_terms, default=df[destination.name])
            else:
                if category_terms and conditions:
                    new_field.append(np.select(conditions, category_terms, default="none").tolist())
        # If a list of terms, organise the nested lists and then set the new field
        if is_array:
            # Sorted to avoid hashing errors later ...
            new_field = [sorted(list(set(x))) for x in zip(*new_field)]
            for n in new_field:
                if "none" in n:
                    n.remove("none")
            if new_field:
                df[destination.name] = new_field
        return df

    ###################################################################################################
    ### SUPPORT UTILITIES
    ###################################################################################################

    def _get_unique_conditions(
        self,
        *,
        df: pd.DataFrame,
        source: ColumnModel,
        category_terms: List[str],
        assigned: List[
            Dict[str, Union[CategoryActionModel, FieldModel, CategoryModel, ColumnModel, List[CategoryModel]]]
        ],
    ) -> List[pd.Series]:
        """Return a list of pandas Series of boolean results to support an np.select conditions term. Used when
        `modifier.name == '+'`.

        Generate a matrix of len(category_terms) arrays by len(rows) of the source dataframe where they correspond
        as follows::

            [schema_category1, schema_category1, schema_category2, schema_category2, ...]
            [[source_cat_t1], [source_cat_t1], [source_cat_t1], [source_cat_t1], ...]

        Where each value is tested for inclusion in the assigned categories for that schema category::

            [[True], [False], [False], ...]

        Where only one should be `True` (although, I suppose, that's up to the user if a source category belongs to more
        than one schema category), and all `False` results in 'default' assignment.

        Each category assignment action comes back as a dictionary::

            {
                "action": ACTION,
                "destination": Schema_field,
                "category": Schema_category (from constraints),
                "source": Source_column,
                "assigned": ['source_category_term1',...],
                "unassigned": ['source_category_term2',...],
            }

        These are in the `assigned` list.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        source: ColumnModel
            Source data column.
        category_terms: list of str
            The generated category terms forming the test and length for the matrix columns.
        assigned: list of dict
            Each dict has values for: Assignment ACTION, destination schema field, schema category, source data column,
            and a list of source data column category terms assigned to that schema category.

        Returns
        -------
        List of pd.Series
            Containing the implementation of the Action
        """
        df = df.copy()
        return [
            # Test values in each row of source_column are 'in'
            # Read the following sort-of from the bottom up (numbered)
            df[source.name].isin(
                [
                    # 6. Adding validated source_category_terms to the membership list to 'isin' testing.
                    source_category_term.name
                    for source_category_groups in [
                        # 4. include the list of source_category_terms
                        source_category_assignment["assigned"]
                        # 2. for each source_category_assignment from the assigned source_categories
                        # for this source_column
                        # i.e. "ASSIGN_CATEGORY_UNIQUES > 'schema_field'::'schema_category1' < 'source_column2'::['source_category_term3',etc.]"
                        for source_category_assignment in assigned
                        # 3. if the schema_category the source_category_term is assigned is
                        # the same as the schema_category
                        if source_category_assignment["category"].name == schema_category
                    ]
                    # 5. for each source_category_term
                    for source_category_term in source_category_groups
                ]
            )
            # 1. for each (including duplicates) category in the list of category_terms
            # Generates each column in the constrains matrix.
            for schema_category in category_terms
        ]

    def _get_boolean_conditions(
        self,
        *,
        df: pd.DataFrame,
        source: ColumnModel,
        category_terms: List[str],
        assigned: List[
            Dict[str, Union[CategoryActionModel, FieldModel, CategoryModel, ColumnModel, List[CategoryModel]]]
        ],
    ) -> List[pd.Series]:
        """Return a list of pandas Series of boolean results to support an np.select conditions term. Used when
        `modifier.name == '-'`.

        Each category assignment action comes back as a dictionary::

            {
                "action": ACTION,
                "destination": Schema_field,
                "category": Schema_category (from constraints),
                "source": Source_column,
                "null_zero": bool,
            }

        These are in the `assigned` list. Unlike the `unique` assignment, the values themselves are immaterial,
        however, it is important to know if Zeros should be null. *Default is that zeros are null.*

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        source: ColumnModel
            Source data column.
        category_terms: list of str
            The generated category terms forming the test and length for the matrix columns.
        assigned: list of dict
            Each dict has values for: Assignment ACTION, destination schema field, schema category, source data column,
            and a list of source data column category terms assigned to that schema category.

        Returns
        -------
        List of pd.Series
            Containing the implementation of the Action
        """
        # Modifier is -, so can make certain assumptions:
        # - Terms are categorised as True or False, so choices are only True or False
        # - However, all terms allocated to 'true' will fail (since True on default is True no matter)
        # - User may return both True / False or only one
        # - If both True and False, keep False. If True, convert the True to False
        # Ensure any numerical zeros are nan'ed +
        df = df.copy()
        if df[source.name].dtype in ["float64", "int64"]:
            df[source.name] = df[source.name].replace({0: np.nan})
        if df[source.name].dtype in ["datetime64[ns]"]:
            df[source.name] = df[source.name].apply(self.wrangle.parse_dates_coerced)
        return [
            pd.notnull(df[source.name]) if schema_category == "false" else ~pd.notnull(df[source.name])
            for schema_category in category_terms
        ]
