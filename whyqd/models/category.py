# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Union, Optional
from pydantic import BaseModel, Field, StrictBool

from whyqd.models.identifier import Identifier


class CategoryModel(BaseModel):
    uuid: Identifier = Field(description="Unique identity for the category. Automatically generated.")
    # Little gotcha ... if bool is 2nd, then any bools are automatically coerced to string ... order is priority.
    # Second gotcha, Pydantic is quite liberal with what it classifies as bool https://docs.pydantic.dev/latest/usage/types/booleans/
    name: Union[StrictBool, str] = Field(..., description="Unique category term.")
    description: Optional[str] = Field(None, description="Description of the unique term")
    code: Optional[str] = Field(
        None, description="The term's code in its list, which identifies it where its label may change."
    )
