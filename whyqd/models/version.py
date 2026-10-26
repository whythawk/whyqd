# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

from whyqd.models.utc import UtcParser, UtcTime


class VersionModel(BaseModel):
    name: Optional[str] = Field(None, description="Name of the person who modified the schema or method.")
    description: Optional[str] = Field(None, description="Description of what was done in this version.")
    updated: Optional[UtcTime] = Field(
        default_factory=UtcParser().now, description="When this version was made, in UTC."
    )
