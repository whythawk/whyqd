# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from whyqd.models.reference import ReferenceModel


class ReasonModel(BaseModel):
    """Why a crosswalk step holds, in the terms of an SSSOM mapping's justification
    ([SSSOM data model](https://github.com/mapping-commons/sssom/blob/9287d104437ad702fa4e74b1ea2b42a879b877ae/src/docs/spec-model.md)).
    It covers every mapping in its step.

    The justification is a term from the
    [Semantic Mapping Vocabulary](https://mapping-commons.github.io/semantic-mapping-vocabulary/), recording whether a
    person or a tool made the judgement: `semapv:ManualMappingCuration` for a wrangler's own, `semapv:MappingReview`
    for a check of someone else's.
    """

    justification: str = Field("semapv:ManualMappingCuration", description="How the mapping was justified.")
    comment: Optional[str] = Field(None, description="The reason, in words.")
    author: list[str] = Field([], description="Who made the mapping, by name or identifier.")
    date: Optional[datetime.date] = Field(None, description="When the mapping was made.")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="How sure the author is, from 0 to 1.")
    seeAlso: list[str] = Field([], description="Where more can be read, by URI.")
    reference: Optional[ReferenceModel] = Field(None, description="The versioned source the mapping relies on.")
    model_config = ConfigDict(validate_assignment=True)
