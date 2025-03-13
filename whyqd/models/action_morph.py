from __future__ import annotations
from pydantic import field_validator, ConfigDict, BaseModel, Field
from typing import List, Optional


class MorphActionModel(BaseModel):
    """Morph Model - generated from the Morph module. A type of SchemaActionModel."""

    name: str = Field(..., description="Name of the Action. Uppercase.")
    title: str = Field(..., description="Title of the Action. Regular case.")
    description: str = Field(..., description="Description of the purpose for performing this action.")
    structure: Optional[List[str]] = Field(
        default=[],
        description="The structure of an action depends on source column fields, and integer row indices.",
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @field_validator("structure")
    @classmethod
    def check_valid_models(cls, v: Optional[List[str]]):
        for s in v:
            if not (s in ["fields", "rows", "source"]):
                raise ValueError(f"Structure ({s}) must be of either `source`, `fields`, or `rows`.")
        return v
