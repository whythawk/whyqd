from __future__ import annotations
from typing import List, Union, TYPE_CHECKING

# import pandas as pd
import numpy as np

from whyqd.base import BaseSchemaAction

if TYPE_CHECKING:
    import modin.pandas as pd
    from ..models import FieldModel, ColumnModel


class Action(BaseSchemaAction):
    """
    Create a new field by iterating over a list of fields and picking the next value in the list.

    Script::

        "ORDER > 'destination_field' < ['source_column', 'source_column', etc.]"

    Where order of `source_column` is important, each successive column in the list has priority over the ones before
    it (e.g. for columns A, B & C, values in C will have precedence over values in B and A).
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "ORDER"
        self.title = "Order"
        self.description = "Use sparse data from a list of fields to populate a new field. Order is important, each successive field in the list have priority over the ones before it (e.g. for columns A, B & C, values in C will have precedence over values in B and A)."
        self.structure = ["field"]

    def transform(
        self,
        df: pd.DataFrame,
        destination: Union[FieldModel, ColumnModel],
        source: List[ColumnModel],
    ) -> pd.DataFrame:
        """
        Create a new field by iterating over a list of fields and picking the next value in the list.

        Parameters
        ----------
        df: DataFrame
            Working data to be transformed
        destination: FieldModel
            Destination FieldModel for the result of the Action. Must have category fields or will raise ValueError.
        source: list of ColumnModel
            List of source columns for the action.

        Returns
        -------
        Dataframe
            Containing the implementation of the Action
        """
        if destination.name not in df.columns:
            df[destination.name] = None
        for field in source:
            df[destination.name] = np.where(df[field.name].notnull(), df[field.name], df[destination.name])
        return df
