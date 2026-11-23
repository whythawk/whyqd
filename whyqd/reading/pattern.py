# SPDX-License-Identifier: BSD-3-Clause
from typing import ClassVar

from whyqd.config.patterns import PythonPatterns
from whyqd.dtypes import FieldFamilies, FieldType


class PatternParser:
    """A date, time, or duration pattern as Unicode's [UAX 35](https://unicode.org/reports/tr35/tr35-dates.html#Date_Field_Symbol_Table)
    writes it, which CSV on the Web reads, however it was typed: Excel's spelling and `strptime`'s are translated.

    A policy's pattern is translated when it is declared, and a stored cell's format when it is read, so both read by
    one grammar. Pure Python, so a definition loads without the engine.

    Example:
      ```python
      PatternParser().standard_pattern("DD/MM/YYYY", "date")   # "dd/MM/yyyy"
      ```
    """

    YEAR_FIELDS: ClassVar[frozenset[str]] = frozenset({"y", "yy", "yyyy"})
    MONTH_NAMES: ClassVar[frozenset[str]] = frozenset({"MMM", "MMMM"})
    MONTH_FIELDS: ClassVar[frozenset[str]] = frozenset({"M", "MM"}) | MONTH_NAMES
    NAME_FIELDS: ClassVar[frozenset[str]] = MONTH_NAMES | {"E", "EEE", "EEEE"}
    DATE_FIELDS: ClassVar[frozenset[str]] = YEAR_FIELDS | MONTH_FIELDS | {"d", "dd", "E", "EEE", "EEEE"}
    TIME_FIELDS: ClassVar[frozenset[str]] = frozenset({"H", "HH", "h", "hh", "a", "m", "mm", "s", "ss", "S"})
    READABLE: ClassVar[dict[str, frozenset[str]]] = {
        FieldType.DATE.value: DATE_FIELDS,
        FieldType.USDATE.value: DATE_FIELDS,
        FieldType.TIME.value: TIME_FIELDS,
        FieldType.DATETIME.value: DATE_FIELDS | TIME_FIELDS,
        FieldType.MONTH.value: YEAR_FIELDS | MONTH_FIELDS,
        FieldType.QUARTER.value: YEAR_FIELDS | MONTH_FIELDS | {"Q"},
        FieldType.YEAR.value: YEAR_FIELDS,
        FieldType.DURATION.value: frozenset({"d", "dd", "H", "HH", "m", "mm", "s", "ss", "S"}),
    }
    NEEDED: ClassVar[dict[str, frozenset[str]]] = {
        FieldType.DATE.value: frozenset("yMd"),
        FieldType.TIME.value: frozenset("H"),
        FieldType.DATETIME.value: frozenset("yMdH"),
        FieldType.MONTH.value: frozenset("yM"),
        FieldType.QUARTER.value: frozenset("yM"),
        FieldType.YEAR.value: frozenset("y"),
    }
    # How many digits or characters a field reads, a number's width saying nothing of its meaning: `dd` reads `1`
    WIDTHS: ClassVar[dict[str, tuple[int, int]]] = {
        "y": (1, 99),
        "yyyy": (4, 99),
        "yy": (2, 2),
        "Q": (1, 1),
        "M": (1, 2),
        "MM": (1, 2),
        "d": (1, 2),
        "dd": (1, 2),
        "H": (1, 2),
        "HH": (1, 2),
        "h": (1, 2),
        "hh": (1, 2),
        "m": (1, 2),
        "mm": (1, 2),
        "s": (1, 2),
        "ss": (1, 2),
    }
    STRPTIME: ClassVar[dict[str, str]] = {
        "d": "dd",
        "e": "d",
        "m": "MM",
        "Y": "yyyy",
        "y": "yy",
        "H": "HH",
        "I": "hh",
        "M": "mm",
        "S": "ss",
        "f": "S",
        "b": "MMM",
        "B": "MMMM",
        "a": "EEE",
        "A": "EEEE",
        "p": "a",
        "z": "X",
    }
    OFFSET_FIELDS: ClassVar[frozenset[str]] = frozenset("XxZO")

    def __init__(self) -> None:
        self.patterns = PythonPatterns()

    def standard_pattern(self, typed: str, dtype: str) -> str:
        """A pattern as UAX 35 writes it, from Excel's or `strptime`'s spelling.

        A letter's case means nothing in Excel, so `DD` and `YYYY` read as day and year, as they were meant, and `m` is
        minutes beside an hour or a second and otherwise a month, by Excel's own rule. An offset is not part of a
        pattern, a datetime's cell reading one wherever it holds one.
        """
        p = self.patterns
        text = p.STRPTIME.sub(lambda match: self.STRPTIME.get(match.group(1), match.group()), typed)
        text = p.EXCEL_DROPPED.sub("", text)
        text = p.EXCEL_ELAPSED.sub(lambda match: match.group(1), text)
        text = p.EXCEL_DAY_PERIOD.sub("a", text)
        text = p.EXCEL_QUOTED.sub(lambda match: f"'{match.group(1)}'", text)
        text = p.EXCEL_ESCAPED.sub(lambda match: f"'{match.group(1)}'", text)
        text = p.EXCEL_FRACTION.sub(".S", text)
        parts = self.parts(text)
        fields = [part for is_field, part in parts if is_field]
        twelve_hour = any(field[0] in "aA" for field in fields)
        written = []
        for index, (is_field, part) in enumerate(parts):
            if not is_field:
                dropped = part == "Z" and dtype == FieldType.DATETIME.value
                written.append("" if dropped else f"'{part}'" if any(c.isalpha() for c in part) else part)
                continue
            before = next((f for is_f, f in reversed(parts[:index]) if is_f), "")
            after = next((f for is_f, f in parts[index + 1 :] if is_f), "")
            written.append(self.standard_field(part, dtype, before, after, twelve_hour))
        return "".join(written).rstrip()

    def standard_field(self, field: str, dtype: str, before: str, after: str, twelve_hour: bool) -> str:
        """One field of a pattern as UAX 35 writes it, read beside the fields before and after it."""
        letter, length = field[0], len(field)
        if letter in "yY":
            return "yy" if length == 2 else "yyyy" if length == 4 else "y"
        if letter in "dD":
            return {3: "EEE", 4: "EEEE"}.get(length, "d" * min(length, 2))
        if letter in "mM":
            if length > 2:
                return "M" * length
            minutes = (
                before[:1] in tuple("hH")
                or after[:1] in tuple("sS")
                or (letter == "m" and dtype in FieldFamilies.QUANTITIES)
            )
            return ("m" if minutes else "M") * length
        if letter in "hH":
            return ("h" if twelve_hour else "H") * min(length, 2)
        if letter in "sS":
            return "S" if before[:1] in tuple("sS") else "s" * min(length, 2)
        if letter in "aA":
            return "a"
        if letter in "qQ":
            return "Q"
        if letter == "T":
            return "'T'"
        if letter in self.OFFSET_FIELDS and dtype == FieldType.DATETIME.value:
            return ""
        return field

    def parts(self, pattern: str) -> list[tuple[bool, str]]:
        """A date pattern's parts in order, each `(is_field, text)`; a quoted literal without its quotes."""
        found = []
        for match in self.patterns.PATTERN_PART.finditer(pattern):
            text = match.group()
            found.append((bool(match.group(1)), text[1:-1] if text.startswith("'") else text))
        return found

    def two_readings(self, first: str, second: str) -> bool:
        """Whether one cell could fit both patterns and read differently: the same literals, widths that meet, and a
        position that means something else. `d/M/yyyy` and `dd/MM/yyyy` read alike, and `MM/dd/yyyy` does not."""
        ones, others = self.parts(first), self.parts(second)
        if len(ones) != len(others):
            return False
        differs = False
        for (one_field, one), (other_field, other) in zip(ones, others):
            if one_field != other_field or (not one_field and one != other):
                return False
            if one_field:
                low_one, high_one = self.WIDTHS.get(one, (1, 99))
                low_other, high_other = self.WIDTHS.get(other, (1, 99))
                if max(low_one, low_other) > min(high_one, high_other):
                    return False
                meaning = [field if field == "yy" else field[0] for field in (one, other)]
                differs = differs or meaning[0] != meaning[1]
        return differs
