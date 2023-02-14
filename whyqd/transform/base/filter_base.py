from __future__ import annotations
from typing import List, Union, Optional, Dict, TYPE_CHECKING

# import pandas as pd
from datetime import date

if TYPE_CHECKING:
    import modin.pandas as pd
    from whyqd.metamodel.models import FilterActionModel, FieldModel, ColumnModel


class BaseFilterAction:
    """Filter ACTIONS act to filter a table by a date column, while preserving information referenced in specific
    columns.

    Actions should redefine `name`, `title`, `description`, and `structure`. There is no transform function.

    `structure` is defined by these parameters:

    * `column`: a specific column for grouped-by filtering, can be `ColumnModel` or `FieldModel`.
    * `date`: a specific date reference, in ISO `YYYY-MM-DD` format. Times are not filtered and would need to be
        added to this feature.

    A standard script is::

        "FILTER_LATEST > 'filter_column' < 'source_column'"
    """

    def __init__(self) -> None:
        self.name = ""
        self.title = ""
        self.description = ""
        self.structure = None

    @property
    def settings(self) -> FilterActionModel:
        """
        Returns the FilterActionModel representation of the Action.

        Returns
        -------
        FilterActionModel
            FilterActionModel representation of an Action.
        """
        from whyqd.metamodel.models import FilterActionModel

        action_settings = {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "structure": self.structure,
        }
        return FilterActionModel(**action_settings)

    def parse(self, *, script: str) -> Dict[str, Union[str, List[str]]]:
        """Base parser for the FilterAction script. Produces required terms and validates against this
        FilterAction's structure requirements.

        Script is of the form::

            "FILTER_LATEST > 'filter_column' < 'source_column'"

        Which is inherited as::

            {
                "action": ACTION,
                "filter": 'filter_column',
                "date": date,
                "column": 'source_column'
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
        from whyqd.transform.parsers import ParserScript

        parser = ParserScript()
        column = None
        date_term = None
        filter_column = None
        # Get unique assignment terms
        root = parser.get_split_terms(script=script, by="<")
        # All column terms are optional ... if the user wants to filter everything by a specific date column,
        # that's fine.
        if len(root) == 2:
            # Extract column
            if "column" not in self.structure:
                raise ValueError(f"Filter action script has no grouped by column filter terms ({script}).")
            column = root[1]
        root = parser.get_split_terms(script=root[0], by=">")
        # Extract filter_column terms
        if len(root) != 2:
            raise ValueError(f"Filter action script has no destination terms ({script}).")
        filter_terms = parser.get_split_terms(script=root[1], by="::")
        if len(filter_terms) != 2 and "date" in self.structure:
            raise ValueError(f"Filter action script has no reference `date` term ({script}).")
        filter_column = filter_terms[0]
        if len(filter_terms) == 2:
            date_term = filter_terms[1]
        return {"action": root[0], "filter": filter_column, "date": date_term, "column": column}

    def transform(
        self,
        *,
        df: pd.DataFrame,
        filter_column: Union[FieldModel, ColumnModel],
        column: Optional[Union[FieldModel, ColumnModel]] = None,
        date_term: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Perform a transformation. This function must be overridden by child Actions and describe a unique
        new method.

        .. warning:: Assumes that is a valid call. Will raise exceptions from inside Pandas if not.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        filter_column: FieldModel or ColumnModel
            A date-field column to use to filter the table. Column values will be coerced to date-type.
        column: FieldModel or ColumnModel, default None
            A column which defines the groups from which to extract the latest row.
        date_term: date, default None
            A specific date for filtering.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        return df
