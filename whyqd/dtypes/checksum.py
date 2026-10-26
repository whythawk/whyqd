# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum


class ChecksumContent(str, Enum):
    """What a checksum hashed. The algorithm is named beside it, as SPDX names it."""

    TABLE_1X = "table-1x"  # the table as whyqd 1.x printed it through pandas
    FP0 = "fp0"
    BYTES = "bytes"
    DEFINITION = "definition"  # a definition's canonical JSON (RFC 8785), without its edit history
