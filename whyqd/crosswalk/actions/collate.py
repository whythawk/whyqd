from __future__ import annotations
from typing import TYPE_CHECKING

from whyqd.crosswalk.base import BaseSchemaAction
from whyqd.models import ModifierModel, FieldModel

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
        self.structure = [ModifierModel, FieldModel]

    @property
    def modifiers(self) -> list[ModifierModel]:
        return [ModifierModel(**{"name": "~", "title": "Spacer"})]

    def validate(self, *, destination: FieldModel, source: list) -> bool:
        """
        Validate that script source structure conforms to the ACTION structure.

        Returns
        -------
        bool
        """
        if not isinstance(source, list):
            raise ValueError(f"Action source script does not conform to required structure. ({source})")
        for term in source:
            # Loops through the phrasing of the structure, and checks that each term is as expected
            # does not check that the actual terms match, though
            if isinstance(term, tuple(self.structure)):
                continue
            else:
                raise ValueError(
                    f"Source structure ({term}) doesn't conform to ACTION structure requirements ({self.structure})."
                )
        return True

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: list[FieldModel | ModifierModel],
    ) -> pd.DataFrame:
        # Defaults
        # default = None
        # if destination.constraints and destination.constraints.default:
        #     default = destination.constraints.default.name
        # Array collation
        new_column = []
        if destination.name in df.columns:
            new_column = [df[destination.name].tolist()]
        spacer = [None] * len(df)
        for s in source:
            source_column = spacer
            if isinstance(s, FieldModel):
                # It's not a spacer column
                source_column = df[s.name].tolist()
            new_column.append(
                [
                    [x] if not isinstance(x, list) else x
                    for x in source_column
                ]
            )
        if len(new_column) > 1:
            # Permits reconstruction of datasets using array transformations
            # https://stackoverflow.com/a/18411610
            new_column = [[c for clist in x for c in clist] for x in zip(*new_column)]
        else:
            new_column = [[x] if not isinstance(x, list) else x for x in new_column[0]]
        df[destination.name] = new_column
        return df
