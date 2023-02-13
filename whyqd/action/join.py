from __future__ import annotations
from typing import List, Union, TYPE_CHECKING

# import pandas as pd

from whyqd.base import BaseSchemaAction

if TYPE_CHECKING:
    import modin.pandas as pd
    from ..models import ColumnModel, FieldModel


class Action(BaseSchemaAction):
    """
    Join a list of columns together with a space (i.e. concatenating text in multiple fields).

    Script::

        "JOIN > 'destination_field' < ['source_column', 'source_column', etc.]"

    Values in each column row will be joined with `, `.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "JOIN"
        self.title = "Join"
        self.description = "Join values in different fields to create a new concatenated value. Each value will be converted to a string (e.g. A: 'Word 1' B: 'Word 2' => 'Word 1 Word 2')."
        self.structure = ["field"]

    def transform(
        self,
        df: pd.DataFrame,
        destination: Union[FieldModel, ColumnModel],
        source: List[ColumnModel],
    ) -> pd.DataFrame:
        """
        Join a list of columns together with a space (i.e. concatenating text in multiple fields).

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        destination: FieldModel or ColumnModel, default None
            Destination column for the result of the Action.
        source: list of ColumnModel and / or ModifierModel
            List of source columns and modifiers for the action.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        fields = [field.name for field in source]
        # https://stackoverflow.com/a/45976632
        df[destination.name] = df[fields].apply(
            lambda x: "" if x.isnull().all() else ", ".join(x.dropna().astype(str)).strip(), axis=1
        )
        return df
