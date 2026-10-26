# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Optional

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import BaseModel, ConfigDict, Field, field_validator

from whyqd.dtypes import ExtensionKind


class ExtensionModel(BaseModel):
    """An action or type a definition uses that whyqd does not include, from the package that provides it.

    An extension is known by its package and its name together, since one name in two packages need not do the same
    thing. Its version is a range in the Python packaging standard's
    [version specifier](https://packaging.python.org/en/latest/specifications/version-specifiers/) syntax, such as
    `>=1.2.3,<2`; a transform records the exact version it ran, as `==1.2.3`.
    """

    name: str = Field(..., description="The action's or type's name, as a definition writes it.")
    kind: ExtensionKind = Field(..., description="Whether it is an action or a type.")
    distribution: str = Field(..., description="The installed package that provides it.")
    version: str = Field(..., description="The versions of that package the definition accepts.")
    iri: Optional[str] = Field(None, description="An IRI giving the extension's meaning.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @field_validator("version")
    @classmethod
    def is_specifier(cls, v: str) -> str:
        try:
            SpecifierSet(v)
        except InvalidSpecifier as e:
            raise ValueError(f"`{v}` is not a version specifier, such as `>=1.2.3,<2`.") from e
        return v
