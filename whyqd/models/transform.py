from __future__ import annotations
from pydantic import BaseModel, Field, validator, constr
from typing import Optional
from uuid import UUID, uuid4

from whyqd.models import CitationModel, DataSourceModel, CrosswalkModel, VersionModel


class TransformModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Automatically generated unique identity for the method.")
    name: constr(strip_whitespace=True, to_lower=True) = Field(
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
    version: list[VersionModel] = Field(default=[], description="Version and update history for the method.")

    class Config:
        use_enum_values = True
        # anystr_strip_whitespace = True
        validate_assignment = True

    @validator("name")
    def name_space(cls, v):
        return "_".join(v.split(" ")).lower()
