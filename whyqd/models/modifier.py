from __future__ import annotations
from pydantic import field_validator, ConfigDict, BaseModel, Field


class ModifierModel(BaseModel):
    name: str = Field(..., description="Single-character modifier.")
    title: str = Field(..., description="Human-readable title for the name. Acts as a description.")
    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str):
        if len(v) != 1:
            raise ValueError(f"Modifier provided ({v}) must be a single character.")
        return v
