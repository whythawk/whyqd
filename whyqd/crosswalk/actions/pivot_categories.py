from __future__ import annotations
from typing import TYPE_CHECKING
import modin.pandas as pd
import numpy as np

from whyqd.crosswalk.base import BaseCategoryAction

if TYPE_CHECKING:
    from whyqd.models import FieldModel


class Action(BaseCategoryAction):
    """Convert row-level categories into field categorisations.

    !!! tip "Script template"
        ```python
        "PIVOT_CATEGORIES > 'destination_field' < 'source_field'::[int, int, int, etc.]"
        ```

        Where `int` contains the rows that define the categories, and `field` are the fields to include. Makes several
        assumptions:

        - Rows may contain more than one category
        - All terms in indexed rows in the same field are related
        - Categories are assigned downwards to all rows between indices
        - The last indexed category is assigned to all rows to the end of the table

    !!! example
        ```python
        "PIVOT_CATEGORIES > 'NewField' < 'Field'::[1, 5]"
        ```

        Will transform:

        | ID | Field |
        |:---|:------|
        | 1  | Cat1  |
        | 2  | Term2 |
        | 3  | Term3 |
        | 4  | Term4 |
        | 5  | Cat2  |
        | 6  | Term6 |
        | 7  | Term7 |
        | 8  | Term8 |

        To:

        | ID | Field | NewField |
        |:---|:------|:---------|
        | 2  | Term2 | Cat1     |
        | 3  | Term3 | Cat1     |
        | 4  | Term4 | Cat1     |
        | 6  | Term6 | Cat2     |
        | 7  | Term7 | Cat2     |
        | 8  | Term8 | Cat2     |
    """

    def __init__(self):
        super().__init__()
        self.name = "PIVOT_CATEGORIES"
        self.title = "Pivot categories"
        self.description = "Convert row-level categories into field categorisations."

    def parse(self, *, script: str) -> dict[str, str]:
        parsed = {}
        # Get unique assignment terms
        root = self.parser.get_split_terms(script=script, by="<")
        if len(root) != 2:
            raise ValueError(f"Category action script has no source terms ({script}).")
        # Extract source terms
        source_terms = self.parser.get_split_terms(script=root[1], by="::")
        parsed["source"] = source_terms[0]
        if len(source_terms) != 2:
            raise ValueError(f"Category pivot action script has no source category row term ({script}).")
        source_terms = self.parser.get_literal(text=source_terms[1])
        if not all([isinstance(x, int) for x in source_terms]):
            raise ValueError(f"Category pivot row terms are not integers ({script}).")
        parsed["source_category"] = source_terms
        root = self.parser.get_split_terms(script=root[0], by=">")
        # Extract destination terms
        if len(root) != 2:
            raise ValueError(f"Category action script has no destination terms ({script}).")
        parsed["destination"] = root[1]
        parsed["category"] = None
        # And the action term
        parsed["action"] = root[0]
        return parsed

    def transform(
        self,
        *,
        df: pd.DataFrame,
        destination: FieldModel,
        source: FieldModel,
        category: None = None,
        assigned: list[int] | None = None,
    ) -> pd.DataFrame:
        # Fix: Multiple arguments results in keyerror in Modin
        df[destination.name] = None
        for i, idx in enumerate(assigned):
            to_idx = df.index[-1] + 1
            if i + 1 < len(assigned):
                to_idx = assigned[i + 1]
            category_column = {k: v for k, v in df.loc[idx].items() if pd.notnull(v) and k == source.name}
            # https://stackoverflow.com/a/46307319
            idx_list = np.arange(idx + 1, to_idx)
            # https://github.com/modin-project/modin/issues/4354
            df.loc[df.index.intersection(idx_list), destination.name] = category_column[source.name]
        return df.drop(assigned, errors="ignore")
