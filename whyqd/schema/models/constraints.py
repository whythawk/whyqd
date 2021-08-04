from typing import List, Optional, Union
from pydantic import BaseModel, Field, validator


class CategoryModel(BaseModel):
    name: str = Field(..., description="Unique category term.")
    description: Optional[str] = Field(None, description="Description of the unique term")


class ConstraintModel(BaseModel):
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
    minimum: Optional[Union[int, float]] = Field(
        None,
        description="An integer that specifies the minimum of a value, or the minimum number of characters of a string, depending on the field type.",
    )
    maximum: Optional[Union[int, float]] = Field(
        None,
        description="An integer that specifies the maximum of a value, or the maximum number of characters of a string, depending on the field type.",
    )

    @validator("maximum")
    def is_maximum(cls, v, values, **kwargs):
        if "minimum" in values and v < values["minimum"]:
            raise ValueError(f"Maximum ({v}) must be greater than Minimum ({values['minimum']}).")
        return v

    @validator("category")
    def are_categories_unique(cls, v):
        category_names = []
        for c in v:
            category_names.append(c.name)
        if len(category_names) != len(set(category_names)):
            raise ValueError(
                f"Categories must be unique. There are {len(category_names) - len(set(category_names))} duplications."
            )
        return v
