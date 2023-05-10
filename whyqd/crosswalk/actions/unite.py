from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseMorphAction
from whyqd.models import FieldModel

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """
    Unite a list of columns with a selected `string` (i.e. concatenating text in multiple fields).

    !!! tip "Script template"
        ```python
        "UNITE > 'destination_field' < 'by'::['source_field', 'source_field', etc.]"
        ```

        Or:
        ```python
        "UNITE > 'destination_field' < ['source_field', 'source_field', etc.]"
        ```

        Where `'by'` can be any `string` with one **MAJOR** caveat. Since `::` is used in the query, you **cannot** use it
        for joining. By default this will be `', '` and so, alternatively, you can leave the `'by'` term out.

    !!! example
        ```python
        "UNITE > 'reference' < ', '::['Reference 1', 'Reference 2', 'Reference 3']"
        ```
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "UNITE"
        self.title = "Unite"
        self.description = "Unite values in different fields to create a new concatenated value. Each value will be converted to a string (e.g. A: 'Word 1' B: 'Word 2' => 'Word 1 Word 2')."
        self.structure = ["fields"]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel | list[FieldModel],
        source: list[FieldModel],
        source_param: str | None = None,
        rows: None = None,
        destination_param: None = None,
    ) -> pd.DataFrame:
        if isinstance(destination, list):
            destination = destination[0]
        if source_param is None:
            source_param = ", "
        fields = [field.name for field in source]
        # https://stackoverflow.com/a/45976632
        df[destination.name] = df[fields].apply(
            lambda x: "" if x.isnull().all() else source_param.join(x.dropna().astype(str)).strip(), axis=1
        )
        return df
