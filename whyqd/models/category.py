from __future__ import annotations
from typing import Union, Optional
from pydantic import BaseModel, Field, StrictBool
from uuid import UUID, uuid4


class CategoryModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Unique identity for the category. Automatically generated.")
    # Little gotcha ... if bool is 2nd, then any bools are automatically coerced to string ... order is priority.
    # Second gotcha, Pydantic is quite liberal with what it classifies as bool https://docs.pydantic.dev/latest/usage/types/booleans/
    name: Union[StrictBool, str] = Field(..., description="Unique category term.")
    description: Optional[str] = Field(None, description="Description of the unique term")
