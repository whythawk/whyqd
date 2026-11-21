# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field
from typing import Optional

from whyqd.models.actionscript import ActionScriptModel
from whyqd.models.citation import CitationModel
from whyqd.models.extension import ExtensionModel
from whyqd.models.identifier import DefinitionName, Identifier
from whyqd.models.schema import SchemaModel
from whyqd.models.version import VersionModel


class CrosswalkModel(BaseModel):
    """How a source schema maps onto a destination schema: action scripts, run in order, each taking source fields to
    destination fields."""

    uuid: Identifier = Field(description="Automatically generated unique identity for the crosswalk.")
    name: DefinitionName = Field(
        ...,
        description="Machine-readable term to address this crosswalk: trimmed, lower case, its spaces underscores.",
    )
    title: Optional[str] = Field(None, description="A human-readable version of the crosswalk name.")
    description: Optional[str] = Field(
        None,
        description="A complete description of the crosswalk. Depending on how complex your work becomes, try and be as helpful as possible to 'future-you'. You'll thank yourself later.",
    )
    schemaSource: Optional[SchemaModel] = Field(
        None,
        description="The source schema which the crosswalk will transform from.",
    )
    schemaDestination: Optional[SchemaModel] = Field(
        None,
        description="The destination schema which the crosswalk will transform to.",
    )
    actions: list[ActionScriptModel] = Field(
        default=[],
        description="List of Actions in script format to be performed on these data, in this order. Will be parsed and validated separately.",
    )
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")
    extensions: list[ExtensionModel] = Field([], description="The extension actions the crosswalk's steps use.")
    version: list[VersionModel] = Field(default=[], description="Version and update history for the crosswalk.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
