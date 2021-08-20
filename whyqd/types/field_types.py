from enum import Enum


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    DATE = "date"
    DATETIME = "datetime"
    YEAR = "year"

    def describe(self):
        description = {
            "string": "Any text-based string.",
            "number": "Any number-based value, including integers and floats.",
            "integer": "Any integer-based value.",
            "boolean": "A boolean [true, false] value. Can set category constraints to fix term used.",
            "object": "Any valid JSON data.",
            "array": "Any valid array-based data.",
            "date": "Any date without a time. Must be in ISO8601 format, YYYY-MM-DD.",
            "datetime": "Any date with a time. Must be in ISO8601 format, with UTC time specified (optionally) as YYYY-MM-DD hh:mm:ss Zz.",
            "year": "Any year, formatted as YYYY.",
        }
        return description[self.value]
