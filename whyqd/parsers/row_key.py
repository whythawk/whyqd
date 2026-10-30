# SPDX-License-Identifier: BSD-3-Clause
import re
from typing import Iterable

from whyqd.models.dialect import DialectModel
from whyqd.parsers.column import ColumnParser


class RowKeyParser:
    """The row key: every row's number from the read, carried through every action.

    Rows are numbered from `0` by their position in the table as read, each sheet from `0`: row `0` is the first row
    after the header, or the file's first where its dialect declares no header row (`headerRowCount` 0). A 1.x data
    source reads by a dialect with no header row, so its rows are numbered as 1.x numbered them. An action never
    renumbers a row, so `DELETE_ROWS` and `PIVOT_CATEGORIES` address the same rows wherever they run.

    The key is the column `__row__`. An action that turns one row into several adds a part, `__row__1` and so on,
    holding the row's position within the rows it made; sorting by every part, in order, gives the table its order.

    The key is not in the source, so it is never a field of the source schema. A source may already hold a column
    named like one of its parts, so adding the key takes three steps, in order: check the source's names, rename any
    that clash (`deconflict`), then add the key. The renamed column keeps its data, and its new name is its name
    everywhere: in the source schema, every preview, and every crosswalk script. Add the key with a method that refuses
    an existing name (pandas' `insert`, Polars' `with_row_index`), never by assignment, which would overwrite a column
    that slipped through.
    """

    ROW = "__row__"
    _PART = re.compile(rf"^{ROW}(\d*)$")

    def __init__(self) -> None:
        self.column = ColumnParser()

    def part(self, *, index: int = 0) -> str:
        """Name of a part of the row key.

        Parameters
        ----------
        index: int, default 0
            `0` for the number from the read; `1` and on for each part an action adds.

        Returns
        -------
        str

        Example
        -------
        ```python
        row_key = RowKeyParser()
        row_key.part()          # "__row__"
        row_key.part(index=1)   # "__row__1"
        ```
        """
        if index < 0:
            raise ValueError(f"A row key part is numbered from 0, not {index}.")
        return f"{self.ROW}{index or ''}"

    def is_part(self, column: str) -> bool:
        """Whether a column name is a part of the row key."""
        match = self._PART.match(column)
        return bool(match) and match.group(1) != "0"

    def deconflict(self, *, columns: Iterable[str]) -> list[str]:
        """Source column names with any named like a part of the key renamed, so the key can be added.

        Parameters
        ----------
        columns: Iterable[str]
            Column names as read from the source.

        Returns
        -------
        list[str]
            As `ColumnParser.deconflict` gives them: `__row__` becomes `__row__.1`.
        """
        return self.column.deconflict(columns=columns, reserved=self.is_part)

    def first_position(self, *, dialect: DialectModel) -> int:
        """Position in the file's rows, counted from `0`, of the row numbered `0`.

        Parameters
        ----------
        dialect: DialectModel
            How the file is read.

        Returns
        -------
        int
            The rows skipped before the header, and the header's own, each of them a record's rows where a record
            spans several.
        """
        return dialect.skipRows + dialect.headerRowCount * len(dialect.rowsPerRecord or [1])

    def sort_order(self, *, columns: Iterable[str]) -> list[str]:
        """The row key's parts among `columns`, in the order to sort a table by.

        Parameters
        ----------
        columns: Iterable[str]

        Returns
        -------
        list[str]
            `__row__` first, then each added part by its number.
        """
        parts = [c for c in columns if self.is_part(c)]
        return sorted(parts, key=lambda c: int(self._PART.match(c).group(1) or 0))
