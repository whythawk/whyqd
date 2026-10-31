# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Optional
from pydantic import ConfigDict, BaseModel, Field

from whyqd.dtypes import FieldType
from whyqd.models.identifier import Identifier
from whyqd.models.profile import ProfileModel


class ColumnModel(BaseModel):
    """A data source's column, by its name as the source writes it, typed in whyqd's types only."""

    uuid: Identifier = Field(description="Unique identity for the column. Automatically generated.")
    name: str = Field(
        ...,
        description="Column label / name from source data. In whatever format it was written, including leading/lagging spaces, non-printing characters, etc.",
    )
    dtype: FieldType = Field(
        default=FieldType.STRING,
        alias="type",
        description="A column must contain values of a specific type. Default is 'string'.",
    )
    profile: Optional[ProfileModel] = Field(None, description="What the column holds, as read, in counts.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True, populate_by_name=True)
