# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import field_validator, StringConstraints, ConfigDict, BaseModel, Field
from typing import Annotated, List, Optional, Union

from whyqd.models import ExtensionModel, FieldModel, VersionModel, CitationModel
from whyqd.models.identifier import Identifier


class SchemaModel(BaseModel):
    uuid: Identifier = Field(description="Automatically generated unique identity for the schema.")
    name: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True)] = Field(
        ...,
        description="Machine-readable term to uniquely address this schema. Cannot have spaces. CamelCase or snake_case for preference.",
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
    missingValues: list[str] = Field(
        default=[],
        description="Indicates which string values should be treated as null values. There could be a variety of these, such as '..', or '-'.",
    )
    primaryKey: Optional[Union[list[str], str]] = Field(
        default=None,
        description="A field or set of fields which uniquely identifies each row in the table. Specify using the `name` of relevant fields.",
    )
    index: Optional[int] = Field(
        None,
        description="Maximum value of a zero-base index for tabular data defined by this schema. Necessary where `actions` apply row-level transforms.",
    )
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")
    extensions: list[ExtensionModel] = Field([], description="The extension types the schema's fields use.")
    version: List[VersionModel] = Field(default=[], description="Version and update history for the schema.")
    model_config = ConfigDict(validate_assignment=True)

    @field_validator("name")
    @classmethod
    def name_space(cls, v: str):
        return "_".join(v.split(" ")).lower()

    @field_validator("fields")
    @classmethod
    def are_fields_unique(cls, v: List[FieldModel]):
        field_names = []
        for f in v:
            field_names.append(f.name)
        if len(field_names) != len(set(field_names)):
            raise ValueError(
                f"Field names must be unique. There are {len(field_names) - len(set(field_names))} duplications."
            )
        return v
