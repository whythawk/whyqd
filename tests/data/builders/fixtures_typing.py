# SPDX-License-Identifier: BSD-3-Clause
"""Write the typing fixture: cell text, the field's declared policy, and what reading it must return.

    python tests/data/builders/fixtures_typing.py [target]

Target defaults to tests/data/synthetic-typing and is never overwritten. Each group states a field's type and the policy
it declares, as a `PolicyModel` holds it, or none for the type's canonical form. A cell is a value, a blank, or a refusal
with its `RefusalReason`; an ambiguity is settled by the declaration, never per cell, and nothing is assumed of a file.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

TARGET = (
    Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "synthetic-typing"
)

BLANKS = ["", "   ", " ", "\t", "\xa0"]
MONTHS = "January February March April May June July August September October November December".split()
SHORT = [month[:3] for month in MONTHS]
UK = {
    "format": {"decimalChar": ".", "groupChar": ","},
    "rules": {"currency": ["£", "¬£"], "negative": ["(x)", "x-"]},
}
EU = {"format": {"decimalChar": ",", "groupChar": "."}, "rules": {"currency": ["€"]}}


def v(text, value, note=""):
    return {"text": text, "outcome": "value", "value": value, "note": note}


def b(text):
    return {"text": text, "outcome": "blank"}


def r(text, reason):
    return {"text": text, "outcome": "refuse", "reason": reason}


def group(dtype, policy, cases, **parts):
    return {"type": dtype, "policy": policy, "cases": cases, **parts}


BLANK_CASES = [b(text) for text in BLANKS]
NUMBER = {
    "canonical": group(
        "number",
        None,
        [
            v("1234.50", "1234.50"),
            v("-5", "-5"),
            v("0000130842", "130842"),
            v(" 7", "7"),
            v("−45", "-45", "Unicode minus"),
            v("１２", "12", "full-width digits, NFKC"),
            v("٣٤", "34", "Arabic-Indic digits, by Unicode's value"),
            v("१२३", "123", "Devanagari digits"),
            v("12‏", "12", "a right-to-left mark"),
            r("٣4", "mixed-digits"),
            r("1,234", "undeclared-character"),
            r("£5", "undeclared-character"),
            r("<5", "undeclared-character"),
            r("~5", "undeclared-character"),
            r("±5", "undeclared-character"),
            r("5%", "undeclared-character"),
            r("12​", "undeclared-character"),
            r("(5)", "undeclared-sign"),
            r("5-", "undeclared-sign"),
            r("1e3", "undeclared-exponent"),
            r("12E4", "undeclared-exponent"),
            r("2310009E13", "undeclared-exponent"),
            r("NaN", "undeclared-non-finite"),
            r("INF", "undeclared-non-finite"),
            r("-INF", "undeclared-non-finite"),
            r("43.40¹", "number-form-character"),
            r("10²", "number-form-character"),
            r("①2", "number-form-character"),
            r("½", "number-form-character"),
            r("1½", "number-form-character"),
            r("12345678901234567890", "too-many-digits"),
            r("N/A", "undeclared-character"),
            *BLANK_CASES,
        ],
    ),
    "UK": group(
        "number",
        UK,
        [
            v("£43.40", "43.40"),
            v("¬£43.40", "43.40", "mojibake, declared as a currency"),
            v("£-826.80", "-826.80"),
            v("-£826.80", "-826.80"),
            v("£1,234.50", "1234.50"),
            v("£.00", "0.00"),
            v("12.50", "12.50"),
            v(" 7", "7"),
            v("(826.80)", "-826.80"),
            v("826.80-", "-826.80"),
            v("1,234", "1234"),
            v("0000130842", "130842"),
            v("−45", "-45", "Unicode minus"),
            v("１２", "12", "full-width digits, NFKC"),
            r("1e3", "undeclared-exponent"),
            r("5%", "undeclared-character"),
            r("$5", "undeclared-character"),
            r("1.234,50", "grouping-mismatch"),
            r("1,5", "grouping-mismatch"),
            r("1.2.3", "grouping-mismatch"),
            r("12,34,567", "grouping-mismatch"),
            r("826.80 CR", "undeclared-character"),
            r("N/A", "undeclared-character"),
            r("12k", "undeclared-character"),
            r("£10 - £20", "two-numbers"),
            r("Trans Prem: £0.01", "undeclared-character"),
            *BLANK_CASES,
        ],
    ),
    "EU": group(
        "number",
        EU,
        [
            v("1.234,50", "1234.50"),
            v("1,5", "1.5"),
            v("1.234", "1234"),
            v("€-12,30", "-12.30"),
            v("12,30 €", "12.30"),
            r("1,234.50", "grouping-mismatch"),
            r("(5)", "undeclared-sign"),
            *BLANK_CASES,
        ],
    ),
    "lakh": group(
        "number",
        {"format": {"decimalChar": ".", "groupChar": ",", "pattern": "#,##,##0.##"}, "rules": {"currency": ["₹"]}},
        [
            v("₹12,34,567.50", "1234567.50"),
            v("1,234", "1234"),
            v("99,99,99,999", "999999999"),
            r("1,234,567", "grouping-mismatch"),
        ],
    ),
    "spaces and marks": group(
        "number",
        {"format": {"decimalChar": ",", "groupChar": " "}, "rules": {"negative": ["x CR"], "marks": ["#"]}},
        [
            v("1 234,50", "1234.50", "a thin space, as declared"),
            v("1 234,50", "1234.50", "NFKC makes a hard space and a thin one the same"),
            v("#-4963,45", "-4963.45", "a publisher's mark"),
            v("826,80 CR", "-826.80"),
            r("826,80 DR", "undeclared-character"),
        ],
    ),
    "Swiss": group(
        "number",
        {"format": {"decimalChar": ".", "groupChar": "’"}, "rules": {"currency": ["CHF"]}},
        [v("CHF 1’234.50", "1234.50"), v("CHF-5.00", "-5.00"), r("EUR 5.00", "undeclared-character")],
    ),
    "Arabic": group(
        "number",
        {"format": {"decimalChar": "٫", "groupChar": "٬"}, "rules": {"currency": ["ج.م."], "percent": "٪"}},
        [
            v("١٬٢٣٤٫٥٠", "1234.50"),
            v("‏-١٬٢٣٤٫٥٠\xa0ج.م.‏", "-1234.50", "bidirectional marks removed"),
            v("؜-٥", "-5", "ar-EG's minus, a letter mark then a hyphen"),
            v("٥٪؜", "0.05", "a percent"),
        ],
    ),
    "percent": group(
        "number",
        {"rules": {"percent": "%", "perMille": "‰"}},
        [v("5%", "0.05"), v("5.5%", "0.055"), v("5‰", "0.005"), v("-5%", "-0.05"), v("5", "5")],
    ),
    "exponent": group(
        "number",
        {"rules": {"exponent": True, "nonFinite": True}},
        [v("1e3", "1000"), v("12E4", "120000"), v("NaN", "NaN"), v("INF", "INF"), v("-INF", "-INF")],
    ),
    "decimal": group(
        "number",
        {"base": "decimal"},
        [v("12345678901234567890", "12345678901234567890"), v("0.10", "0.10"), v("1234.5", "1234.5")],
    ),
}
INTEGER = {
    "UK": group(
        "integer",
        {"format": {"decimalChar": ".", "groupChar": ","}},
        [
            v("12", "12"),
            v("0000130842", "130842"),
            v("1,234", "1234"),
            v("-7", "-7"),
            r("12.50", "not-an-integer"),
            r("1.234,50", "grouping-mismatch"),
            r("826.80-", "undeclared-sign"),
            *BLANK_CASES,
        ],
    ),
}
BOOLEAN = {
    "canonical": group(
        "boolean",
        None,
        [
            v("TRUE", True),
            v("true", True),
            v("True", True),
            v("1", True),
            v("FALSE", False),
            v("false", False),
            v("0", False),
            r("Y", "not-in-format"),
            r("N", "not-in-format"),
            *BLANK_CASES,
        ],
    ),
    "declared": group(
        "boolean",
        {"format": "Y|N", "rules": {"alternateFormats": ["Yes|No", "1|0"]}},
        [
            v("Y", True),
            v("Yes", True),
            v("1", True),
            v("N", False),
            v("No", False),
            v("0", False),
            r("TRUE", "not-in-format"),
            r("y", "not-in-format"),
            r("maybe", "not-in-format"),
            *BLANK_CASES,
        ],
    ),
}
DATE = {
    "canonical": group(
        "date",
        None,
        [
            v("2024-04-13", "2024-04-13"),
            r("13/04/2024", "not-in-format"),
            r("2024/04/13", "not-in-format"),
            r("2024-02-30", "impossible-date"),
            *BLANK_CASES,
        ],
    ),
    "day_first": group(
        "date",
        {"format": "dd/MM/yyyy", "rules": {"alternateFormats": ["yyyy-MM-dd"]}},
        [
            v("13/04/2024", "2024-04-13"),
            v("04/01/2024", "2024-01-04"),
            v("2024-04-01", "2024-04-01"),
            r("2024/04/01", "not-in-format"),
            r("01.04.2010", "not-in-format"),
            r("2010-04-01 00:00:00", "not-in-format"),
            r("31/02/2024", "impossible-date"),
            r("45295", "not-in-format"),
            *BLANK_CASES,
        ],
    ),
    "month_first": group(
        "date",
        {"format": "MM/dd/yyyy"},
        [v("04/01/2024", "2024-04-01"), r("13/04/2024", "impossible-date"), r("2024/04/01", "not-in-format")],
    ),
    "dotted": group("date", {"format": "dd.MM.yyyy"}, [v("01.04.2010", "2010-04-01")]),
    "any_length_year": group(
        "date",
        {"format": "dd/MM/y"},
        [v("01/04/2024", "2024-04-01"), r("01/04/24", "not-in-format"), r("1/4/2024", "not-in-format")],
        note="`y` is four digits, or `01/04/24` would read as the year 24.",
    ),
    "year_first": group(
        "date", {"format": "yyyy/MM/dd"}, [v("2024/04/01", "2024-04-01"), r("2024/13/01", "impossible-date")]
    ),
    "two_digit_year": group(
        "date",
        {"format": "dd.MM.yy", "rules": {"yearStart": 1950}},
        [
            v("01.04.24", "2024-04-01"),
            v("01.04.49", "2049-04-01"),
            v("01.04.50", "1950-04-01"),
            v("01.04.97", "1997-04-01"),
            r("01.04.2024", "not-in-format"),
        ],
    ),
    "month_names": group(
        "date",
        {
            "format": "d MMMM yyyy",
            "rules": {"alternateFormats": ["d MMM yyyy"], "monthNames": MONTHS, "monthAbbreviations": SHORT},
        },
        [
            v("1 April 2024", "2024-04-01"),
            v("1 Apr 2024", "2024-04-01"),
            r("1 Avril 2024", "not-in-format"),
            r("1 APRIL 2024", "not-in-format"),
        ],
    ),
    "quoted": group(
        "date",
        {
            "format": "d 'de' MMM 'de' y",
            "rules": {"monthAbbreviations": "jan. fev. mar. abr. mai jun. jul. ago. set. out. nov. dez.".split()},
        },
        [v("1 de abr. de 2024", "2024-04-01"), r("1 abr. 2024", "not-in-format")],
    ),
    "Arabic": group(
        "date",
        {"format": "d‏/M‏/y"},
        [v("١‏/٤‏/٢٠٢٤", "2024-04-01", "by Unicode's digits, with marks removed"), v("1/4/2024", "2024-04-01")],
    ),
    "month_first_cells": group(
        "date",
        {"format": "dd/MM/yyyy", "rules": {"cellFormats": {"d": "yyyy-dd-MM"}}},
        [
            {"cell_type": "d", "text": "2024-01-04", "outcome": "value", "value": "2024-04-01"},
            {"cell_type": "s", "text": "13/04/2024", "outcome": "value", "value": "2024-04-13"},
        ],
        note="A column Excel partly converted: its date cells have day and month swapped, its text is as published.",
    ),
    "stored_cells": group(
        "date",
        {"format": "dd/MM/yyyy"},
        [
            {"cell_type": "d", "text": "2024-01-04", "outcome": "value", "value": "2024-01-04"},
            {"cell_type": "e", "text": "#N/A", "outcome": "refuse", "reason": "error-cell"},
        ],
        note="A policy's text rules read only text cells: a stored date is already a value.",
    ),
}
DATE |= {
    "early_years": group(
        "date",
        {"format": "dd/MM/yyy", "rules": {"alternateFormats": ["dd/MM/yyyy"]}},
        [
            v("01/04/800", "0800-04-01"),
            v("01/04/0800", "0800-04-01"),
            v("01/04/2024", "2024-04-01"),
            r("01/04/24", "not-in-format"),
        ],
        note="Three digits are declared by `yyy`; four, zero-padded or not, by `yyyy`.",
    ),
}
MONTH = {
    "canonical": group(
        "month",
        None,
        [
            v("2024-04", "2024-04-30"),
            v("2024-02", "2024-02-29"),
            r("04/2024", "not-in-format"),
            r("2024-13", "impossible-date"),
            {"cell_type": "d", "text": "2024-04-15", "outcome": "value", "value": "2024-04-30"},
            *BLANK_CASES,
        ],
    ),
    "named": group(
        "month",
        {"format": "MMM yyyy", "rules": {"monthAbbreviations": SHORT}},
        [v("Apr 2024", "2024-04-30"), v("Dec 1997", "1997-12-31"), r("Avr 2024", "not-in-format")],
    ),
}
QUARTER = {
    "canonical": group(
        "quarter",
        None,
        [v("2024-06", "2024-06-30"), v("2024-04", "2024-06-30"), r("2024Q2", "not-in-format"), *BLANK_CASES],
    ),
    "declared": group(
        "quarter",
        {"format": "yyyy'Q'Q", "rules": {"alternateFormats": ["'Q'Q yyyy"]}},
        [
            v("2024Q1", "2024-03-31"),
            v("2024Q2", "2024-06-30"),
            v("2024Q4", "2024-12-31"),
            v("Q3 2024", "2024-09-30"),
            r("2024Q5", "impossible-date"),
            r("2024Q0", "impossible-date"),
        ],
    ),
}
YEAR = {
    "canonical": group("year", None, [v("2024", "2024-12-31"), r("24", "not-in-format"), *BLANK_CASES]),
    "two_digit": group(
        "year", {"format": "yy", "rules": {"yearStart": 1950}}, [v("24", "2024-12-31"), v("97", "1997-12-31")]
    ),
}
TIME = {
    "twelve_hour": group(
        "time",
        {"format": "h:mm a", "rules": {"dayPeriods": ["AM", "PM"]}},
        [
            v("9:30 AM", "09:30:00"),
            v("9:30 PM", "21:30:00"),
            v("12:00 AM", "00:00:00"),
            v("12:00 PM", "12:00:00"),
            r("13:00 PM", "impossible-date"),
            r("0:30 AM", "impossible-date"),
            r("9:30", "not-in-format"),
            r("9:30 pm", "not-in-format"),
        ],
    ),
    "canonical": group(
        "time",
        None,
        [
            v("12:45:00", "12:45:00"),
            r("12:45", "not-in-format"),
            r("25:00:00", "impossible-date"),
            *BLANK_CASES,
        ],
    ),
    "declared": group("time", {"format": "HH:mm"}, [v("12:45", "12:45:00"), r("12:45:00", "not-in-format")]),
}
DATETIME = {
    "canonical": group(
        "datetime",
        None,
        [v("2024-04-13T12:45:00", "2024-04-13T12:45:00"), r("13/04/2024 12:45", "not-in-format"), *BLANK_CASES],
    ),
    "declared": group(
        "datetime", {"format": "dd/MM/yyyy HH:mm"}, [v("13/04/2024 12:45", "2024-04-13T12:45:00")]
    ),
    "twelve_hour": group(
        "datetime",
        {"format": "dd/MM/yyyy h:mm a", "rules": {"dayPeriods": ["a. m.", "p. m."]}},
        [v("13/04/2024 9:30 p. m.", "2024-04-13T21:30:00")],
    ),
    "utc": group(
        "datetime",
        {"format": "yyyy-MM-dd'T'HH:mm:ss'Z'", "rules": {"zone": "UTC"}},
        [
            v("2024-04-13T12:45:00Z", "2024-04-13T12:45:00+00:00"),
            r("2024-04-13T12:45:00", "not-in-format"),
            r("2024-04-13T12:45:00+01:00", "not-in-format"),
        ],
    ),
    "london": group(
        "datetime",
        {"format": "dd/MM/yyyy HH:mm", "rules": {"zone": "Europe/London"}},
        [
            v("13/06/2024 12:45", "2024-06-13T12:45:00+01:00"),
            v("13/01/2024 12:45", "2024-01-13T12:45:00+00:00"),
            r("31/03/2024 01:30", "impossible-date"),
            r("27/10/2024 01:30", "impossible-date"),
        ],
        note="A clock time that never happened, or happened twice as the clocks changed, states no one moment.",
    ),
}
DURATION = {
    "canonical": group(
        "duration",
        None,
        [
            v("PT25M", 1500),
            v("PT1H30M", 5400),
            v("P1DT2H", 93600),
            v("-PT1M", -60),
            v("PT0.5S", 0.5),
            r("P1Y", "not-in-format"),
            r("P1M", "not-in-format"),
            r("P", "not-in-format"),
            r("25 min", "not-in-format"),
            {"cell_type": "d", "text": "PT25H30M", "outcome": "value", "value": 91800},
            *BLANK_CASES,
        ],
        note="A value is in seconds. Years and months have no fixed length.",
    ),
    "hours_and_minutes": group(
        "duration",
        {"format": "H:mm"},
        [
            v("1:30", 5400),
            v("100:30", 361800, "a quantity, not a clock"),
            r("1:75", "impossible-date"),
            r("25 min", "not-in-format"),
            {"cell_type": "d", "text": "PT25H30M", "outcome": "value", "value": 91800},
        ],
    ),
    "with_words": group(
        "duration",
        {"format": "m' min'", "rules": {"alternateFormats": ["H'h'mm"]}},
        [v("25 min", 1500), v("90 min", 5400), v("12h45", 45900), r("12:45", "not-in-format")],
    ),
}
STRING = {
    "default": group(
        "string",
        None,
        [
            v("  a  b ", "  a  b "),
            v("a\tb", "a\tb"),
            v("\\path", "\\path"),
            v("'0012", "'0012"),
            v("line\nbreak", "line\nbreak"),
            v("a\xa0b", "a\xa0b"),
            *BLANK_CASES,
        ],
    ),
    "excel_damage": group(
        "string",
        None,
        [
            {"cell_type": "d", "text": "2024-09-02", "outcome": "value", "value": "2024-09-02", "warns": "SEPT2"},
            {"cell_type": "n", "text": "23100090000000000000", "outcome": "value", "value": "23100090000000000000", "warns": "2310009E13"},
            {"cell_type": "d", "text": "2024-09-01", "outcome": "value", "value": "2024-09-01", "warns": "1-Sep"},
            {"cell_type": "s", "text": "SEPT2", "outcome": "value", "value": "SEPT2"},
        ],
        note="What Excel did before whyqd saw the file: `warns` holds the original, which is gone. whyqd warns of the "
        "stored type and never reverses it.",
    ),
}
CATEGORISE = {
    "note": "CATEGORISE with a boolean source term: does a cell count as a value?",
    "cases": [{"text": t, "is_value": False} for t in BLANKS]
    + [{"text": t, "is_value": True} for t in ["0", "N/A", "x", "a b"]],
}
TYPES = {
    "number": NUMBER,
    "integer": INTEGER,
    "boolean": BOOLEAN,
    "date": DATE,
    "month": MONTH,
    "quarter": QUARTER,
    "year": YEAR,
    "time": TIME,
    "datetime": DATETIME,
    "duration": DURATION,
    "string": STRING,
}


def main():
    assert not TARGET.exists(), f"{TARGET} exists; fixtures are never overwritten"
    TARGET.mkdir(parents=True)
    key = {"generated": datetime.now().isoformat(timespec="seconds"), **TYPES, "categorise": CATEGORISE}
    (TARGET / "typing-key.json").write_text(json.dumps(key, indent=2, ensure_ascii=False), encoding="utf-8")
    count = sum(len(g["cases"]) for groups in TYPES.values() for g in groups.values())
    print(count, "typing cases and", len(CATEGORISE["cases"]), "CATEGORISE cases written")


if __name__ == "__main__":
    main()
