# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import warnings
from pydantic import ConfigDict, BaseModel, Field, model_validator
from typing import Optional

from whyqd.models.constraints import ConstraintsModel
from whyqd.models.identifier import Identifier
from whyqd.models.policy import PolicyModel
from whyqd.models.reference import ReferenceModel
from whyqd.dtypes import FieldFamilies, FieldType


class FieldModel(BaseModel):
    """One field of a schema: its name and type, what its values must meet, and, for a type read from text, how to read
    it (`policy`)."""

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

    @model_validator(mode="after")
    def policy_fits(self) -> FieldModel:
        if self.policy:
            self.policy.standardise(dtype=self.dtype)
            self.policy.check(name=self.name, dtype=self.dtype)
        return self

    @model_validator(mode="after")
    def usdate_deprecated(self) -> FieldModel:
        # A 1.x definition's `usdate` is a `date` once read, so only a current one declares it
        if self.dtype == FieldType.USDATE.value:
            warnings.warn(
                f"Field `{self.name}` is `usdate`, kept for 1.x definitions. Declare it `date` with a month-first "
                "`policy`, such as `MM/dd/yyyy`. [whyqd:usdate-deprecated]",
                FutureWarning,
                stacklevel=2,
            )
        return self

    @model_validator(mode="after")
    def zero_fits(self) -> FieldModel:
        if self.constraints and self.constraints.zeroAsTrue and self.dtype not in FieldFamilies.NUMBERS:
            raise ValueError(
                f"Field `{self.name}` is `{self.dtype}`, which holds no zero, so `zeroAsTrue` cannot apply. Remove it, "
                "or change the field's type. [whyqd:constraint-zero-as-true]"
            )
        return self
