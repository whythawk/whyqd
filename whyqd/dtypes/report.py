# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum, StrEnum, nonmember


class FindingKind(str, Enum):
    """What a report's finding is: a fault, a warning, or a fact."""

    FAULT = "fault"
    FACT = "fact"
    WARNING = "warning"

    DESCRIPTIONS = nonmember(
        {
            "fault": "The file could not be read as written, or was read with a loss. Its owner may correct it, or a "
            "setting may read past it.",
            "warning": "A value was read, with something worth checking. It stops nothing.",
            "fact": "Something the file holds, with no claim of what it means. What to do about it, if anything, is "
            "for the crosswalk.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]


class ReadingKind(str, Enum):
    """What reading a cell as its field's type gave: a value, a blank, or a refusal."""

    VALUE = "value"
    BLANK = "blank"
    REFUSED = "refused"

    DESCRIPTIONS = nonmember(
        {
            "value": "The cell fits its field's declaration, and holds this value.",
            "blank": "The cell is empty or only whitespace, so it is never a value.",
            "refused": "The cell does not fit its field's declaration, and is never read another way.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]


class ReadingWarning(str, Enum):
    """A cell read as its type with one sensible reading the field did not declare, each confirmed by declaring it."""

    CURRENCY = "currency-read"
    SIGN = "sign-read"
    PERCENT = "percent-read"
    MARKS = "marks-read"
    EXPONENT = "exponent-read"
    EXACT_DECIMAL = "exact-decimal"
    ROUNDED = "integer-rounded"
    SERIAL = "serial-read"
    MONTH_NAME = "month-name-read"
    DATE_ORDER = "date-order-read"
    YEAR_BELOW_1000 = "year-below-1000"
    TIME_DROPPED = "time-dropped"
    REPEATED_HOUR = "repeated-hour"

    DESCRIPTIONS = nonmember(
        {
            "currency-read": "A currency mark was read past, the number kept. Declaring it in `rules.currency` "
            "confirms it.",
            "sign-read": "A negative form such as `(x)` or `x-` was read as negative. Declaring it in `rules.negative` "
            "confirms it.",
            "percent-read": "A percent was read as a fraction, `5%` as 0.05. Declaring `rules.percent` confirms it.",
            "marks-read": "Which mark is the decimal was settled by the cell itself: the last of two marks, a repeated "
            "mark grouping, or a lone mark without three digits after it. Declaring `format` confirms it.",
            "exponent-read": "An exponent was read, `1e3` as 1000. Setting `rules.exponent` confirms it; a reference "
            "such as `12E4` belongs in a `string` field.",
            "exact-decimal": "More digits than a `Float64` holds, so the column read as exact decimals. Declaring "
            "`base` as `decimal` confirms it.",
            "integer-rounded": "A fraction rounded half away from zero, `5.5` to 6. A `number` field keeps it.",
            "serial-read": "A bare number read as a date serial, text by Excel's 1900 system. Declaring `rules.serial` "
            "confirms it.",
            "month-name-read": "A month's name read with no language declared, being one month in every language whyqd "
            "holds. Declaring `rules.language` confirms it.",
            "date-order-read": "A date's order was settled by the cell itself, as `13/04/2024`, whose 13 can only be a "
            "day. Declaring `format` confirms it.",
            "year-below-1000": "The cell read as a year before 1000, which is more often a shortened year: `24` under "
            "`y` is the year 24. A `yy` pattern with `rules.yearStart` reads a century.",
            "time-dropped": "A date field's cell also held a time other than midnight, which a date does not keep. A "
            "`datetime` field keeps it.",
            "repeated-hour": "The clocks went back, so this time happened twice, and it read as the earlier.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]


class RefusalReason(str, Enum):
    """Why a cell does not read as its field's type, which it is then never read as another way."""

    NO_NUMBER = "no-number"
    TWO_NUMBERS = "two-numbers"
    NUMBER_FORM = "number-form-character"
    MIXED_DIGITS = "mixed-digits"
    UNDECLARED_CHARACTER = "undeclared-character"
    UNDECLARED_SIGN = "undeclared-sign"
    UNDECLARED_EXPONENT = "undeclared-exponent"
    UNDECLARED_NON_FINITE = "undeclared-non-finite"
    GROUPING = "grouping-mismatch"
    TOO_MANY_DIGITS = "too-many-digits"
    NOT_IN_FORMAT = "not-in-format"
    TWO_READINGS = "two-readings"
    NO_ZONE = "no-zone"
    IMPOSSIBLE_DATE = "impossible-date"
    ERROR_CELL = "error-cell"

    DESCRIPTIONS = nonmember(
        {
            "no-number": "A number field's cell holds no number.",
            "two-numbers": "A number field's cell holds two numbers, a fault for a crosswalk action.",
            "number-form-character": "The cell holds a character such as `¹`, `①`, or `½`, which normalising would "
            "turn into a digit of its number: `43.40¹` would read 43.401.",
            "mixed-digits": "The cell's digits come from more than one script, such as `٣4`.",
            "undeclared-character": "Something beside the number that the field does not declare, such as `£` or `<`.",
            "undeclared-sign": "A negative form the field does not declare, which never reads as positive.",
            "undeclared-exponent": "An exponent the field does not declare, so a reference such as `12E4` stays one.",
            "undeclared-non-finite": "`NaN` or `INF`, which the field does not declare.",
            "grouping-mismatch": "Group marks that do not fit the declared group sizes, such as `1,23`.",
            "too-many-digits": "More digits than the type holds: 38 for an exact decimal, or 18 for an integer.",
            "not-in-format": "The cell fits neither the declared format nor, if none, any form with one reading.",
            "two-readings": "The cell fits two readings: two declared patterns, or with none declared two orders, as "
            "`01/02/2024`, or a month's name meaning different months in different languages.",
            "no-zone": "The cell states no offset, beside cells that do, and the field declares no zone.",
            "impossible-date": "The cell fits the pattern and names no such date or time, such as 31 April.",
            "error-cell": "A workbook's error cell, such as `#N/A`, which is no value of any type.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]


class ConformanceFinding(str, Enum):
    """What a transform found about a field as a whole, beside each cell's refusals and warnings: a conflict of types,
    a failed constraint, or something worth checking."""

    TYPE_CONFLICT = "type-conflict"
    CONSTRAINT_REQUIRED = "constraint-required"
    CONSTRAINT_UNIQUE = "constraint-unique"
    CONSTRAINT_MINIMUM = "constraint-minimum"
    CONSTRAINT_MAXIMUM = "constraint-maximum"
    CONSTRAINT_MIN_LENGTH = "constraint-min-length"
    CONSTRAINT_MAX_LENGTH = "constraint-max-length"
    STORED_AS_OTHER_TYPE = "stored-as-other-type"
    SEVERAL_CURRENCIES = "several-currencies"
    UNREAD_REFUSAL = "unread-refusal"

    DESCRIPTIONS = nonmember(
        {
            "type-conflict": "A source field's type cannot become its destination's, found before any cell is read.",
            "constraint-required": "A destination field requires a value, and these cells hold none.",
            "constraint-unique": "A destination field's values must be unique, and these repeat one.",
            "constraint-minimum": "These values are below the destination field's minimum.",
            "constraint-maximum": "These values are above the destination field's maximum.",
            "constraint-min-length": "These texts are shorter than the destination field allows.",
            "constraint-max-length": "These texts are longer than the destination field allows.",
            "stored-as-other-type": "A text field's cells a workbook stores as another type, which Excel may have "
            "converted on opening, the original gone.",
            "several-currencies": "A number field's amounts are in more than one currency, which read as one number.",
            "unread-refusal": "A field's cells were refused, and no action reads the field, so the transform goes on.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]


class Place(StrEnum):
    """What a report's rows count, which its messages and preview name. A `StrEnum`, so a message prints `line`."""

    LINE = "line"
    ROW = "row"


class SettingSource(str, Enum):
    """Where a read's setting came from: declared, a default, or the file itself."""

    DECLARED = "declared"
    DEFAULT = "default"
    FILE = "file"

    DESCRIPTIONS = nonmember(
        {
            "declared": "Declared by the wrangler.",
            "default": "Not declared, so its fixed default.",
            "file": "Settled by what the file shows, by a rule that never depends on anything else: an encoding's "
            "steps, for one.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]
