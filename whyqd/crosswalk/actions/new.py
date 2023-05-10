from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseSchemaAction

if TYPE_CHECKING:
    import modin.pandas as pd
    from whyqd.models import FieldModel


class Action(BaseSchemaAction):
    """
    Add a new field to the dataframe, populated with a single value.

    !!! tip "Script template"
        ```python
        "NEW > 'destination_field' < ['value']"
        ```

        Where `value` is a unique `string` value which will be assigned to the entire column. This is useful where data form
        part of a series and each transformed dataset will be concatenated into a single larger table. This can function as
        a grouping identifier.

        **NOTE:** the `value` will be assigned as the default term for the `destination_field` FieldModel is part of the
        Schema, and the `default` in the `constraints`. Useful when creating a data series column. Will usually be added
        automatically after parsing of the scripts.

    !!! example
        ```python
        "NEW > 'la_code' < ['E06000044']"
        ```
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "NEW"
        self.title = "New"
        self.description = "Create a new field and assign a set value."
        self.structure = ["value"]

    def transform(self, *, df: pd.DataFrame, destination: FieldModel) -> pd.DataFrame:
        df[destination.name] = destination.constraints.default.name
        return df
