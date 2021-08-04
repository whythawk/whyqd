from typing import List, Optional
from pydantic import BaseModel, Field, validator
from pydantic.types import constr
from datetime import datetime
from uuid import UUID, uuid4

from .fields import FieldModel


class VersionModel(BaseModel):
    name: Optional[str] = Field(None, description="Name of the person who modified the schema.")
    updated: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Date generated on update.",
    )


class SchemaModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Automatically generated unique identity for the schema.")
    name: constr(strip_whitespace=True, to_lower=True) = Field(
        ...,
        description="Machine-readable term to uniquely address this schema. Cannot have spaces. CamelCase or snake_case.",
    )
    title: Optional[str] = Field(None, description="A human-readable version of the schema name.")
    description: Optional[str] = Field(
        None,
        description="A complete description of the schema. Depending on how complex your work becomes, try and be as helpful as possible to 'future-you'. You'll thank yourself later.",
    )
    fields: List[FieldModel] = Field(
        default=[],
        description="A list of fields which define the schema. Fields, similarly, contain `name`, `title` and `description`, as well as `type` as compulsory.",
    )
    version: List[VersionModel] = Field(default=[], description="Version and update history for the schema.")

    class Config:
        anystr_strip_whitespace = True

    @validator("name")
    def name_space(cls, v):
        if v.lower() != "_".join(v.split(" ")).lower():
            raise ValueError(f"Schema name ({v}) cannot have spaces and must be CamelCase or snake_case.")
        return "_".join(v.split(" ")).lower()

    @validator("fields")
    def are_fields_unique(cls, v):
        field_names = []
        for f in v:
            field_names.append(f.name)
        if len(field_names) != len(set(field_names)):
            raise ValueError(
                f"Field names must be unique. There are {len(field_names) - len(set(field_names))} duplications."
            )
        return v
