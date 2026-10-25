# SPDX-License-Identifier: BSD-3-Clause
from typing import Callable, Iterable


class ColumnParser:
    """Column names, made safe to work with without changing the source."""

    def deconflict(self, *, columns: Iterable[str], reserved: Callable[[str], bool] | None = None) -> list[str]:
        """Column names made unique, renaming only what clashes, as the read names repeated headers.

        The first of a repeated name keeps it; each repeat takes the lowest free `.N` suffix, never a name already
        among the columns. A name for which `reserved` is true is renamed the same way, even the first time it appears,
        so whyqd can add a column of that name without replacing source data. The source and its data are unchanged,
        and the new name is the column's only name.

        Parameters
        ----------
        columns: Iterable[str]
            Column names as read from the source.
        reserved: Callable[[str], bool] | None, default None
            Whether a name is kept for whyqd's own use.

        Returns
        -------
        list[str]

        Example
        -------
        ```python
        column = ColumnParser()
        column.deconflict(columns=["a", "a", "a.1"])                                   # ["a", "a.2", "a.1"]
        column.deconflict(columns=["__row__", "a"], reserved=lambda c: c == "__row__")  # ["__row__.1", "a"]
        ```
        """
        columns = list(columns)
        taken = set(columns)
        seen = set()
        renamed = []
        for name in columns:
            if name in seen or (reserved and reserved(name)):
                n = 1
                while f"{name}.{n}" in taken:
                    n += 1
                name = f"{name}.{n}"
                taken.add(name)
            seen.add(name)
            renamed.append(name)
        return renamed
