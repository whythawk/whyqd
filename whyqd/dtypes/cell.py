# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum


class CellType(str, Enum):
    STRING = "s"
    NUMBER = "n"
    DATE = "d"
    BOOLEAN = "b"
    ERROR = "e"

    @property
    def describe(self):
        description = {
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
        return description[self.value]
