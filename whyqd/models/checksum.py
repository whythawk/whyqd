# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import ConfigDict, BaseModel, Field

from whyqd.dtypes import ChecksumContent


class ChecksumModel(BaseModel):
    """A checksum in SPDX's shape, `algorithm` and `checksumValue`, with what it hashed."""

    algorithm: str = Field(..., description="SPDX's name for the hash algorithm, such as `BLAKE2b-512`.")
    checksumValue: str = Field(..., description="The digest, in lowercase hexadecimal.")
    content: ChecksumContent = Field(..., description="What was hashed.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
