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
    minimum: Optional[Union[int, float]] = Field(
        None,
        description="An integer that specifies the minimum of a value, or the minimum number of characters of a string, depending on the field type.",
    )
    maximum: Optional[Union[int, float]] = Field(
        None,
        description="An integer that specifies the maximum of a value, or the maximum number of characters of a string, depending on the field type.",
    )
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    @field_validator("maximum")
    @classmethod
    def is_maximum(cls, v: Optional[Union[int, float]], info: ValidationInfo):
        if info.data["minimum"] is not None and v is not None and v < info.data["minimum"]:
            raise ValueError(f"Maximum ({v}) must be greater than Minimum ({info.data['minimum']}).")
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
