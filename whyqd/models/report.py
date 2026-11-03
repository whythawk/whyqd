# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from whyqd.dtypes import FindingKind, MimeType, SettingSource

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
    rows: list[int] = Field([], description="The rows concerned: a text file's lines or a sheet's rows, from 1.")
    columns: list[int] = Field([], description="The columns concerned, by position in the grid, from 0.")
    cells: list[str] = Field([], description="The cells or ranges concerned, as a workbook names them: `B2:C3`.")
    setting: Optional[str] = Field(None, description="For a fault, the setting or policy slot that addresses it.")
    field: Optional[str] = Field(None, description="The schema field concerned, for a typing or constraint finding.")
    shape: Optional[str] = Field(None, description="The form the cells share, such as `#-9999.99`.")
    count: Optional[int] = Field(None, ge=0, description="How many cells have this shape; `rows` holds the first.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    def __str__(self) -> str:
        return f"{self.message} [whyqd:{self.code}]"


class ProposalModel(BaseModel):
    """A setting that would read past a fault. Never applied: it takes effect only when the wrangler declares it."""

    setting: str = Field(..., description="The setting's name in the dialect, or the slot in a field's policy.")
    field: Optional[str] = Field(None, description="The schema field the setting is for, if it is not the dialect's.")
    value: SettingValue = Field(None, description="The value proposed.")
    evidence: str = Field(..., description="What in the file supports it.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)


class ReportModel(BaseModel):
    """How one file, or one sheet of a workbook, was read, and what was found there. Computed when asked, never stored
    on a definition."""

    path: str = Field(..., description="The file read.")
    mime: MimeType = Field(..., description="The file's format.")
    sheet: Optional[str] = Field(None, description="The sheet read, in a workbook.")
    place: str = Field("line", description="What `rows` counts: a text file's `line`, a sheet's `row`.")
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
