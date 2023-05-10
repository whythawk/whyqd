from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """Remove all blank columns and rows from a DataFrame.

    !!! tip "Script template"
        ```python
        "DEBLANK"
        ```
    """

    def __init__(self) -> None:
        self.name = "DEBLANK"
        self.title = "De-blank"
        self.description = "Remove all blank columns and rows from a DataFrame."
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
        # https://stackoverflow.com/a/51794989
        # First remove all columns (axis=1) with no values
        df = df.dropna(how="all", axis=1)
        # Remove all rows (axis=0) with no values
        return df.dropna(how="all", axis=0)
