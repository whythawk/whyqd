# SPDX-License-Identifier: BSD-3-Clause
from .format import FormatParser
from .core import CoreParser
from .script import ScriptParser
from .action import ActionParser
from .morph import MorphParser
from .category import CategoryParser


def __getattr__(name: str):
    # The reader loads the engine, which reading a definition must not
    if name == "ReadingParser":
        from .reading import ReadingParser

        return ReadingParser
    if name == "ConformanceParser":
        from .conformance import ConformanceParser

        return ConformanceParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
