from __future__ import annotations
from typing import List, Union, TYPE_CHECKING
import modin.pandas as pd
import numpy as np

from whyqd.transform.base import BaseSchemaAction

if TYPE_CHECKING:
    from whyqd.metamodel.models import FieldModel, ColumnModel, ModifierModel


class Action(BaseSchemaAction):
    """Calculate the value of a field derived from the values of other fields. Requires a constraint
       indicating whether the fields should be ADD or SUB from the current total.

    .. note:: This is still very rudimentary. Enhancements should stick to basic `reverse Polish notation` arithmetic.

    Script::

        "CALCULATE > 'destination_field' < [modifier 'source_column', modifier 'source_column', etc]"

    Where the `modifier` is either of `+` or `-`. If you want to change the sign of the values in a column, *before*
    further arithmatic, you'll need to do this sort of script::

        "CALCULATE > 'destination_field' < [modifier 'source_column', modifier CALCULATE < [- 'source_column']"
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "CALCULATE"
        self.title = "Calculate"
        self.description = "Derive a calculation from a list of fields. Each field must have a modifier, including the first (e.g. +A -B +C)."
        self.structure = ["modifier", "field"]

    @property
    def modifiers(self) -> List[ModifierModel]:
        """
        Describes the modifiers for calculations.

        Returns
        -------
        List of ModifierModel
            ModifierModel representation of the modifiers.
        """
        return [
            {"name": "+", "title": "Add"},
            {"name": "-", "title": "Subtract"},
        ]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: Union[FieldModel, ColumnModel],
        source: List[Union[ColumnModel, ModifierModel]],
    ) -> pd.DataFrame:
        """Calculate the value of a field derived from the values of other fields. Requires a constraint
           indicating whether the fields should be ADD or SUB from the current total.

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
        term_set = len(self.structure)
        add_fields = [field.name for modifier, field in self.core.chunks(lst=source, n=term_set) if modifier.name == "+"]
        sub_fields = [field.name for modifier, field in self.core.chunks(lst=source, n=term_set) if modifier.name == "-"]
        for field in add_fields + sub_fields:
            df[field] = df[field].apply(self.wrangle.parse_float)
        # Need to maintain NaNs ... default is to treat NaNs as zeros, so even a sum of two NaNs is zero
        # If we don't know, we don't know ... but ... if a sum is mixed, then ignore the NaNs
        _add = df[add_fields].sum(min_count=1, axis=1).array
        _sub = df[sub_fields].sum(min_count=1, axis=1).array
        # Need to use 'logical_and' since comparing NaNs is a disaster
        df[destination.name] = np.where(
            np.logical_and(np.isnan(_add), np.isnan(_sub)), np.nan, np.nan_to_num(_add) - np.nan_to_num(_sub)
        )
        return df
