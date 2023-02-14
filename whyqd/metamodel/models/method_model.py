from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, validator, constr
from uuid import UUID, uuid4

from whyqd.metamodel.models import CitationModel, DataSourceModel, FieldModel, VersionModel


class MethodModel(BaseModel):
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
    schema_fields: List[FieldModel] = Field(
        default=[],
        description="A list of fields which define the schema. Fields, similarly, contain `name`, `title` and `description`, as well as `type` as compulsory.",
    )
    input_data: List[DataSourceModel] = Field(
        default=[],
        description="A list of source data wrangled to produce restructured data conforming to a defined schema.",
    )
    working_data: Optional[DataSourceModel] = Field(
        None,
        description="An interim dataset, derived from merged input data, to produce restructured data conforming to a defined schema.",
    )
    restructured_data: Optional[DataSourceModel] = Field(
        None,
        description="Final restructured dataset, according to all build actions, and conforming to a defined schema.",
    )
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")
    version: List[VersionModel] = Field(default=[], description="Version and update history for the method.")

    class Config:
        use_enum_values = True
        anystr_strip_whitespace = True
        validate_assignment = True

    @validator("name")
    def name_space(cls, v):
        return "_".join(v.split(" ")).lower()
