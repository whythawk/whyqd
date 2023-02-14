from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from whyqd.metamodel.models import ConstraintsModel
from whyqd.metamodel.dtypes import FieldType


class FieldModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Unique identity for the field. Automatically generated.")
    name: str = Field(
        ...,
        description="Defined exactly as it appears in the source data. By convention, it should be a machine-readable term to uniquely address this field. Cannot have spaces. CamelCase or snake_case.",
    )
    title: Optional[str] = Field(None, description="A human-readable version of the field name.")
    description: Optional[str] = Field(None, description="A description for the field.")
    type_field: FieldType = Field(..., alias="type", description="A field must contain values of a specific type.")
    constraints: Optional[ConstraintsModel] = Field(
        None, description="A set of optional constraints to define the field."
    )
    missing: Optional[Any] = Field(default=None, description="Default to be used for missing values.")
    foreignKey: Optional[bool] = Field(
        default=False, description="Set `foreignKey` `true` if the field is to be treated as an immutable value."
    )

    class Config:
        use_enum_values = True
        anystr_strip_whitespace = True
        validate_assignment = True
