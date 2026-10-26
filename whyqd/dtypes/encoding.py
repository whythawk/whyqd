# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum


class EncodingStep(str, Enum):
    BOM = "bom"
    UTF8 = "utf-8"
    DETECTED = "detected"
    LATIN1 = "latin-1"
    DECLARED = "declared"

    @property
    def describe(self):
        description = {
            "bom": "The file opens with a byte-order mark naming its encoding.",
            "utf-8": "The file decodes as strict UTF-8.",
            "detected": "Detected among a declared shortlist of encodings.",
            "latin-1": "Read as Latin-1, which decodes any byte and loses nothing, since no other step settled it.",
            "declared": "Declared by the wrangler.",
        }
        return description[self.value]
