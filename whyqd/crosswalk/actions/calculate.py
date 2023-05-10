from __future__ import annotations
import modin.pandas as pd
import numpy as np

from whyqd.crosswalk.base import BaseSchemaAction
from whyqd.models import ModifierModel, FieldModel


class Action(BaseSchemaAction):
    """Calculate the value of a field derived from the values of other fields. Requires a `MODIFIER` indicating whether
    the fields should be added or subtracted from the current total.

    !!! tip "Script template"
        ```python
        "CALCULATE > 'destination_field' < [modifier 'source_field', modifier 'source_field', etc]"
        ```

        Where the `modifier` is either of `+` or `-`. If you want to change the sign of the values in a column,
        *before* further arithmatic, you'll need to do this sort of script:

        ```python
        "CALCULATE > 'destination_field' < [modifier 'source_field', modifier CALCULATE < [- 'source_field']"
        ```

    !!! example
        ```python
        "CALCULATE > 'total' < [+ 'income', - 'expenses']"
        ```

    !!! warning
        This is still very rudimentary. Enhancements should stick to basic `reverse Polish notation` arithmetic.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "CALCULATE"
        self.title = "Calculate"
        self.description = "Derive a calculation from a list of fields. Each field must have a modifier, including the first (e.g. +A -B +C)."
        self.structure = [ModifierModel, FieldModel]

    @property
    def modifiers(self) -> list[ModifierModel]:
        return [
            ModifierModel(**{"name": "+", "title": "Add"}),
            ModifierModel(**{"name": "-", "title": "Subtract"}),
        ]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: list[FieldModel | ModifierModel],
    ) -> pd.DataFrame:
        term_set = len(self.structure)
        add_fields = [
            field.name for modifier, field in self.core.chunks(lst=source, n=term_set) if modifier.name == "+"
        ]
        sub_fields = [
            field.name for modifier, field in self.core.chunks(lst=source, n=term_set) if modifier.name == "-"
        ]
        for field in add_fields + sub_fields:
            df[field] = df[field].apply(self.reader.parse_float)
        # Need to maintain NaNs ... default is to treat NaNs as zeros, so even a sum of two NaNs is zero
        # If we don't know, we don't know ... but ... if a sum is mixed, then ignore the NaNs
        _add = df[add_fields].sum(min_count=1, axis=1).array
        _sub = df[sub_fields].sum(min_count=1, axis=1).array
        # Need to use 'logical_and' since comparing NaNs is a disaster
        df[destination.name] = np.where(
            np.logical_and(np.isnan(_add), np.isnan(_sub)), np.nan, np.nan_to_num(_add) - np.nan_to_num(_sub)
        )
        return df
