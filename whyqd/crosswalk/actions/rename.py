from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseSchemaAction
from whyqd.models import FieldModel

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseSchemaAction):
    """
    Rename the source field to the destination field.

    !!! tip "Script template"
        ```python
        "RENAME > 'destination_field' < ['source_field']"
        ```

        Where only the first `source_field` will be used.

    This - ideally - is the most commonly-used script action as many source and destination fields have the same intention
    but different names.

    !!! example
        ```python
        "RENAME > 'occupant_name' < ['Primary Liable party name']"
        ```
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "RENAME"
        self.title = "Rename"
        self.description = (
            "Rename an existing field to conform to a schema name. Only valid where a single field is provided."
        )
        self.structure = [FieldModel]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: list[FieldModel],
    ) -> pd.DataFrame:
        # Rename, note, can only be one field if a rename ...
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.rename.html
        # {'from': 'too'}
        return df.rename(index=str, columns={source[0].name: destination.name})
