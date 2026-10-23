"""Write the typing fixture: cell text, the field's declared policy, and what the proposed typing must return.

    python tests/data/builders/fixtures_typing.py [target]

Target defaults to tests/data/synthetic-typing and is never overwritten. The expectations follow whyqd's proposed
typing: one grammar per type, ambiguity settled by the field's declared policy, never per cell; a blank-like cell is
blank; anything the policy cannot read is refused with a reason.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

TARGET = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "synthetic-typing"

UK = {"decimal": ".", "grouping": ",", "negatives": ["-x", "(x)", "x-"], "percent": "number"}
EU = {"decimal": ",", "grouping": ".", "negatives": ["-x", "(x)", "x-"], "percent": "number"}
BLANKS = ["", "   ", " ", "\t"]


def v(text, value, note=""):
    return {"text": text, "outcome": "value", "value": value, "note": note}


def b(text):
    return {"text": text, "outcome": "blank"}


def r(text, reason):
    return {"text": text, "outcome": "refuse", "reason": reason}


NUMBER = {
    "UK": {"policy": UK, "cases": [
        v("£43.40", "43.40"), v("¬£43.40", "43.40", "mojibake: ¬ is Sm, £ is Sc, both drop"), v("£-826.80", "-826.80"),
        v("-£826.80", "-826.80"), v("£1,234.50", "1234.50"), v("£.00", "0.00"), v("12.50", "12.50"), v(" 7", "7"),
        v("1e3", "1000"), v("(826.80)", "-826.80"), v("826.80-", "-826.80"), v("1,234", "1234"),
        v("0000130842", "130842"), v("5%", "5", "percent policy: number"), v("−45", "-45", "Unicode minus"),
        v("１２", "12", "full-width digits, NFKC"),
        r("1.234,50", "separators out of order for this policy"), r("1,5", "grouping of fewer than three digits"),
        r("826.80 CR", "letters"), r("N/A", "letters"), r("12k", "letters"), r("£10 - £20", "two numbers"),
        r("Trans Prem: £0.01", "letters"), r("1.2.3", "two decimal points"),
        *[b(t) for t in BLANKS]]},
    "EU": {"policy": EU, "cases": [
        v("1.234,50", "1234.50"), v("1,5", "1.5"), v("1.234", "1234"), v("€-12,30", "-12.30"),
        r("1,234.50", "separators out of order for this policy"), *[b(t) for t in BLANKS[:2]]]},
}
INTEGER = {"UK": {"policy": UK, "cases": [
    v("12", "12"), v("0000130842", "130842"), v("1,234", "1234"), v("-7", "-7"),
    r("12.50", "a fraction is not an integer"), r("1.234,50", "separators out of order for this policy"),
    r("826.80-", "a fraction is not an integer"), *[b(t) for t in BLANKS[:2]]]}}
BOOLEAN = {"declared": {"policy": {"true": ["true", "yes", "y", "1"], "false": ["false", "no", "n", "0"], "case": "insensitive"},
                        "cases": [v("TRUE", True), v("true", True), v("Y", True), v("1", True), v("yes", True),
                                  v("FALSE", False), v("N", False), v("0", False), r("maybe", "not in the declared terms"),
                                  *[b(t) for t in BLANKS]]}}
DATE = {
    "day_first": {"policy": {"order": "day_first"}, "cases": [
        v("13/04/2024", "2024-04-13"), v("04/01/2024", "2024-01-04"), v("2010-04-01 00:00:00", "2010-04-01"),
        v("2024-04-01", "2024-04-01"), v("2024/04/01", "2024-04-01", "year-first in any separator is year, month, day"),
        v("01.04.2010", "2010-04-01"), r("31/02/2024", "no such date"), r("45295", "an Excel serial as text"),
        *[b(t) for t in BLANKS[:2]]]},
    "month_first": {"policy": {"order": "month_first"}, "cases": [
        v("04/01/2024", "2024-04-01"), v("2024/04/01", "2024-04-01"), r("13/04/2024", "no month 13; never read day-first")]},
    "month_first_cells": {"policy": {"order": "day_first", "date_cells": "swap_day_month"},
                          "note": "the Stockport case: date cells were swapped by Excel, text cells are day-first as published",
                          "cases": [{"cell_type": "date", "stored": "2024-01-04", "outcome": "value", "value": "2024-04-01"},
                                    {"cell_type": "text", "text": "13/04/2024", "outcome": "value", "value": "2024-04-13"}]},
}
STRING = {"default": {"policy": {}, "cases": [
    v("  a  b ", "  a  b "), v("a\tb", "a\tb"), v("\\path", "\\path"), v("'0012", "'0012"), v("line\nbreak", "line\nbreak"),
    v("a b", "a b"), *[b(t) for t in BLANKS]]}}
CATEGORISE = {"note": "CATEGORISE with a boolean source term: does a cell count as a value?",
              "cases": [{"text": t, "is_value": False} for t in BLANKS] +
                       [{"text": t, "is_value": True} for t in ["0", "N/A", "x", "a b"]]}


def main():
    assert not TARGET.exists(), f"{TARGET} exists; fixtures are never overwritten"
    TARGET.mkdir(parents=True)
    key = {"generated": datetime.now().isoformat(timespec="seconds"), "design": "proposed typing",
           "number": NUMBER, "integer": INTEGER, "boolean": BOOLEAN, "date": DATE, "string": STRING, "categorise": CATEGORISE}
    (TARGET / "typing-key.json").write_text(json.dumps(key, indent=2, ensure_ascii=False), encoding="utf-8")
    count = sum(len(p["cases"]) for t in (NUMBER, INTEGER, BOOLEAN, DATE, STRING) for p in t.values())
    print(count, "typing cases and", len(CATEGORISE["cases"]), "CATEGORISE cases written")


if __name__ == "__main__":
    main()
