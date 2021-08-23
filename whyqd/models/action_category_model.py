from __future__ import annotations
from pydantic import BaseModel, Field, validator


class CategoryActionModel(BaseModel):
    """Category Model - generated from the Category module. A type of SchemaActionModel."""

    name: str = Field(..., description="Name of the Action. Uppercase.")
    title: str = Field(..., description="Title of the Action. Regular case.")
    description: str = Field(..., description="Description of the purpose for performing this action.")
    structure: str = Field(
        default="unique",
        description="The structure of an action depends on either 'boolean' or 'unique' action terms.",
    )

    class Config:
        use_enum_values = True
        anystr_strip_whitespace = True
        validate_assignment = True

    @validator("structure")
    def check_valid_models(cls, v):
        if v not in ["boolean", "unique"]:
            raise ValueError(f"Structure ({v}) must be of either `boolean` or `unique`.")
        return v
