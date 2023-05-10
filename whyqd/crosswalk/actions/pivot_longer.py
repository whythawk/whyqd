from __future__ import annotations
import modin.pandas as pd

from whyqd.crosswalk.base import BaseSchemaAction
from whyqd.models import FieldModel


class Action(BaseSchemaAction):
    """Pivot a list of columns to create a new long table format.

    !!! tip "Script template"
        ```python
        "PIVOT_LONGER > ['name_field', 'value_field'] < ['source_field', 'source_field', etc.]"
        ```

        Will assign to the destination fields as:

        - name_field: containing the original source field names, as appropriate,
        - value_field: containing the original values corresponding to the original source fields.

    !!! example
        ```python
        "PIVOT_LONGER > ['year', 'values'] < ['1990', '1991', '1992', '1993']"
        ```
    """

    def __init__(self):
        super().__init__()
        self.name = "PIVOT_LONGER"
        self.title = "Pivot longer"
        self.description = "Transform a DataFrame from wide to long format."
        self.structure = [FieldModel]

    def validate(self, *, destination: list[FieldModel], source: list) -> bool:
        if not isinstance(destination, list) and len(destination) == 2:
            raise ValueError(f"Action source script does not conform to required structure. ({destination})")
        return super().validate(destination=destination, source=source)

    def transform(self, *, df: pd.DataFrame, destination: list[FieldModel], source: list[FieldModel]) -> pd.DataFrame:
        columns = [c.name for c in source]
        id_columns = list(set(df.columns.values.tolist()).difference(set(columns)))
        name_field, value_name = destination[0].name, destination[1].name
        # https://pandas.pydata.org/docs/reference/api/pandas.melt.html
        return pd.melt(df, id_vars=id_columns, value_vars=columns, var_name=name_field, value_name=value_name)
