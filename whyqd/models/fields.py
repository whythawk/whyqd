# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field
from typing import Optional

from whyqd.models.constraints import ConstraintsModel
from whyqd.models.identifier import Identifier
from whyqd.models.policy import PolicyModel
from whyqd.models.reference import ReferenceModel
from whyqd.dtypes import FieldType


class FieldModel(BaseModel):
    uuid: Identifier = Field(description="Unique identity for the field. Automatically generated.")
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
    policy: Optional[PolicyModel] = Field(None, description="How to read the field's text as its type.")
    termList: Optional[ReferenceModel] = Field(
        None, description="The versioned term list the field's categories come from, taking precedence over `enum`."
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True, populate_by_name=True)
