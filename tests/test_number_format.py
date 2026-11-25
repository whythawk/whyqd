# SPDX-License-Identifier: BSD-3-Clause
"""An Excel number format code read by ECMA-376's grammar: what Excel shows under it, and what whyqd reads.

What whyqd reads is held to the cell fixtures' own rule, `kind` in `tests/data/builders/cells.py`, written apart from
the library. What Excel shows is held to the classes of every code in the workbooks the rebuild was tested on.
"""

import pytest

from tests.data.builders import cells
from whyqd.dtypes import FormatClass
from whyqd.sources.number_format import NumberFormatParser

# Every code the real workbooks hold, with the class of what Excel shows
CENSUS = {
    "General": FormatClass.GENERAL,
    "mm-dd-yy": FormatClass.DATE,
    "yyyy\\-mm\\-dd;@": FormatClass.DATE,
    "0": FormatClass.ROUNDED,
    "#,##0.00": FormatClass.ROUNDED,
    "#,##0": FormatClass.ROUNDED,
    "0.00": FormatClass.ROUNDED,
    "YYYY-MM-DD HH:MM:SS": FormatClass.DATE,
    "0%": FormatClass.PERCENT,
    "dd\\/mm\\/yyyy": FormatClass.DATE,
    "d-mmm-yy": FormatClass.DATE,
    "d/m/yy;@": FormatClass.DATE,
    "dd/mm/yyyy": FormatClass.DATE,
    "0.00%": FormatClass.PERCENT,
    "0.00E+00": FormatClass.SCIENTIFIC,
    "d-mmm": FormatClass.DATE,
    "dd.mm": FormatClass.DATE,
}
# The grammar's other classes, none in the real workbooks
GRAMMAR = {
    "[h]:mm": FormatClass.ELAPSED,
    "0.0,,": FormatClass.SCALED,
    "# ?/?": FormatClass.FRACTION,
    "0000000000": FormatClass.ZERO_PADDED,
    "[$£-809]#,##0.00": FormatClass.CURRENCY,
    '"Ref "0': FormatClass.LITERAL,
    "[Red]0": FormatClass.CONDITIONAL,
    "[>=100][Magenta].00": FormatClass.CONDITIONAL,
    ";;;": FormatClass.HIDDEN,
    "@": FormatClass.TEXT,
    "[$-F800]dddd, mmmm dd, yyyy": FormatClass.LOCALE,
    "aaa yyyy": FormatClass.DATE,
}


@pytest.mark.parametrize("code", list(CENSUS) + list(GRAMMAR))
def test_each_code_shows_as_its_class(code):
    assert NumberFormatParser().shows(code) == (CENSUS | GRAMMAR)[code]


@pytest.mark.parametrize("code", [*cells.CODES, *CENSUS, *GRAMMAR, "A/P", "[ss]", "0;yyyy-mm-dd"])
def test_each_code_reads_as_the_fixtures_rule_says(code):
    assert NumberFormatParser().reads(code) == cells.kind(code)


def test_a_weekday_and_year_show_a_date_and_read_a_number():
    parser = NumberFormatParser()
    assert parser.shows("aaa yyyy") == FormatClass.DATE and parser.reads("aaa yyyy") == "number"


@pytest.mark.parametrize("code", ['0";"0', "0\\;0", "[>;]0"])
def test_a_quoted_or_escaped_semicolon_does_not_split(code):
    assert len(NumberFormatParser().sections(code)) == 1


def test_sections_split_as_written():
    assert NumberFormatParser().sections("#,##0.00;(#,##0.00);-;@") == ["#,##0.00", "(#,##0.00)", "-", "@"]


@pytest.mark.parametrize("code", ["mm-dd-yy", "[$-F800]dddd, mmmm dd, yyyy", "[$-F400]h:mm:ss AM/PM"])
def test_a_code_the_machine_s_locale_renders_is_named(code):
    assert NumberFormatParser().machine(code)


def test_a_written_date_code_is_not_the_machine_s():
    assert not NumberFormatParser().machine("dd/mm/yyyy")
