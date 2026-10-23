from datetime import date, datetime, time

from whyqd.dtypes import CellType


class CellParser:
    """One text for a typed cell, whichever reader gave it.

    Readers render the same stored cell differently: a whole number as `1`, `1.0`, or `1.00`; a boolean as `True`,
    `true`, or `1`; a date with or without its midnight. `render` gives whyqd's own text, by the rules `CellType`
    describes, so a source reads the same through any reader.
    """

    def render(
        self, *, value: str | int | float | bool | date | time | None, error: bool = False
    ) -> tuple[CellType, str] | None:
        """A cell's type and canonical text, or `None` for an empty cell.

        Each type's rule is in `CellType.describe`. Empty, and empty text, are `None`.

        Parameters
        ----------
        value: str | int | float | bool | date | time | None
            The cell's stored value, as a Python type.
        error: bool, default False
            Whether the reader reports the cell as an error, such as `#N/A`.

        Raises
        ------
        TypeError
            For any other type, which has no defined rendering.
        ValueError
            For a number that is not finite, which no cell stores.

        Example
        -------
        ```python
        cell = CellParser()
        cell.render(value=1.0)                           # (CellType.NUMBER, "1")
        cell.render(value=datetime(2024, 4, 1))          # (CellType.DATE, "2024-04-01")
        cell.render(value=datetime(2024, 4, 1, 9, 30))   # (CellType.DATE, "2024-04-01T09:30:00")
        cell.render(value="#N/A", error=True)            # (CellType.ERROR, "#N/A")
        cell.render(value="")                            # None
        ```
        """
        if value is None or value == "":
            return None
        if error:
            return CellType.ERROR, str(value)
        if isinstance(value, bool):
            return CellType.BOOLEAN, "TRUE" if value else "FALSE"
        if isinstance(value, int):
            return CellType.NUMBER, str(value)
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError(f"A cell cannot hold the number {value}.")
            return CellType.NUMBER, str(int(value)) if value.is_integer() else repr(value)
        if isinstance(value, datetime):
            if value.time() == time(0) and not value.tzinfo:
                return CellType.DATE, value.date().isoformat()
            return CellType.DATE, value.isoformat()
        if isinstance(value, (date, time)):
            return CellType.DATE, value.isoformat()
        if isinstance(value, str):
            return CellType.STRING, value
        raise TypeError(f"No rendering is defined for a cell of type {type(value).__name__}.")
