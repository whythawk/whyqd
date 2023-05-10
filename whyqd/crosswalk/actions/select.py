from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

from whyqd.crosswalk.base import BaseSchemaAction
from whyqd.models import FieldModel

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseSchemaAction):
    """Use sparse data from a list of fields to populate a new field by iterating over a list of fields and selecting the
    next value in the list.

    !!! tip "Script template"
        ```python
        "SELECT > 'destination_field' < ['source_field', 'source_field', etc.]"
        ```

        Where order of `source_field` is important, each successive field in the list has priority over the ones before
        it (e.g. for columns A, B & C, values in C will have precedence over values in B and A). If there are nulls in
        A and B, but not B, then the returned value will be from B. If, however, there are values in A, B and C, then
        the returned value will be from C.

    !!! example
        ```python
        "SELECT > 'occupation_state_date' < ['Account Start date', 'Current Relief Award Start Date']"
        ```

        In this example, any dates in `Current Relief Award Start Date` will have precedence over `Account Start date`
        while nulls will be ignored, ensuring that `Account Start date` will be returned.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "SELECT"
        self.title = "Select"
        self.description = "Use sparse data from a list of fields to populate a new field. Order is important, each successive field in the list have priority over the ones before it (e.g. for columns A, B & C, values in C will have precedence over values in B and A)."
        self.structure = [FieldModel]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: list[FieldModel],
    ) -> pd.DataFrame:
        if destination.name not in df.columns:
            df[destination.name] = None
        for field in source:
            df[destination.name] = np.where(df[field.name].notnull(), df[field.name], df[destination.name])
        return df
