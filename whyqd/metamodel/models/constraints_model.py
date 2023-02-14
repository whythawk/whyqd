from __future__ import annotations
from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator

from whyqd.metamodel.models import CategoryModel


class ConstraintsModel(BaseModel):
    required: Optional[bool] = Field(
        default=False, description="Indicates whether a field must have a value for each instance."
    )
    unique: Optional[bool] = Field(
        default=False, description="When `true`, each value defined by the field `MUST` be unique."
    )
    category: Optional[List[CategoryModel]] = Field(
        None,
        alias="enum",
        description="The set of unique category terms permitted in this field,  with `name` & (optional) `description`.",
    )
    default: Optional[CategoryModel] = Field(
        None,
        description="A default category term used when source values are ambiguous, or unstated.",
    )
    minimum: Optional[Union[int, float]] = Field(
        None,
        description="An integer that specifies the minimum of a value, or the minimum number of characters of a string, depending on the field type.",
    )
    maximum: Optional[Union[int, float]] = Field(
        None,
        description="An integer that specifies the maximum of a value, or the maximum number of characters of a string, depending on the field type.",
    )

    class Config:
        validate_assignment = True

    @validator("maximum")
    def is_maximum(cls, v, values, **kwargs):
        if "minimum" in values and v < values["minimum"]:
            raise ValueError(f"Maximum ({v}) must be greater than Minimum ({values['minimum']}).")
        return v

    @validator("category")
    def check_categories_unique(cls, v):
        category_names = []
        for c in v:
            category_names.append(c.name)
        if len(category_names) != len(set(category_names)):
            raise ValueError(
                f"Categories must be unique. There are {len(category_names) - len(set(category_names))} duplications."
            )
        return v
