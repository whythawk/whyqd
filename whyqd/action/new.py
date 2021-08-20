from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING
import pandas as pd

from whyqd.base import BaseSchemaAction

if TYPE_CHECKING:
    from ..models import FieldModel


class Action(BaseSchemaAction):
    """
    Add a new field to the dataframe, populated with a single value.

    Script::

        "NEW > 'destination_field' < ['value']"

    Where `value` is a unique `string` value which will be assigned to the entire column. This is useful where data form
    part of a series and each wrangled dataset will be concatenated into a single larger table. This can function as
    a grouping identifier.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "NEW"
        self.title = "New"
        self.description = "Create a new field and assign a set value."
        self.structure = ["value"]

    def transform(self, df: pd.DataFrame, destination: FieldModel, _: Optional[Any] = None) -> pd.DataFrame:
        """
        Add a new field to a dataframe and set its value to the default provided.

        Slightly different. The destination FieldModel is part of the Schema, and the `default` in the `constraints`
        provides the necessary value. Useful when creating a data series column. Will usually be added automatically
        after review of the Schema.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        destination: FieldModel
            Destination column for the result of the Action.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        df.loc[:, destination.name] = destination.constraints.default.name
        return df
