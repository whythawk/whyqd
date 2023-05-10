from enum import Enum


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    TIME = "time"
    DATE = "date"
    DATETIME = "datetime"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ANY = "any"

    @property
    def describe(self):
        description = {
            "string": "Any text-based string.",
            "number": "Any number-based value, including integers and floats.",
            "integer": "Any integer-based value.",
            "boolean": "A boolean [true, false] value. Can set category constraints to fix term used.",
            "array": "Any valid array-based data.",
            "time": "Any time, with an optional date. Must be in ISO8601 format, hh:mm:ss.",
            "date": "Any date without a time. Must be in ISO8601 format, YYYY-MM-DD.",
            "datetime": "Any date with a time. Must be in ISO8601 format, with UTC time specified (optionally) as YYYY-MM-DD hh:mm:ss Zz.",
            "month": "Any month, as month end frequency, formatted as YYYY-MM",
            "quarter": "Any quarter, as quarter end frequency, formatted as YYYY-MM.",
            "year": "Any year, as year end frequency, formatted as YYYY.",
            "any": "Any valid JSON data.",
        }
        return description[self.value]

    @property
    def astype(self):
        astypes = {
            "string": "string",
            "number": "Float64",
            "integer": "Int64",
            "boolean": "boolean",
            "array": "object",
            "time": "timedelta64[ns]",
            "date": "datetime64[ns]",
            "datetime": "datetime64[ns, UTC]",
            "month": "period[M]",
            "quarter": "period[Q]",
            "year": "period[Y]",
            "any": "object",
        }
        return astypes[self.value]
