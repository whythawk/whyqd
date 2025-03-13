from __future__ import annotations
from typing import List, Optional
from pydantic import field_validator, ConfigDict, BaseModel, Field


class CategoryActionModel(BaseModel):
    """Category Model - generated from the Category module. A type of BaseCategoryAction."""

    name: str = Field(..., description="Name of the Action. Uppercase.")
    title: str = Field(..., description="Title of the Action. Regular case.")
    description: str = Field(..., description="Description of the purpose for performing this action.")
    structure: Optional[List[str]] = Field(
        default=[],
        description="The structure of an action depends on either 'boolean' or 'unique' action terms.",
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @field_validator("structure")
    @classmethod
    def check_valid_models(cls, v: Optional[List[str]]):
        for s in v:
            if not (s in ["boolean", "unique"]):
                raise ValueError(f"Structure ({s}) must be of either `boolean` or `unique`.")
        return v
