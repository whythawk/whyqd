# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import ClassVar, NamedTuple

from whyqd.dtypes import FieldType, FormatClass
from whyqd.sources.excel import ExcelParser


class Token(NamedTuple):
    """One part of a format code: a quoted literal, an escaped character, a bracket's contents, or a character."""

    kind: str
    text: str
    start: int


class NumberFormatParser:
    """An Excel number format code read by the grammar of [ECMA-376 Part 1, section
    18.8.31](https://ecma-international.org/publications-and-standards/standards/ecma-376/): what whyqd reads a number
    under it as, and what Excel shows.

    A code has up to four sections split by `;`: positive, negative, zero, and text. A `;` quoted, escaped by `\\`, or
    in brackets does not split. Quotes, whatever follows `\\`, `_`, or `*`, and brackets are not tokens; but a bracket
    holding only `h`, `m`, or `s` makes an elapsed time, a bracket opening `$` names a currency or a locale, and any
    other bracket is a colour or a condition.

    **What whyqd reads** follows `ExcelParser`'s rule, by the first section alone: the first of `d m y h s` makes a
    date, and once an `a` has come only `/`, `m`, or `p` still does. **What Excel shows** is a `FormatClass`, read from
    the grammar rather than from a list, so a code a publisher invents still falls in one; `aaa yyyy` shows a date,
    a weekday and year, and reads as a number.

    Examples:
      ```python
      from whyqd.sources.number_format import NumberFormatParser

      parser = NumberFormatParser()
      parser.shows("0.00E+00")   # FormatClass.SCIENTIFIC
      parser.reads("aaa yyyy")   # "number"
      ```
    """

    # A token's kinds
    QUOTED: ClassVar[str] = "quoted"
    ESCAPED: ClassVar[str] = "escaped"
    BRACKET: ClassVar[str] = "bracket"
    CHAR: ClassVar[str] = "char"
    QUOTE: ClassVar[str] = '"'
    ESCAPES: ClassVar[str] = "\\_*"
    OPEN: ClassVar[str] = "["
    CLOSE: ClassVar[str] = "]"
    SECTION: ClassVar[str] = ";"
    DATE_LETTERS: ClassVar[str] = "dmyhs"
    ELAPSED_LETTERS: ClassVar[str] = "hms"
    WEEKDAY: ClassVar[str] = "a"
    AFTER_WEEKDAY: ClassVar[str] = "/mp"
    PLACEHOLDERS: ClassVar[str] = "0#?"
    ZERO: ClassVar[str] = "0"
    POINT: ClassVar[str] = "."
    SCALE: ClassVar[str] = ","
    TEXT: ClassVar[str] = "@"
    PERCENT: ClassVar[str] = "%"
    EXPONENTS: ClassVar[tuple[str, ...]] = ("E+", "E-")
    FRACTION: ClassVar[str] = "/"
    CURRENCY: ClassVar[str] = "$"
    CURRENCIES: ClassVar[str] = "$£€¥"
    LOCALE: ClassVar[str] = "$-"
    CONDITIONS: ClassVar[str] = "<>="
    # The codes that show by the machine's own settings: id 14, its short date, and the system long date and time
    MACHINE_ID: ClassVar[int] = 14
    MACHINE_LOCALES: ClassVar[tuple[str, ...]] = ("$-F800", "$-F400")

    def tokens(self, code: str) -> list[Token]:
        """A code's parts in order: `quoted`, `escaped`, `bracket`, or `char`."""
        found, i = [], 0
        while i < len(code):
            c = code[i]
            if c == self.QUOTE:
                end = code.find(self.QUOTE, i + 1)
                end = len(code) if end < 0 else end
                found.append(Token(self.QUOTED, code[i + 1 : end], i))
                i = end + 1
            elif c in self.ESCAPES:
                found.append(Token(self.ESCAPED, code[i + 1 : i + 2], i))
                i += 2
            elif c == self.OPEN:
                end = code.find(self.CLOSE, i + 1)
                end = len(code) if end < 0 else end
                found.append(Token(self.BRACKET, code[i + 1 : end], i))
                i = end + 1
            else:
                found.append(Token(self.CHAR, c, i))
                i += 1
        return found

    def sections(self, code: str) -> list[str]:
        """A code's sections, split at each `;` that is not quoted, escaped, or in brackets."""
        cuts = [token.start for token in self.tokens(code) if token.kind == self.CHAR and token.text == self.SECTION]
        bounds = [-1, *cuts, len(code)]
        return [code[start + 1 : end] for start, end in zip(bounds, bounds[1:], strict=False)]

    def reads(self, code: str) -> str:
        """What whyqd reads a number under this code as: `date`, `duration`, or `number`, by the first section."""
        after_weekday = False
        for token in self.tokens(self.sections(code)[0]):
            if token.kind == self.BRACKET and self.elapsed(token.text):
                return FieldType.DURATION.value
            if token.kind != self.CHAR:
                continue
            letter = token.text.lower()
            if after_weekday:
                if letter in self.AFTER_WEEKDAY:
                    return FieldType.DATE.value
            elif letter == self.WEEKDAY:
                after_weekday = True
            elif letter in self.DATE_LETTERS:
                return FieldType.DATE.value
        return FieldType.NUMBER.value

    def shows(self, code: str) -> FormatClass:
        """What Excel shows a number under this code as, against the value whyqd reads."""
        if code.strip().lower() == ExcelParser.BUILT_IN[0].lower():
            return FormatClass.GENERAL
        brackets = [token.text for token in self.tokens(code) if token.kind == self.BRACKET]
        first = self.tokens(self.sections(code)[0])
        written = "".join(token.text for token in first if token.kind == self.CHAR)
        if any(text[:1] in self.CONDITIONS or text[:1].isalpha() and not self.elapsed(text) for text in brackets):
            return FormatClass.CONDITIONAL
        if any(text.startswith(self.LOCALE) for text in brackets):
            return FormatClass.LOCALE
        if any(token.kind == self.BRACKET and self.elapsed(token.text) for token in first):
            return FormatClass.ELAPSED
        if any(letter in self.DATE_LETTERS + self.WEEKDAY for letter in written.lower()):
            return FormatClass.DATE
        if written.strip() == self.TEXT:
            return FormatClass.TEXT
        if not any(letter in self.PLACEHOLDERS for letter in written):
            return FormatClass.HIDDEN
        if any(exponent in written for exponent in self.EXPONENTS):
            return FormatClass.SCIENTIFIC
        if self.FRACTION in written:
            return FormatClass.FRACTION
        if self.PERCENT in written:
            return FormatClass.PERCENT
        if written.rstrip().endswith(self.SCALE):
            return FormatClass.SCALED
        if any(text.startswith(self.CURRENCY) for text in brackets) or any(c in self.CURRENCIES for c in written):
            return FormatClass.CURRENCY
        if any(token.kind in (self.QUOTED, self.ESCAPED) and token.text.strip() for token in first):
            return FormatClass.LITERAL
        if written.split(self.POINT)[0].count(self.ZERO) > 1:
            return FormatClass.ZERO_PADDED
        return FormatClass.ROUNDED

    def machine(self, code: str) -> bool:
        """Whether Excel shows this code by the machine's own settings, so no file says how it looked: id 14's short
        date, or the system long date or time. A custom code written as id 14's cannot be told from it."""
        brackets = [token.text for token in self.tokens(code) if token.kind == self.BRACKET]
        return code == ExcelParser.BUILT_IN[self.MACHINE_ID] or any(
            text.upper().startswith(self.MACHINE_LOCALES) for text in brackets
        )

    def elapsed(self, text: str) -> bool:
        """Whether a bracket's contents make an elapsed time: one of `h`, `m`, or `s`, repeated."""
        lower = text.lower()
        return bool(lower) and lower[0] in self.ELAPSED_LETTERS and set(lower) == {lower[0]}
