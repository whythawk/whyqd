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
            "s": "Text, as stored. Text that is only whitespace stays text; empty text is an empty cell.",
            "n": "A number, as its shortest exact text; a whole number without `.0`.",
            "d": "A date as ISO 8601, with its time only when that is not midnight; a time alone, or a duration, as "
            "ISO 8601 (`PT25H30M`).",
            "b": "A boolean, as `TRUE` or `FALSE`.",
            "e": "An error cell, such as `#N/A`, as its reader reports it.",
        }
        return description[self.value]
