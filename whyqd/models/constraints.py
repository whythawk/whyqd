# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import List, Optional, Union
from pydantic import field_validator, ConfigDict, BaseModel, Field, ValidationInfo

from whyqd.models.category import CategoryModel


class ConstraintsModel(BaseModel):
    """What a field's values must meet beyond their type: present, unique, one of its categories, within bounds on a
    value or a string's length; and whether a zero counts as present."""

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
    zeroAsTrue: Optional[bool] = Field(
        None,
        description="Whether a zero counts as present where `CATEGORISE` assigns `True` to any value of a number or "
        "integer field. A zero is absent by default, and a blank always is.",
    )
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    @field_validator("maximum", "maxLength")
    @classmethod
    def is_maximum(cls, v: Optional[Union[int, float]], info: ValidationInfo):
        bound = {"maximum": "minimum", "maxLength": "minLength"}[info.field_name]
        least = info.data.get(bound)
        if least is not None and v is not None and v < least:
            raise ValueError(
                f"`{info.field_name}` {v} is below `{bound}` {least}. Change one, so the maximum is not below the "
                "minimum. [whyqd:constraint-bounds]"
            )
        return v

    @field_validator("category")
    @classmethod
    def check_categories_unique(cls, v: Optional[List[CategoryModel]]):
        names = [c.name for c in v]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError(
                f"Categories {', '.join(f'`{name}`' for name in repeated)} appear more than once. Remove the repeats. "
                "[whyqd:category-repeated]"
            )
        return v
