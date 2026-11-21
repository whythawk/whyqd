# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum, nonmember


class EncodingStep(str, Enum):
    """What settled a file's encoding, the steps a read takes in order."""

    BOM = "bom"
    DECLARED = "declared"
    UTF8 = "utf-8"
    WINDOWS_1252 = "windows-1252"

    DESCRIPTIONS = nonmember(
        {
            "bom": "The file opens with a byte-order mark naming its encoding, which overrides any declaration.",
            "declared": "Declared by the wrangler.",
            "utf-8": "The file decodes as strict UTF-8.",
            "windows-1252": "Read as windows-1252, which decodes any byte and loses none, since no other step settled it.",
        }
    )

    @property
    def describe(self) -> str:
        """What this value means."""
        return self.DESCRIPTIONS[self.value]
