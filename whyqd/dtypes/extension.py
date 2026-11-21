# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum


class ExtensionKind(str, Enum):
    """What an installed extension adds to whyqd: an action, or a field type."""

    ACTION = "action"
    TYPE = "type"

    @property
    def group(self) -> str:
        """The entry point group an extension of this kind registers in."""
        return f"whyqd.{self.value}s"
