# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Optional
from pydantic import ConfigDict, BaseModel, Field, model_validator

from whyqd.models.identifier import Identifier
from whyqd.models.reason import ReasonModel
from whyqd.models.reference import ReferenceModel


class ActionScriptModel(BaseModel):
    """Action Script Model - only action `script` string required."""

    uuid: Identifier = Field(description="Unique identity for the Action. Automatically generated.")
    script: str = Field(..., description="An action script.")
    reason: Optional[ReasonModel] = Field(None, description="Why the step holds, covering every mapping in it.")
    correspondence: Optional[ReferenceModel] = Field(
        None, description="The versioned correspondence a `CATEGORISE` step cites for its mappings."
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @model_validator(mode="after")
    def correspondence_categorises(self) -> ActionScriptModel:
        if self.correspondence and self.script.split(">")[0].strip() != "CATEGORISE":
            raise ValueError(f"Only a `CATEGORISE` step cites a correspondence, not `{self.script}`.")
        return self
