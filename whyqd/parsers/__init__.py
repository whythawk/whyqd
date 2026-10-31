# SPDX-License-Identifier: BSD-3-Clause
from .format import FormatParser
from .core import CoreParser
from .script import ScriptParser
from .action import ActionParser
from .morph import MorphParser
from .category import CategoryParser
from .cell import CellParser
from .column import ColumnParser
from .fingerprint import FingerprintParser
from .row_key import RowKeyParser


def __getattr__(name: str):
    # The reader loads the engine, which reading a definition must not
    if name == "DataSourceParser":
        from .datasource import DataSourceParser

        return DataSourceParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
