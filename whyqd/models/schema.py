# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import field_validator, ConfigDict, BaseModel, Field, ValidationInfo
from typing import List, Optional, Union

from whyqd.models.citation import CitationModel
from whyqd.models.extension import ExtensionModel
from whyqd.models.fields import FieldModel
from whyqd.models.identifier import DefinitionName, Identifier
from whyqd.models.version import VersionModel


class SchemaModel(BaseModel):
    uuid: Identifier = Field(description="Automatically generated unique identity for the schema.")
    name: DefinitionName = Field(
        ...,
        description="Machine-readable term to uniquely address this schema. Cannot have spaces. CamelCase or snake_case for preference.",
    )
    title: Optional[str] = Field(None, description="A human-readable version of the schema name.")
    release: Optional[str] = Field(
        None,
        description="A name for this copy of the schema, for people, such as `2026 relief categories`. It orders "
        "nothing: the edit history's latest `updated` says which copy came first.",
    )
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
        description="A 1.x schema's row count, kept to save it as 1.x. It bounds nothing: a row-level action's rows are checked against its data source's `index`.",
    )
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")
    extensions: list[ExtensionModel] = Field([], description="The extension types the schema's fields use.")
    version: List[VersionModel] = Field(default=[], description="Version and update history for the schema.")
    model_config = ConfigDict(validate_assignment=True)

    @field_validator("fields")
    @classmethod
    def are_fields_unique(cls, v: List[FieldModel], info: ValidationInfo):
        names = [f.name for f in v]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError(
                f"Schema `{info.data.get('name')}` names fields {', '.join(f'`{name}`' for name in repeated)} more than "
                "once. Rename or remove the repeats. [whyqd:field-repeated]"
            )
        return v
