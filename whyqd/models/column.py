from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field, field_validator
from uuid import UUID, uuid4

from whyqd.dtypes import FieldType


class ColumnModel(BaseModel):
    """Pandas DataFrame column model for maintaining source reference. Necessary to perform term matching in
    parsing operations (there can be some *really* fruity column names."""

    uuid: UUID = Field(default_factory=uuid4, description="Unique identity for the column. Automatically generated.")
    name: str = Field(
        ...,
        description="Column label / name from source data. In whatever format it was written, including leading/lagging spaces, non-printing characters, etc.",
    )
    dtype: FieldType = Field(
        default=FieldType.STRING,
        alias="type",
        description="A column must contain values of a specific type. Default is 'string'.",
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True, populate_by_name=True)

    @field_validator("dtype", mode="before")
    @classmethod
    def generate_dtype(cls, v: FieldType):
        if v in ["float64", "int64", "Float64", "Int64", FieldType.NUMBER.value]:
            return FieldType.NUMBER
        if v in ["datetime64[ns]", FieldType.DATETIME.value]:
            return FieldType.DATETIME
        return FieldType.STRING
