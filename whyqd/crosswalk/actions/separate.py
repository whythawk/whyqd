from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

from whyqd.crosswalk.base import BaseMorphAction

if TYPE_CHECKING:
    import modin.pandas as pd
    from whyqd.models import FieldModel


class Action(BaseMorphAction):
    """Separate the string values in a single column into any number of new columns on a specified key.

    !!! tip "Script template"
        ```python
        "SEPARATE > ['destination_field_1', 'destination_field_2', etc. ] < 'by'::['source_field']"
        ```

        Where `'by'` can be any `string` with one **MAJOR** caveat. Since `::` is used in the query, you **cannot** use
        it for separating.

    !!! example
        ```python
        "SEPARATE > ['new_1', 'new_2', 'new_3', 'new_4'] < ';;'::['separate_column']"
        ```

        Will transform:

        | ID | separate_column         |
        |:---|:------------------------|
        | 2  | Dogs;;Cats;;Fish        |
        | 3  | Cats;;Bats;;Hats;;Mats  |
        | 4  | Sharks;;Crabs           |

        Bitwise into each destination field. If more fields are required than are assigned, will raise an error.

        | ID | separate_column         | new_1 | new_2 | new_3 | new_4 |
        |:---|:------------------------|:------|:------|:------|:------|
        | 2  | Dogs;;Cats;;Fish        |Dogs   | Cats  | Fish  |       |
        | 3  | Cats;;Bats;;Hats;;Mats  |Cats   | Bats  | Hats  | Mats  |
        | 4  | Sharks;;Crabs           |Sharks | Crabs |       |       |

        You will need a different strategy if separation results in more categories than you have destination fields for.
    """

    def __init__(self):
        self.name = "SEPARATE"
        self.title = "Separate strings"
        self.description = (
            "Separate the string values in a single column into any number of new columns on a specified key."
        )
        self.structure = ["fields"]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: list[FieldModel],
        source: FieldModel,
        source_param: str | None = None,
        rows: None = None,
        destination_param: None = None,
    ) -> pd.DataFrame:
        # separateting indefinite numbers of items
        # https://stackoverflow.com/a/50459986/295606
        # https://stackoverflow.com/a/39358924/295606
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.str.extract.html
        if not source_param:
            raise ValueError("SEPARATE action did not receive an expected separate-by parameter.")
        if len(source) != 1:
            raise ValueError("SEPARATE action should have only a single source field for separating.")
        separate_array = np.array([x.split(source_param) for x in df[source[0].name].array.ravel()], dtype=object)
        num_columns = max(map(len, separate_array))
        if num_columns == 1:
            return df
        if not isinstance(destination, list) or num_columns != len(destination):
            raise ValueError(
                f"SEPARATE action needs to separate {num_columns} columns by received {len(destination)} for destination."
            )
        new_columns = [c.name for c in destination]
        df[new_columns] = df[source[0].name].str.split(source_param, expand=True)
        return df
