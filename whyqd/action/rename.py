from __future__ import annotations
from typing import List, Union, TYPE_CHECKING

# import pandas as pd

from whyqd.base import BaseSchemaAction

if TYPE_CHECKING:
    import modin.pandas as pd
    from ..models import FieldModel, ColumnModel


class Action(BaseSchemaAction):
    """
    Rename the field to the schema field.

    Script::

        "RENAME > 'destination_field' < ['source_column']"

    Where only the first `source_column` will be used.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "RENAME"
        self.title = "Rename"
        self.description = (
            "Rename an existing field to conform to a schema name. Only valid where a single field is provided."
        )
        self.structure = ["field"]

    def transform(
        self,
        df: pd.DataFrame,
        destination: Union[FieldModel, ColumnModel],
        source: List[ColumnModel],
    ) -> pd.DataFrame:
        """
        Rename the field to the schema field.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        destination: FieldModel or ColumnModel, default None
            Destination column for the result of the Action.
        source: list of ColumnModel
            List of source columns for the action. If there are more than one, only the first will be
            used.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        # Rename, note, can only be one field if a rename ...
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rename.html
        # {'from': 'too'}
        return df.rename(index=str, columns={source[0].name: destination.name})
