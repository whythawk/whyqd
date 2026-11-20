# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar, Optional, Union
from pydantic import ConfigDict, BaseModel, Field, model_validator

from whyqd.models.identifier import Identifier
from whyqd.models.policy import PolicyModel
from whyqd.models.reason import ReasonModel
from whyqd.models.reference import ReferenceModel


class ActionScriptModel(BaseModel):
    """Action Script Model - only action `script` string required."""

    ONE_OUTPUT: ClassVar[frozenset[str]] = frozenset({"UNITE", "NEW"})
    OUTPUTS: ClassVar[frozenset[str]] = frozenset({"SEPARATE"})

    uuid: Identifier = Field(description="Unique identity for the Action. Automatically generated.")
    script: str = Field(..., description="An action script.")
    reason: Optional[ReasonModel] = Field(None, description="Why the step holds, covering every mapping in it.")
    correspondence: Optional[ReferenceModel] = Field(
        None, description="The versioned correspondence a `CATEGORISE` step cites for its mappings."
    )
    policy: Optional[Union[PolicyModel, dict[str, PolicyModel]]] = Field(
        None,
        description="How to read the text the step builds: one policy for `UNITE` and `NEW`, and for `SEPARATE` one "
        "per destination field it writes.",
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @model_validator(mode="after")
    def policy_builds_text(self) -> ActionScriptModel:
        if self.policy is None:
            return self
        action = self.script.split(">")[0].strip()
        if action not in self.ONE_OUTPUT | self.OUTPUTS:
            raise ValueError(
                f"`{action}` builds no text, so a format goes on the source field it reads. Move the `policy` there. "
                "[whyqd:policy-on-action]"
            )
        if isinstance(self.policy, dict) != (action in self.OUTPUTS):
            raise ValueError(
                f"`{action}` needs {'one policy per destination field' if action in self.OUTPUTS else 'one policy'}, "
                "as it writes that many outputs. Change its `policy`. [whyqd:policy-on-action]"
            )
        return self

    @model_validator(mode="after")
    def correspondence_categorises(self) -> ActionScriptModel:
        if self.correspondence and self.script.split(">")[0].strip() != "CATEGORISE":
            raise ValueError(f"Only a `CATEGORISE` step cites a correspondence, not `{self.script}`.")
        return self
