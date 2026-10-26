# SPDX-License-Identifier: BSD-3-Clause
import os
import time
from typing import Annotated
from uuid import UUID

from pydantic import Field


class IdentifierParser:
    """Identifiers for definitions and their parts: UUIDv7, as the IETF's UUID standard defines it
    ([RFC 9562, section 5.7](https://www.rfc-editor.org/rfc/rfc9562#section-5.7)).

    A UUIDv7 opens with the Unix time in milliseconds, so identifiers sort by when they were made, as bytes and as
    text. The standard fills the remaining 74 bits with random data, offering a counter only as an option for order
    within one millisecond. whyqd uses random data alone: an identifier says what something is, not where it falls
    among others made in the same millisecond.

    Python's `uuid.uuid7()` exists only from 3.14; this gives the same layout on every Python whyqd supports.

    Example:
      ```python
      from whyqd.models.identifier import IdentifierParser

      identifier = IdentifierParser()
      identifier.new()  # UUID('019a2f6c-…'), version 7
      ```

    A model takes one through `Identifier`, its `uuid` field's type. An identifier read from a saved definition is
    kept as written, so a 1.x definition keeps its UUIDv4s.
    """

    _VERSION = 7 << 76
    _VARIANT = 0b10 << 62

    def new(self) -> UUID:
        """A new UUIDv7."""
        value = (time.time_ns() // 1_000_000 & (1 << 48) - 1) << 80 | int.from_bytes(os.urandom(10))
        value = value & ~(0xF << 76) | self._VERSION
        value = value & ~(0b11 << 62) | self._VARIANT
        return UUID(int=value)


Identifier = Annotated[UUID, Field(default_factory=IdentifierParser().new)]
