# SPDX-License-Identifier: BSD-3-Clause
"""Every regular expression whyqd runs, kept apart from the code that runs it, one class to each engine's syntax.

Polars runs Rust's `regex` crate (https://docs.rs/regex/latest/regex/#syntax), whose syntax is not Python's `re`:
`\\p{Cc}` and the class intersection `&&` are Rust's alone. A pattern lives in the class whose engine runs it.
"""

import re
from typing import ClassVar


class PolarsPatterns:
    """Patterns Polars runs, in the syntax of Rust's `regex` crate.

    A hard space is U+00A0, U+2007, or U+202F; a zero-width character U+200B to U+200D, U+2060, or U+FEFF; a control
    character any in Unicode's `Cc` but tab, line feed, and carriage return. A date-like text is three groups of digits
    split by `/`, `-`, or `.`, or an English month's name, whole or short, among digits and separators.
    """

    HARD_SPACE: ClassVar[str] = "[   ]"
    ZERO_WIDTH: ClassVar[str] = "[​-‍⁠﻿]"
    CONTROL: ClassVar[str] = r"[\p{Cc}&&[^\t\n\r]]"
    WHITESPACE: ClassVar[str] = r"^\s+$"
    DIGIT: ClassVar[str] = "[0-9]"
    ZERO_PADDED: ClassVar[str] = r"^0[0-9]+$"
    DATE: ClassVar[str] = r"^[0-9]+[/.-][0-9]+[/.-][0-9]+$"
    MONTH: ClassVar[str] = (
        r"(?i)^[0-9\s/.,-]*\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(t|tember)?"
        r"|oct(ober)?|nov(ember)?|dec(ember)?)\b\.?[0-9\s/.,-]*$"
    )


class PythonPatterns:
    """Patterns Python's `re` runs, compiled once."""

    # An error cell as fastexcel reports it, naming calamine's `CellErrorType`: `Error(Div0)`
    EXCEL_ERROR: ClassVar[re.Pattern] = re.compile(r"Error\((\w+)\)")
    # A cell's reference in a sheet, its column's letters and its row's number: `AB12`
    CELL_REFERENCE: ClassVar[re.Pattern] = re.compile(r"([A-Z]+)([0-9]+)")
    # A line of text with its end, `\r\n`, `\n`, or `\r`, as `io.StringIO(newline="")` splits it; the last may have none
    LINE: ClassVar[re.Pattern] = re.compile(r"[^\r\n]*(?:\r\n|\n|\r)|[^\r\n]+\Z")
    # A part of the row key, its name given by `RowKeyParser.ROW`: `__row__`, `__row__1`
    ROW_PART: ClassVar[str] = r"^{row}(\d*)$"
