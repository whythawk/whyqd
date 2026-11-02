# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum


class FindingKind(str, Enum):
    FAULT = "fault"
    FACT = "fact"

    @property
    def describe(self):
        description = {
            "fault": "The file could not be read as written, or was read with a loss. Its owner may correct it, or a "
            "setting may read past it.",
            "fact": "Something the file holds, with no claim of what it means. What to do about it, if anything, is "
            "for the crosswalk.",
        }
        return description[self.value]


class SettingSource(str, Enum):
    DECLARED = "declared"
    DEFAULT = "default"
    FILE = "file"

    @property
    def describe(self):
        description = {
            "declared": "Declared by the wrangler.",
            "default": "Not declared, so its fixed default.",
            "file": "Settled by what the file shows, by a rule that never depends on anything else: an encoding's "
            "steps, for one.",
        }
        return description[self.value]
