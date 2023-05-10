from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """Remove all duplicated rows from a DataFrame.

    !!! tip "Script template"
        ```python
        "DEDUPE"
        ```
    """

    def __init__(self) -> None:
        self.name = "DEDUPE"
        self.title = "Deduplicate"
        self.description = "Remove all duplicated rows from a DataFrame."
        self.structure = []

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: None = None,
        source: None = None,
        rows: None = None,
        source_param: None = None,
        destination_param: None = None,
    ) -> pd.DataFrame:
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.drop_duplicates.html
        return df.drop_duplicates()
