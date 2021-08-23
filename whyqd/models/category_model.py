from __future__ import annotations
from typing import Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class CategoryModel(BaseModel):
    uuid: UUID = Field(default_factory=uuid4, description="Unique identity for the category. Automatically generated.")
    # Little gotcha ... if bool is 2nd, then any bools are automatically coerced to string ... order is priority.
    name: Union[bool, str] = Field(..., description="Unique category term.")
    description: Optional[str] = Field(None, description="Description of the unique term")
