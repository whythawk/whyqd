from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseSchemaAction
from whyqd.models import FieldModel

if TYPE_CHECKING:
    import modin.pandas as pd


class Action(BaseSchemaAction):
    """
    Collate a list of source fields into an array of corresponding values in a destination field.

    !!! tip "Script template"
        ```python
        "COLLATE > 'destination_field' < ['source_field', 'source_field', etc.]"
        ```

        Where the order of collation is important and is used to create an array (list) of values from corresponding sources.
        Any missing values will be included as `None`.

    This can be used as part of a process which will permit multiple corresponding columns (e.g. a `date`, `description`, 
    `value` sequence) to each be placed in an array, and then pivoted using `df.explode`.

    !!! example
        ```python
        "COLLATE > 'laReliefExemptionAmount' < ['Mandatory Relief Amount', 'Discretionary Relief Amount', 'Additional Relief Amount', 'Small Business Rate Relief Amount']"
        ```
        This could be sequenced with:
        ```python
        "CATEGORISE > 'laReliefExemptionType'::'mandatory' < 'Mandatory Relief Code'::['COMMUNITY AMATEUR SPORTS CLUB RELIEFM','MANDATORY 80%']"
        "CATEGORISE > 'laReliefExemptionType'::'discretionary' < 'Discretionary Relief Code'::['20%']"
        "CATEGORISE > 'laReliefExemptionType'::'retail' < 'Additional Relief Code'::['RETAIL SCHEME']"
        "CATEGORISE > 'laReliefExemptionType'::'small_business' < 'Small Business Rate Relief'::['yes']"
        ```
        This creates two arrays, each with four elements, and permits the following `pandas` transform:
        ```python
        df = df.explode(["laReliefExemptionType","laReliefExemptionAmount"])
        ```
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "COLLATE"
        self.title = "Collate"
        self.description = (
            "Collate a list of source fields into an array of corresponding values in a destination field."
        )
        self.structure = [FieldModel]

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: list[FieldModel],
    ) -> pd.DataFrame:
        # Defaults
        # default = None
        # if destination.constraints and destination.constraints.default:
        #     default = destination.constraints.default.name
        # Array collation
        new_column = []
        if destination.name in df.columns:
            new_column = [df[destination.name].tolist()]
        for s in source:
            new_column.append(
                [
                    [x] if not isinstance(x, list) else x
                    for x in df[s.name].tolist()
                ]
            )
        # Sorted to avoid hashing errors later ...
        if len(new_column) > 1:
            # Moving sorting to the hashing function so we can maintain None's for ordered lists
            # Permits reconstruction of datasets using array transformations
            # https://stackoverflow.com/a/18411610
            # new_column = [sorted(list(set([c for clist in x for c in clist])), key=lambda x: (x is None, x)) for x in zip(*new_column)]
            new_column = [[c for clist in x for c in clist] for x in zip(*new_column)]
        else:
            new_column = [[x] if not isinstance(x, list) else x for x in new_column[0]]
        df[destination.name] = new_column
        return df
