from __future__ import annotations
from pydantic import field_validator, StringConstraints, ConfigDict, BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4

from whyqd.models import CitationModel, ActionScriptModel, SchemaModel, VersionModel
from typing_extensions import Annotated


class CrosswalkModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Automatically generated unique identity for the crosswalk.")
    name: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True)] = Field(
        ...,
        description="Machine-readable term to uniquely address this crosswalk. Cannot have spaces. CamelCase or snake_case for preference.",
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
        description="List of Actions in script format to be performed on these data, in this order. Will be parsed and validated seperately.",
    )
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")
    version: list[VersionModel] = Field(default=[], description="Version and update history for the crosswalk.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @field_validator("name")
    @classmethod
    def name_space(cls, v: str):
        return "_".join(v.split(" ")).lower()
