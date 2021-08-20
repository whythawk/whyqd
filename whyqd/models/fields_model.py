from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field, validator
from pydantic.types import constr
from uuid import UUID, uuid4

from ..models import ConstraintsModel
from ..types import FieldType


class FieldModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Unique identity for the field. Automatically generated.")
    name: constr(strip_whitespace=True, to_lower=True) = Field(
        ...,
        description="Machine-readable term to uniquely address this field. Cannot have spaces. CamelCase or snake_case.",
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

    @validator("name")
    def name_space(cls, v):
        return "_".join(v.split(" ")).lower()
