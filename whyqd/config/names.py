# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import json
from pathlib import Path
from typing import ClassVar


class NameTables:
    """The month, weekday, and day-period names whyqd reads, per language, fixed in `names.json`, an extract of Unicode's
    [CLDR](https://cldr.unicode.org/), so a date depends on no library's version and no machine's locale."""

    SOURCE: ClassVar[Path] = Path(__file__).resolve().with_name("names.json")
    held: ClassVar[dict | None] = None

    @classmethod
    def language(cls, tag: str) -> dict | None:
        """A language's names, by its tag (`de`, `pt`), or `None` where whyqd holds none."""
        if cls.held is None:
            cls.held = json.loads(cls.SOURCE.read_text(encoding="utf-8"))["languages"]
        return cls.held.get(tag)
