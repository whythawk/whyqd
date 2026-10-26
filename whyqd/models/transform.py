# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import field_validator, StringConstraints, ConfigDict, BaseModel, Field
from typing import Annotated, Optional

from whyqd.models import (
    CitationModel,
    CrosswalkModel,
    DataSourceModel,
    ExtensionModel,
    UsedReferenceModel,
    VersionModel,
)
from whyqd.models.identifier import Identifier
from whyqd.models.utc import UtcTime


class TransformModel(BaseModel):
    uuid: Identifier = Field(description="Automatically generated unique identity for the method.")
    name: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True)] = Field(
        ...,
        description="Machine-readable term to uniquely address this method. Cannot have spaces. CamelCase or snake_case.",
    )
    title: Optional[str] = Field(None, description="A human-readable version of the method name.")
    description: Optional[str] = Field(
        None,
        description="A complete description of the method. Depending on how complex your work becomes, try and be as helpful as possible to 'future-you'. You'll thank yourself later.",
    )
    dataSource: Optional[DataSourceModel] = Field(
        None,
        description="Tabular source data defined by the crosswalk source schema to produce destination data conforming to a destination schema.",
    )
    dataDestination: Optional[DataSourceModel] = Field(
        None,
        description="Tabular source data defined by the crosswalk destination schema and resulting from execution of the crosswalk.",
    )
    crosswalk: Optional[CrosswalkModel] = Field(
        None,
        description="A method defining the source schema to destination schema crosswalk to be applied to tabular source data.",
    )
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the transform.")
    started: Optional[UtcTime] = Field(None, description="When the transform last ran, in UTC.")
    ended: Optional[UtcTime] = Field(None, description="When that run ended, in UTC.")
    whyqd: Optional[str] = Field(None, description="The version of whyqd that ran it.")
    references: list[UsedReferenceModel] = Field(
        [], description="The versioned sources the run used, such as term lists, with checksums of their content."
    )
    extensions: list[ExtensionModel] = Field(
        [], description="The extensions the run used, each at the exact version that ran (`==1.2.3`)."
    )
    version: list[VersionModel] = Field(default=[], description="Version and update history for the method.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @field_validator("name")
    @classmethod
    def name_space(cls, v: str):
        return "_".join(v.split(" ")).lower()
