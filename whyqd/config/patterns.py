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

    HARD_SPACE: ClassVar[str] = "[\u00a0\u2007\u202f]"
    ZERO_WIDTH: ClassVar[str] = "[\u200b-\u200d\u2060\ufeff]"
    CONTROL: ClassVar[str] = r"[\p{Cc}&&[^\t\n\r]]"
    WHITESPACE: ClassVar[str] = r"^\s+$"
    DIGIT: ClassVar[str] = "[0-9]"
    ZERO_PADDED: ClassVar[str] = r"^0[0-9]+$"
    DATE: ClassVar[str] = r"^[0-9]+[/.-][0-9]+[/.-][0-9]+$"
    # What reading a cell removes or changes: the bidirectional marks LRM, RLM, and ALM; minus-like characters NFKC
    # leaves; a digit of another script; a character NFKC would turn into a digit of its number
    BIDI_MARKS: ClassVar[str] = "\u200e\u200f\u061c"
    BIDI: ClassVar[str] = f"[{BIDI_MARKS}]"
    MINUS: ClassVar[str] = "[‐‑‒–—−]"
    OTHER_DIGIT: ClassVar[str] = r"[\p{Nd}&&[^0-9]]"
    NUMBER_FORM: ClassVar[str] = r"\p{No}"
    ANY_DIGIT: ClassVar[str] = r"\p{Nd}"
    NON_FINITE: ClassVar[str] = r"^(NaN|-?INF)$"
    LEADING_MINUS: ClassVar[str] = r"^-\s*"
    BRACKETED: ClassVar[str] = r"^\(.*\)$"
    TRAILING_MINUS: ClassVar[str] = r"[0-9]\s*-$"
    FRACTION: ClassVar[str] = r"\.[0-9]*$"
    WHOLE: ClassVar[str] = r"^-?[0-9]+(?:\.0*)?$"
    SIGN_OR_POINT: ClassVar[str] = r"[-.]"
    # What a number field reads undeclared: a currency mark of Unicode's category `Sc`, or the mojibake of `£`; the
    # last of its marks, `.` or `,`, with the digits after it; a lone mark that could be either, a group of three after
    # one to three digits; and two runs of digits split only by a space, which may be a group mark or two numbers
    CURRENCY: ClassVar[str] = r"¬£|\p{Sc}"
    LAST_MARK: ClassVar[str] = r"([.,])[0-9]*$"
    EITHER_MARK: ClassVar[str] = r"^[1-9][0-9]{0,2}[.,][0-9]{3}$"
    SPACED: ClassVar[str] = r"[0-9]\s+[0-9]"
    SPACE: ClassVar[str] = r"\s"
    # A date's shapes that read undeclared: day and month as numbers in either order, each separator captured, since
    # Rust's `regex` has no backreference to require the same one twice; digits run together as `yyyyMMdd`; and a
    # day, a month's name, and a year, either of the first two first, once commas are spaces
    DATE_ORDER: ClassVar[str] = r"^([0-9]{1,2})([/.-])([0-9]{1,2})([/.-])([0-9]{4})$"
    DATE_RUN: ClassVar[str] = r"^([0-9]{4})([0-9]{2})([0-9]{2})$"
    DAY_NAME: ClassVar[str] = r"^([0-9]+)\s+(\S+)\s+([0-9]{4})$"
    NAME_DAY: ClassVar[str] = r"^(\S+)\s+([0-9]+)\s+([0-9]{4})$"
    COMMA: ClassVar[str] = ","
    MONTH: ClassVar[str] = (
        r"(?i)^[0-9\s/.,-]*\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|june?|july?|aug(ust)?|sep(t|tember)?"
        r"|oct(ober)?|nov(ember)?|dec(ember)?)\b\.?[0-9\s/.,-]*$"
    )

    # An ISO 8601 duration of days, hours, minutes, and seconds, each captured, with no years or months
    DURATION: ClassVar[str] = r"^(-)?P(?:([0-9]+)D)?(?:T(?:([0-9]+)H)?(?:([0-9]+)M)?(?:([0-9]+(?:\.[0-9]+)?)S)?)?$"

    # A time left on a date's cell, which reads with it; and an offset on a datetime's cell, split from what it follows
    TIME_TAIL: ClassVar[str] = r"(?:[ T][0-9]{1,2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]+)?)?)?"
    TIME_AT_END: ClassVar[str] = r"[ T]([0-9]{1,2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]+)?)?)$"
    NOT_ZERO: ClassVar[str] = "[1-9]"
    OFFSET: ClassVar[str] = (
        r"^(.*[0-9]:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]+)?)?(?: ?[^0-9 ]+)?)\s*(Z|[+-][0-9]{2}(?::?[0-9]{2})?)$"
    )
    SERIAL: ClassVar[str] = r"^[0-9]{1,7}(?:\.[0-9]+)?$"
    # Seconds since 1970, of any length
    UNIX_SERIAL: ClassVar[str] = r"^[0-9]+(?:\.[0-9]+)?$"
    TRAILING_DOT: ClassVar[str] = r"\.$"
    DOT_OR_SPACE: ClassVar[str] = r"[.\s]"
    DIGIT_RUN: ClassVar[str] = "[0-9]+"

    @staticmethod
    def digits(low: int, high: int | None = None) -> str:
        """Exactly `low` digits, or with `high` from `low` to `high`."""
        return f"[0-9]{{{low}}}" if high is None else f"[0-9]{{{low},{high}}}"

    @staticmethod
    def captured(pattern: str) -> str:
        """`pattern` as a group whose match is kept."""
        return f"({pattern})"

    @staticmethod
    def whole_cell(pattern: str) -> str:
        """`pattern` matching a cell from its start to its end."""
        return f"^{pattern}$"

    @staticmethod
    def names(tokens: list[str]) -> str:
        """Any of `tokens` in any case, with or without a closing `.`."""
        spelled = "|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True))
        return rf"(?i:{spelled})\.?"

    @staticmethod
    def literal(text: str) -> str:
        """Text to be matched exactly, in a pattern built from a declaration."""
        return re.escape(text)

    @staticmethod
    def any_of(tokens: list[str]) -> str:
        """Any one of `tokens` literally, the longest first, so `¬£` is found before the `£` inside it."""
        return "|".join(re.escape(token) for token in sorted(tokens, key=len, reverse=True))

    @staticmethod
    def around(prefix: str, suffix: str) -> str:
        """A whole cell between a negative form's `prefix` and `suffix`, its number captured."""
        return rf"^{re.escape(prefix)}\s*(.*?)\s*{re.escape(suffix)}$"

    @staticmethod
    def marks(decimal: str, group: str | None) -> str:
        """A class of a number's own characters: its digits and its declared marks."""
        return "0-9" + re.escape(decimal) + (re.escape(group) if group else "")

    @classmethod
    def beside_number(cls, decimal: str, group: str | None) -> str:
        """What a number may be written with: anything else in its cell is undeclared."""
        return rf"[{cls.marks(decimal, group)}\s-]"

    @classmethod
    def number_run(cls, decimal: str, group: str | None) -> str:
        """One unbroken number: digits and declared marks, ending in a digit."""
        chars = cls.marks(decimal, group)
        return rf"[{chars}]*[0-9]"

    @classmethod
    def exponent(cls, decimal: str, group: str | None) -> str:
        """A whole cell that is a number with an exponent, the number captured, then the exponent."""
        return rf"^([{cls.marks(decimal, group)}]*[0-9])[eE]([+-]?[0-9]+)$"

    @staticmethod
    def number(decimal: str, group: str | None, shapes: list[tuple[int, int]]) -> str:
        """A whole number in its marks, ungrouped or in groups of any of `shapes`, each the last group's size and the
        size of those before it."""
        point = re.escape(decimal)
        whole = "[0-9]+"
        if group:
            mark = re.escape(group)
            whole += "".join(
                rf"|[0-9]{{1,{rest}}}(?:{mark}[0-9]{{{rest}}})*{mark}[0-9]{{{last}}}" for last, rest in shapes
            )
        return rf"^(?:(?:{whole})(?:{point}[0-9]+)?|{point}[0-9]+)$"


