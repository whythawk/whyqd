from __future__ import annotations
from typing import TYPE_CHECKING
import modin.pandas as pd
import numpy as np

from whyqd.parsers import DataSourceParser, ScriptParser

if TYPE_CHECKING:
    from whyqd.models import CategoryActionModel, CategoryModel, FieldModel


class BaseCategoryAction:
    """Category Actions are support utilities for CATEGORY actions. These inherit from this base class which describes
    the core functions and methodology for this support Action.

    Actions should redefine `name`, `title`, `description`, and `structure`.

    `structure` is defined by these parameters:

    * `boolean`: terms will be unique.
    * `unique`: the specific columns effected by the morph, a `list` of `ColumnModel` or, rarely, `FieldModel`.

    A standard script is::

        "ACTION > 'destination_column::destination_category' < ['unique_term', 'unique_term', etc.]"

    Where the structure of the source array is defined by the ACTION.
    """

    def __init__(self) -> None:
        self.reader = DataSourceParser()
        self.parser = ScriptParser()
        self.name = ""
        self.title = ""
        self.description = ""
        self.structure = []

    @property
    def settings(self) -> CategoryActionModel:
        """
        Returns the CategoryActionModel representation of the Action.

        Returns
        -------
        CategoryActionModel
            CategoryActionModel representation of an Action.
        """
        from whyqd.models import CategoryActionModel

        action_settings = {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "structure": self.structure,
        }
        return CategoryActionModel(**action_settings)

    def parse(self, *, script: str) -> dict[str, str]:
        """Base parser for the CategoryAction script. Produces required terms and validates against this
        CategoryAction's structure requirements.

        Script is of the form::

            "ACTION > 'destination_column'::term < 'source_column'::[term]"

        Which is inherited as::

            {
                "action": ACTION,
                "destination": 'destination_column',
                "category": term,
                "source": 'source_column',
                "source_category": [term]
            }

        Parameters
        ----------
        script: str
            An action script.

        Raises
        ------
        ValueError for any parsing errors.

        Returns
        -------
        dict
            Parsed dictionary of validated split strings for further processing.
        """
        parsed = {}
        # Get unique assignment terms
        root = self.parser.get_split_terms(script=script, by="<")
        if len(root) != 2:
            raise ValueError(f"Category action script has no source terms ({script}).")
        # Extract source terms
        source_terms = self.parser.get_split_terms(script=root[1], by="::")
        parsed["source"] = source_terms[0]
        if len(source_terms) == 2:
            parsed["source_category"] = source_terms[1]
        root = self.parser.get_split_terms(script=root[0], by=">")
        # Extract destination terms
        if len(root) != 2:
            raise ValueError(f"Category action script has no destination terms ({script}).")
        destination_terms = self.parser.get_split_terms(script=root[1], by="::")
        if len(destination_terms) != 2:
            raise ValueError(f"Category action script has no destination category term ({script}).")
        parsed["destination"] = destination_terms[0]
        parsed["category"] = destination_terms[1]
        # And the action term
        parsed["action"] = root[0]
        return parsed

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: FieldModel,
        category: CategoryModel = None,
        assigned: list[CategoryModel] | list[int] | None = None,
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
        assigned: list of dict or list of int
            Each dict has values for: Assignment ACTION, destination schema field, schema category, source data column,
            and a list of source data column category terms assigned to that schema category.
            Can also assign specific row values to a category for pivots.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        # Defaults
        default = None
        if destination.constraints and destination.constraints.default:
            default = destination.constraints.default.name
        if destination.name in df.columns and destination.dtype != "array":
            default = df[destination.name]
        # Conditions
        conditions = df[source.name]
        if len(assigned) == 1 and isinstance(assigned[0].name, bool):
            # Conditions are contingent on values in a column
            # If assigned is `True`, then values are `True`, else values are `False` and nulls are `True`
            if source.dtype and source.dtype not in ["string", "object"]:
                conditions = self.reader.coerce_column_to_dtype(column=df[source.name], coerce=source.dtype)
                if conditions.dtype in ["float64", "int64", "Float64", "Int64"]:
                    conditions = conditions.replace({0: np.nan})
                if conditions.dtype in ["datetime64[ns]"]:
                    conditions = conditions.apply(self.reader.parse_dates_coerced)
            if assigned[0].name:
                # i.e. values are assigned True
                conditions = pd.Series([not (pd.isnull(x) or not x) for x in conditions.tolist()])
            else:
                # i.e. values are assigned False
                conditions = pd.Series([(pd.isnull(x) or not x) for x in conditions.tolist()])
        else:
            # The conditional column values are categorised directly
            conditions = conditions.isin([c.name for c in assigned])
        # Array-based categorisation adds additional terms to existing columns
        if destination.dtype == "array":
            new_column = []
            if destination.name in df.columns:
                new_column = [df[destination.name].tolist()]
            if destination.dtype == "array" and not conditions.empty:
                new_column.append(
                    [
                        [x] if not isinstance(x, list) else x
                        for x in np.where(conditions, category.name, default).tolist()
                    ]
                )
            # Sorted to avoid hashing errors later ...
            if len(new_column) > 1:
                # Moving sorting to the hashing function so we can maintain None's for ordered lists
                # Permits reconstruction of datasets using array transformations
                # https://stackoverflow.com/a/18411610
                # new_column = [sorted(list(set([c for clist in x for c in clist])), key=lambda x: (x is None, x)) for x in zip(*new_column)]
                new_column = [[c for clist in x for c in clist] for x in zip(*new_column)]
            else:
                new_column = [[x] if not isinstance(x, list) else x for x in new_column[0]]
            # for n in new_column:
            #     if None in n:
            #         n.remove(None)
            df[destination.name] = new_column
        else:
            df[destination.name] = np.where(conditions, category.name, default)
        return df
