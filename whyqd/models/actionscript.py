from __future__ import annotations
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ActionScriptModel(BaseModel):
    """Action Script Model - only action `script` string required."""

    uuid: UUID = Field(default_factory=uuid4, description="Unique identity for the Action. Automatically generated.")
    script: str = Field(..., description="An action script.")

    class Config:
        use_enum_values = True
        anystr_strip_whitespace = True
        validate_assignment = True
