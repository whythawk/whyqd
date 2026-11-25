# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum, nonmember


class SerialDate(str, Enum):
    """How a bare number counts a date, as a declared `rules.serial` says. What each counts: `describe`."""

    EXCEL_1900 = "excel-1900"
    EXCEL_1904 = "excel-1904"
    UNIX = "unix"

    DESCRIPTIONS = nonmember(
        {
            "excel-1900": "Days counted as most workbooks count them, serial 1 being 1900-01-01. Serial 60 is a 29 "
            "February 1900 that never happened, so it refuses, as does serial 0.",
            "excel-1904": "Days counted as a workbook in the 1904 date system counts them, serial 0 being 1904-01-01.",
            "unix": "Seconds since 1970-01-01 UTC.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]


class CellType(str, Enum):
    """The type a file stores a cell as, written beside its text where the format stores types. How each renders as
    text, the rule every reader follows: `describe`."""

    STRING = "s"
    NUMBER = "n"
    DATE = "d"
    BOOLEAN = "b"
    ERROR = "e"

    DESCRIPTIONS = nonmember(
        {
            "s": "Text, as the file holds it. A workbook's text loses the XML whitespace at its ends (space, tab, line "
            "feed, carriage return) unless marked to keep it (`xml:space`); empty text is an empty cell.",
            "n": "A number, as an IEEE 754 double. A whole one, its exact integer digits; any other, the shortest "
            "digits that return the same double, in fixed notation from `1e-4` up, and below that `d.ddde-XX`.",
            "d": "A date as ISO 8601, with its time only when that is not midnight; a time alone; or a duration as "
            "ISO 8601 (`PT25H30M`). A date's or time's fraction of a second has six digits; a duration's, no "
            "trailing zeros.",
            "b": "A boolean, as `TRUE` or `FALSE`.",
            "e": "An error cell, as its code from Excel's list: `#DIV/0!`, `#N/A`, `#NAME?`, `#NULL!`, `#NUM!`, "
            "`#REF!`, or `#VALUE!`.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]
