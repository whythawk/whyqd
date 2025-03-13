from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4

from whyqd.models.constraints import ConstraintsModel
from whyqd.dtypes import FieldType


class FieldModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Unique identity for the field. Automatically generated.")
    name: str = Field(
        ...,
        description="Defined exactly as it appears in the source data. By convention, it should be a machine-readable term to uniquely address this field. Should not have spaces. CamelCase or snake_case for preference.",
    )
    title: Optional[str] = Field(None, description="A human-readable version of the field name.")
    description: Optional[str] = Field(None, description="A description for the field.")
    dtype: FieldType = Field(..., alias="type", description="A field must contain values of a specific type.")
    example: Optional[str] = Field(None, description="An example value, as a string, for the field.")
    constraints: Optional[ConstraintsModel] = Field(
        None, description="A set of optional constraints to define the field."
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True, populate_by_name=True)
