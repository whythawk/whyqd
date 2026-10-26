# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import List, Optional, Union
from pydantic import field_validator, ConfigDict, BaseModel, Field, ValidationInfo

from whyqd.models import CategoryModel


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
    minimum: Optional[Union[int, float]] = Field(None, description="The smallest value allowed, inclusive.")
    maximum: Optional[Union[int, float]] = Field(None, description="The largest value allowed, inclusive.")
    minLength: Optional[int] = Field(None, ge=0, description="The fewest characters a string may have.")
    maxLength: Optional[int] = Field(None, ge=0, description="The most characters a string may have.")
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    @field_validator("maximum", "maxLength")
    @classmethod
    def is_maximum(cls, v: Optional[Union[int, float]], info: ValidationInfo):
        least = info.data.get({"maximum": "minimum", "maxLength": "minLength"}[info.field_name])
        if least is not None and v is not None and v < least:
            raise ValueError(f"`{info.field_name}` ({v}) must not be less than its minimum ({least}).")
        return v

    @field_validator("category")
    @classmethod
    def check_categories_unique(cls, v: Optional[List[CategoryModel]]):
        category_names = []
        for c in v:
            category_names.append(c.name)
        if len(category_names) != len(set(category_names)):
            raise ValueError(
                f"Categories must be unique. There are {len(category_names) - len(set(category_names))} duplications."
            )
        return v
