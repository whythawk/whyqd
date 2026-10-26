# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

from whyqd.models.checksum import ChecksumModel


class ReferenceModel(BaseModel):
    """A versioned source a definition relies on: a term list, a correspondence, or what a reason cites.

    The pair is SSSOM's source and source version (`subject_source`, `subject_source_version`, in the
    [SSSOM data model](https://github.com/mapping-commons/sssom/blob/9287d104437ad702fa4e74b1ea2b42a879b877ae/src/docs/spec-model.md)).
    The version is required, since a
    definition pins what it relies on and never follows a list's current version.
    """

    source: str = Field(..., description="The source's IRI, or its path where it is private.")
    version: str = Field(..., description="The version relied on.")
    model_config = ConfigDict(validate_assignment=True)


class UsedReferenceModel(ReferenceModel):
    """A versioned source as a transform used it, with checksums of its content, since a public list can change
    under one address and version."""

    checksums: list[ChecksumModel] = Field([], description="Checksums of the source's content, as used.")
