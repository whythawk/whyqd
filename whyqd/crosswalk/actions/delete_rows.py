from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseMorphAction):
    """Delete rows provided in a list. They don't have to be contiguous.

    !!! tip "Script template"
        ```python
        "DELETE_ROWS < [int, int, int, etc.]"
        ```

        Where `int` are  specific integer row references / indices. Delete specifically does *not* reindex the rows so
        that future reference calls will reference a static index.

    !!! example
        ```python
        "DELETE_ROWS < [0, 1, 2, 3]"
        ```
    """

    def __init__(self) -> None:
        self.name = "DELETE_ROWS"
        self.title = "Delete rows"
        self.description = "Delete rows provided in a list. They don't have to be contiguous."
        self.structure = ["rows"]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        rows: list[int] = None,
        destination: None = None,
        source: None = None,
        source_param: None = None,
        destination_param: None = None,
    ) -> pd.DataFrame:
        return df.drop(df.index.intersection(rows))
