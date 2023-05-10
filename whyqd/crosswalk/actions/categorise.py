from __future__ import annotations

from whyqd.crosswalk.base import BaseCategoryAction


class Action(BaseCategoryAction):
    """Associate category terms in a source data field to a specific categorical term in a destination field. If there
     are numerous source and destination terms, then individual scripts are needed for each.

    !!! tip "Script template"
         ```python
         "CATEGORISE > 'destination_field'::'destination_term' < 'source_field'::['source_term']"
         ```

         - If `destination_term` is a boolean (`True` or `False`) then `source_term` hits will assign that boolean value.
         - If `source_term` is a boolean (`True` or `False`) then any value in that column will be assigned `True` or
           `False` and convey the `destination_term` value.
           If the `source_term` is boolean, then there **must** only be one source term.

    !!! example
        ```python
        "CATEGORISE > 'occupation_state_reliefs'::'other' < 'Current Relief Type'::['Sports Club (Registered CASC)', 'Mandatory']"
        ```
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "CATEGORISE"
        self.title = "Categorise"
        self.description = "Associate category terms in a source data field to a specific categorical term in a destination field. If there are numerous source and destination terms, then individual scripts are needed for each."
        self.structure = ["boolean", "unique"]
