from __future__ import annotations
from typing import List, Union

from whyqd.base import BaseMorphAction


class Action(BaseMorphAction):
    """Merge a list of source Pandas DataFrames into a base DataFrame.

    Script::

        "MERGE < ['key_column'::'source_hex'::'sheet_name', ...]"

    Where the first source term of the list will be the base DataFrame.
    """

    def __init__(self) -> None:
        self.name = "MERGE"
        self.title = "Merge"
        self.description = "Merge a list of Pandas DataFrames into a single, new DataFrame, on a key column."
        self.structure = ["source"]

    def parse(self, script: str) -> List[List[str, str, Union[str, None]]]:
        """Parser for the MERGE script. Produces required terms and validates against requirements.

        Script is of the form::

            "MERGE < ['key_column'::'source_hex'::'sheet_name', etc.]"

        .. note:: There can only be *one* interim data source, and only *one* `MERGE` script, which must also be
            *first* in the list of `ACTIONs` for that data source.

        Parameters
        ----------
        script: str
            A `MERGE` action script.

        Raises
        ------
        ValueError for any parsing errors.

        Returns
        -------
        list of list of str
            Parsed list of updated input source data.
        """
        from whyqd.parsers import ParserScript

        parser = ParserScript()
        merge_list = []
        # Get unique assignment terms
        root = parser.get_split_terms(script, "<")
        if len(root) != 2:
            raise ValueError(f"`MERGE` action script has no source terms ({script}).")
        # Extract source terms
        source_term = list(self.parser.generate_contents(root[1]))
        if len(source_term) != 1:
            raise ValueError(f"MERGE action source terms must not be nested. ({source_term}).")
        source_term = self.parser.get_split_terms(source_term[0][1], ",")
        for s in source_term:
            s = self.parser.get_split_terms(s, "::")
            s = [self.parser.get_literal(t) for t in s]
            key, uid, sheet_name = None, None, None
            if len(s) == 3:
                key, uid, sheet_name = s
            elif len(s) == 2:
                key, uid = s
            else:
                raise ValueError(
                    f"MERGE action source terms must include `key`, `source`, and an optional `sheet_name`. No more or less. ({s})."
                )
            merge_list.append([key, uid, sheet_name])
        return merge_list
