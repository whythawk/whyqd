from __future__ import annotations
from pydantic import BaseModel, Field, validator


class ModifierModel(BaseModel):
    name: str = Field(..., description="Single-character modifier.")
    title: str = Field(..., description="Human-readable title for the name. Acts as a description.")

    class Config:
        validate_assignment = True
        use_enum_values = True
        anystr_strip_whitespace = True

    @validator("name")
    def check_name(cls, v):
        if len(v) != 1:
            raise ValueError(f"Modifier provided ({v}) must be a single character.")
        return v
