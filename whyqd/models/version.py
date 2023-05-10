from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VersionModel(BaseModel):
    name: Optional[str] = Field(None, description="Name of the person who modified the schema or method.")
    description: Optional[str] = Field(None, description="Description of what was done in this version.")
    updated: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Date generated on update.",
    )
