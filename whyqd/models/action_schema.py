from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field  # , validator
from typing import List, Union, Optional, Type  # , Any

from whyqd.models.fields import FieldModel
from whyqd.models.modifier import ModifierModel


class SchemaActionModel(BaseModel):
    """Action Model - generated from the Action module."""

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

    # @validator("text_structure")
    # def check_valid_models(cls, v):
    #     for m in v:
    #         if not (m in ["modifier", "field", "value"]):
    #             raise ValueError(
    #                 "Structure must be of either ModifierModel or ColumnModel, or - in the case of `NEW` actions - a `value` assignment."
    #             )
    #     return v

    # @property
    # def structure(self):
    #     return [ModifierModel if s == "modifier" else ColumnModel if s == "field" else Any for s in self.text_structure]