class PythonPatterns:
    """Patterns Python's `re` runs, compiled once."""

    # A date pattern's parts, Unicode's UAX 35: a quoted literal (the `de` of `d 'de' MMM`), a field of one repeated
    # letter, or other literal characters
    PATTERN_PART: ClassVar[re.Pattern] = re.compile(r"'[^']*'|([A-Za-z])\1*|[^'A-Za-z]+")
    # What a pattern typed for Excel or Python's `strptime` holds that UAX 35 writes otherwise
    STRPTIME: ClassVar[re.Pattern] = re.compile(r"%(.)")
    EXCEL_DROPPED: ClassVar[re.Pattern] = re.compile(r"\[\$[^\]]*\]|;@")
    EXCEL_ELAPSED: ClassVar[re.Pattern] = re.compile(r"\[([hHmMsS]+)\]")
    EXCEL_DAY_PERIOD: ClassVar[re.Pattern] = re.compile(r"(?i)AM/PM|A/P")
    EXCEL_QUOTED: ClassVar[re.Pattern] = re.compile(r'"([^"]*)"')
    EXCEL_ESCAPED: ClassVar[re.Pattern] = re.compile(r"\\(.)")
    EXCEL_FRACTION: ClassVar[re.Pattern] = re.compile(r"\.0+")
    # An error cell as fastexcel reports it, naming calamine's `CellErrorType`: `Error(Div0)`
    EXCEL_ERROR: ClassVar[re.Pattern] = re.compile(r"Error\((\w+)\)")
    # A cell's reference in a sheet, its column's letters and its row's number: `AB12`
    CELL_REFERENCE: ClassVar[re.Pattern] = re.compile(r"([A-Z]+)([0-9]+)")
    # A line of text with its end, `\r\n`, `\n`, or `\r`, as `io.StringIO(newline="")` splits it; the last may have none
    LINE: ClassVar[re.Pattern] = re.compile(r"[^\r\n]*(?:\r\n|\n|\r)|[^\r\n]+\Z")
    # A part of the row key, its name given by `RowKeyParser.ROW`: `__row__`, `__row__1`
    ROW_PART: ClassVar[str] = r"^{row}(\d*)$"
    # A refusal or warning, its text and its code: `Something was found. [whyqd:a-code]`
    MESSAGE: ClassVar[re.Pattern] = re.compile(r"^(.*) \[whyqd:([a-z0-9-]+)\]$", re.DOTALL)
