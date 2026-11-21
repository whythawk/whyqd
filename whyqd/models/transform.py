# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field
from typing import Optional

from whyqd.models.citation import CitationModel
from whyqd.models.crosswalk import CrosswalkModel
from whyqd.models.datasource import DataSourceModel
from whyqd.models.extension import ExtensionModel
from whyqd.models.identifier import DefinitionName, Identifier
from whyqd.models.reference import UsedReferenceModel
from whyqd.models.utc import UtcTime
from whyqd.models.version import VersionModel


class TransformModel(BaseModel):
    """A crosswalk applied to a data source: the source, the crosswalk, the destination it built, and when, and with
    which whyqd, references, and extensions, it ran."""

    uuid: Identifier = Field(description="Automatically generated unique identity for the method.")
    name: DefinitionName = Field(
        ...,
        description="Machine-readable term to address this transform: trimmed, lower case, its spaces underscores.",
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
