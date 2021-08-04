from typing import Optional, Any
from pydantic import BaseModel, Field, validator
from pydantic.types import constr
from enum import Enum

from .constraints import ConstraintModel


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


class FieldModel(BaseModel):
    name: constr(strip_whitespace=True, to_lower=True) = Field(
        ...,
        description="Machine-readable term to uniquely address this field. Cannot have spaces. CamelCase or snake_case.",
    )
    title: Optional[str] = Field(None, description="A human-readable version of the field name.")
    description: Optional[str] = Field(None, description="A description for the field.")
    type_field: FieldType = Field(..., alias="type", description="A field must contain values of a specific type.")
    constraints: Optional[ConstraintModel] = Field(
        None, description="A set of optional constraints to define the field."
    )
    missing: Optional[Any] = Field(default=None, description="Default to be used for missing values.")
    foreignKey: Optional[bool] = Field(
        default=False, description="Set `foreignKey` `true` if the field is to be treated as an immutable value."
    )

    class Config:
        use_enum_values = True
        anystr_strip_whitespace = True

    @validator("name")
    def name_space(cls, v):
        return "_".join(v.split(" ")).lower()
