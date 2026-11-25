# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum, nonmember
from typing import ClassVar


class FieldType(str, Enum):
    """A field's type, as a schema declares it. What each holds: `describe`."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    TIME = "time"
    DURATION = "duration"
    USDATE = "usdate"
    DATE = "date"
    DATETIME = "datetime"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ANY = "any"

    DESCRIPTIONS = nonmember(
        {
            "string": "Any text-based string.",
            "number": "Any number-based value, including integers and floats.",
            "integer": "Any integer-based value.",
            "boolean": "A boolean [true, false] value. Can set category constraints to fix term used.",
            "array": "Any valid array-based data.",
            "time": "A time of day, in ISO 8601 format, hh:mm:ss.",
            "duration": "A length of time, as ISO 8601 days, hours, minutes, and seconds, such as PT25M. Years and months are refused, having no fixed length.",
            "usdate": "A 1.x type, read as a `date` whose patterns put the month first, with any separator.",
            "date": "Any date without a time, written as ISO 8601, YYYY-MM-DD; a declared pattern reads other forms.",
            "datetime": "Any date with a time, written as ISO 8601. A cell's own offset is read; `rules.zone` names "
            "the zone of a clock with none; with neither, the time has no zone.",
            "month": "Any month, as month end frequency, formatted as YYYY-MM",
            "quarter": "Any quarter, as quarter end frequency, formatted as YYYY-MM.",
            "year": "Any year, as year end frequency, formatted as YYYY.",
            "any": "Any valid JSON data.",
        }
    )

    @property
    def describe(self) -> str:
        """What a field of this type holds."""
        return self.DESCRIPTIONS[self.value]


class FieldFamilies:
    """Field types grouped by how they read, each rule asking one question of one set."""

    NUMBERS: ClassVar[frozenset[str]] = frozenset({FieldType.NUMBER.value, FieldType.INTEGER.value})
    # Read as a date, any of which can hold another's
    DATES: ClassVar[frozenset[str]] = frozenset(
        {
            FieldType.DATE.value,
            FieldType.DATETIME.value,
            FieldType.USDATE.value,
            FieldType.MONTH.value,
            FieldType.QUARTER.value,
            FieldType.YEAR.value,
        }
    )
    PERIODS: ClassVar[frozenset[str]] = frozenset(
        {FieldType.MONTH.value, FieldType.QUARTER.value, FieldType.YEAR.value}
    )
    # A length of time, or a time of day, each read from hours, minutes, and seconds
    QUANTITIES: ClassVar[frozenset[str]] = frozenset({FieldType.TIME.value, FieldType.DURATION.value})
    # A time of day is no date, and a year's own number is a year, so neither reads a bare number as a serial undeclared
    NO_SERIAL: ClassVar[frozenset[str]] = frozenset({FieldType.TIME.value, FieldType.YEAR.value})
    # A reading policy has nothing to declare for these
    NO_POLICY: ClassVar[frozenset[str]] = frozenset(
        {FieldType.STRING.value, FieldType.ARRAY.value, FieldType.ANY.value}
    )
    # Never read cell by cell, being structures rather than values
    NOT_READ: ClassVar[frozenset[str]] = frozenset({FieldType.ARRAY.value, FieldType.ANY.value})
