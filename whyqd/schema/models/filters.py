from typing import List
from pydantic import BaseModel, Field, validator
from pydantic.types import constr
from enum import Enum


class FilterType(str, Enum):
    LATEST = "latest"
    AFTER = "after"
    BEFORE = "before"
    ALL = "all"

    def describe(self):
        description = {
            "latest": "Import most recent observations.",
            "after": "Import observations after a specified date.",
            "before": "Import observations before a specified date.",
            "all": "Default, import all observations.",
        }
        return description[self.value]


class FilterModel(BaseModel):
    field: constr(strip_whitespace=True, to_lower=True) = Field(
        ...,
        description="Foreign-key reference to unique column to be filtered based on dates in this field.",
    )
    modifiers: List[FilterType] = Field(
        default=["all"], description="A filter is of 'latest', 'after', 'before', or 'all' (default)."
    )

    class Config:
        # https://stackoverflow.com/a/65211727/295606
        use_enum_values = True

    @validator("modifiers")
    def is_properly_filtered(cls, v):
        if len(v) >= 3:
            raise ValueError(
                f"A maximum of two filters may apply at the same time, and then only they are of type {FilterType.BEFORE} and {FilterType.AFTER}."
            )
        if len(v) == 2:
            if set([f.modifier for f in v]) != set([FilterType.BEFORE, FilterType.AFTER]):
                raise ValueError(
                    f"When two filters apply at the same time, they must be of type {FilterType.BEFORE} and {FilterType.AFTER}."
                )
        return v
