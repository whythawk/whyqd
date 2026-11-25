# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from whyqd.dtypes import FindingKind, MimeType, Place, SettingSource
from whyqd.models.policy import PolicyModel

SettingValue = Union[bool, int, str, list[int], None]


class SettingModel(BaseModel):
    """One reading setting, as a read used it."""

    name: str = Field(..., description="The setting's name in the dialect.")
    value: SettingValue = Field(None, description="The value the read used.")
    source: SettingSource = Field(..., description="Where the value came from.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)


class FindingModel(BaseModel):
    """Something found in a file, shaped as a compiler's diagnostic is: a stable code with a page of its own, what was
    found, where, and, for a fault, what addresses it. A code is shared with the refusal or warning for the same thing.
    """

    code: str = Field(..., description="Short, stable, and kebab-case, naming the finding's documentation page.")
    kind: FindingKind = Field(..., description="A fault in the file, or a plain fact about it.")
    message: str = Field(..., description="What was found and where, without its code.")
    rows: list[int] = Field(
        [],
        description="The rows concerned: a text file's lines or a sheet's rows, from 1; or for a transform, the row "
        "keys, from 0, that `DELETE_ROWS` names.",
    )
    columns: list[int] = Field([], description="The columns concerned, by position in the grid, from 0.")
    cells: list[str] = Field([], description="The cells or ranges concerned, as a workbook names them: `B2:C3`.")
    setting: Optional[str] = Field(None, description="For a fault, the setting or policy slot that addresses it.")
    field: Optional[str] = Field(None, description="The schema field concerned, for a typing or constraint finding.")
    shape: Optional[str] = Field(None, description="The form the cells share, such as `#-9999.99`.")
    count: Optional[int] = Field(None, ge=0, description="How many cells have this shape; `rows` holds the first.")
    step: Optional[int] = Field(
        None, ge=0, description="The crosswalk step concerned, by its place among the crosswalk's steps, from 0."
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    def __str__(self) -> str:
        return f"{self.message} [whyqd:{self.code}]"


class ProposalModel(BaseModel):
    """A setting, or a field's whole policy, with what supports it. Never applied: it takes effect only when the
    wrangler declares it."""

    setting: str = Field(
        ...,
        description="The setting's name in the dialect, `policy` for a field's whole policy, or `drop` for a crosswalk "
        "step to leave out.",
    )
    field: Optional[str] = Field(None, description="The schema field the setting is for, if it is not the dialect's.")
    value: SettingValue | PolicyModel = Field(
        None, description="The value proposed: a setting's value, or the policy the field was read under."
    )
    evidence: str = Field(..., description="What in the file supports it.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @field_serializer("value")
    def as_declared(self, value: SettingValue | PolicyModel):
        """A policy written as a definition saves one, its defaults left out, so it can be declared as it stands."""
        if isinstance(value, PolicyModel):
            return value.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        return value


class CrosswalkReportModel(BaseModel):
    """The steps of a saved crosswalk that loading it would refuse, and, where asked, the steps to leave out so it
    loads. Computed when asked, never stored on a definition."""

    name: str = Field(..., description="The crosswalk's name.")
    findings: list[FindingModel] = Field([], description="Each refused step, by its place in `step`.")
    proposals: list[ProposalModel] = Field([], description="Steps proposed to leave out, where the wrangler asked.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)


class ReportModel(BaseModel):
    """How one file, or one sheet of a workbook, was read, and what was found there. Computed when asked, never stored
    on a definition."""

    path: str = Field(..., description="The file read.")
    mime: MimeType = Field(..., description="The file's format.")
    sheet: Optional[str] = Field(None, description="The sheet read, in a workbook.")
    place: Place = Field(Place.LINE, description="What `rows` counts: a text file's `line`, a sheet's `row`.")
    settings: list[SettingModel] = Field(
        [], description="Each setting the read used. Empty where the file could not be read."
    )
    height: int = Field(0, ge=0, description="Rows in the grid.")
    width: int = Field(0, ge=0, description="Columns in the grid.")
    rowWidths: dict[int, int] = Field(
        {},
        description="The grid's rows by how far each reaches: its last filled cell, counted from 1, so `0` is a blank "
        "row. Evidence of a file's shape, with no claim of what it means.",
    )
    findings: list[FindingModel] = Field([], description="What was found, faults first.")
    proposals: list[ProposalModel] = Field([], description="Settings proposed, where the wrangler asked for them.")
    preview: Optional[str] = Field(None, description="A short text of the grid as read, each row numbered by `place`.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
