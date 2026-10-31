# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

from whyqd.dtypes import CellType


class ProfileModel(BaseModel):
    """What a column holds, as read, in counts. Profiling never changes a cell."""

    cellTypes: dict[CellType, int] = Field({}, description="Cells of each type, as the reader found them.")
    blank: int = Field(0, ge=0, description="Empty cells.")
    whitespace: int = Field(0, ge=0, description="Cells holding only whitespace.")
    hardSpace: int = Field(0, ge=0, description="Cells holding a no-break space.")
    zeroWidth: int = Field(0, ge=0, description="Cells holding a zero-width character.")
    control: int = Field(0, ge=0, description="Cells holding a control character.")
    dateLike: int = Field(0, ge=0, description="Text cells that look like a date.")
    zeroPadded: int = Field(0, ge=0, description="Text cells holding a number with leading zeros.")
    numberFormats: dict[str, int] = Field(
        {}, description="Number and date cells by the format code an `.xlsx` stores for them; empty for other files."
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
