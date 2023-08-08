from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class CategoryActionModel(BaseModel):
    """Category Model - generated from the Category module. A type of BaseCategoryAction."""

    name: str = Field(..., description="Name of the Action. Uppercase.")
    title: str = Field(..., description="Title of the Action. Regular case.")
    description: str = Field(..., description="Description of the purpose for performing this action.")
    structure: Optional[List[str]] = Field(
        default=[],
        description="The structure of an action depends on either 'boolean' or 'unique' action terms.",
    )

    class Config:
        use_enum_values = True
        # anystr_strip_whitespace = True
        validate_assignment = True

    @validator("structure")
    def check_valid_models(cls, v):
        for s in v:
            if not (s in ["boolean", "unique"]):
                raise ValueError(f"Structure ({s}) must be of either `boolean` or `unique`.")
        return v
