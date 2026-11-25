# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field
from typing import List, Union, Optional, Type

from whyqd.models.fields import FieldModel
from whyqd.models.modifier import ModifierModel


class SchemaActionModel(BaseModel):
    """An action's definition: its name and purpose, and the structure its script takes, source fields and the
    modifiers acting on them."""

    name: str = Field(..., description="Name of the Action. Uppercase.")
    title: str = Field(..., description="Title of the Action. Regular case.")
    description: str = Field(..., description="Description of the purpose for performing this action.")
    structure: List[Union[str, Type[ModifierModel], Type[FieldModel]]] = Field(
        ...,
        description="The structure of an action depends on source column fields, and [optional] modifiers which act upon them.",
    )
    modifiers: Optional[List[ModifierModel]] = Field(
        None, description="The list of defined modifiers appropriate for this action."
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
