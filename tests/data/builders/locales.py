# SPDX-License-Identifier: BSD-3-Clause
"""Write one table of true values as each locale's publisher would, and what a whole conversion of each must do.

    python tests/data/builders/locales.py [target]

Target defaults to tests/data/synthetic-locales and is never overwritten. Each locale's marks, digits, and date patterns
come from `locale-conventions.json`, an extract of Unicode's CLDR (https://cldr.unicode.org/) read through Babel, so no
convention is recalled; nothing here calls whyqd, so a misreading cannot agree with itself. CLDR says nothing of how a
locale writes a boolean or delimits a CSV, so every file writes `Y` and `N`, and uses commas with CSV's quoting.

A cold transform reads each cell with one sensible reading as its destination type, and halts on the rest. `Cold` says
which, by its own rules: the marks `.` and `,` where only one reading fits, a currency mark of category `Sc`, a sign form
or percent, and the three undeclared date shapes, judging a month name by `whyqd/config/names.json`, read as data.

Beside a clean file per locale are three damaged ones: `mixed` holds markers and a stray mark among its amounts, `footer`
a totals row, and `excel` the conversions Excel makes on opening a file. `answer-key.json` gives, per file, each round of
declarations with the fields it should still halt on, and the values a conforming transform holds.
"""

import csv
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from workbook import save

HERE = Path(__file__).resolve().parent
TARGET = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent / "synthetic-locales"
CONVENTIONS = json.loads((HERE / "locale-conventions.json").read_text(encoding="utf-8"))
LOCALES = CONVENTIONS["locales"]
YEAR_START = 1950

DESTINATION = {
    "id": "string",
    "name": "string",
    "amount": "number",
    "balance": "number",
    "rate": "number",
    "count": "integer",
    "start": "date",
    "end": "date",
    "active": "boolean",
}
EXACT = {"amount", "balance"}
TRUE_VALUES = [
    {
        "id": "R001",
        "name": "Alpha",
        "amount": "1234.50",
        "balance": "-826.80",
        "rate": "0.05",
        "count": "12",
        "start": "2024-04-13",
        "end": "2024-12-31",
        "active": True,
    },
    {
        "id": "R002",
        "name": "Beta",
        "amount": "1234567.89",
        "balance": "15.00",
        "rate": "0.125",
        "count": "1234567",
        "start": "1997-01-04",
        "end": "2004-02-29",
        "active": False,
    },
    {
        "id": "R003",
        "name": "Gamma",
        "amount": "-43.40",
        "balance": "-1.50",
        "rate": "0",
        "count": "0",
        "start": "2004-02-29",
        "end": "2024-01-02",
        "active": True,
    },
    {
        "id": "R004",
        "name": "Delta",
        "amount": "0.00",
        "balance": "1000000.00",
        "rate": "1.5",
        "count": "999",
        "start": "2049-06-30",
        "end": "1950-03-01",
        "active": False,
    },
    {
        "id": "R005",
        "name": "Epsilon",
        "amount": None,
        "balance": None,
        "rate": "0.2",
        "count": None,
        "start": None,
        "end": "2024-05-06",
        "active": None,
    },
]
ZEROS = {"arab": "٠"}
BIDI = "‎‏؜"
DATE_FIELD = re.compile(r"'[^']*'|y+|M+|d+")
NAMES = json.loads((HERE.parents[2] / "whyqd" / "config" / "names.json").read_text(encoding="utf-8"))["languages"]


class Cold:
    """Whether a cell reads, undeclared, as its type: a blank always does, being no value to halt on."""

    NUMBER = re.compile(r"[0-9]*(?:[.,][0-9]+)*")
    EXPONENT = re.compile(r"[eE][+-]?[0-9]+$")
    ISO = re.compile(r"([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})(?:[T ][0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)?")
    ORDER = re.compile(r"([0-9]{1,2})([/.-])([0-9]{1,2})\2([0-9]{4})")
    RUN = re.compile(r"([0-9]{4})([0-9]{2})([0-9]{2})")
    SERIAL = re.compile(r"[0-9]+(?:\.[0-9]+)?")
    BOOLEAN = re.compile(r"(?i)true|false|1|0")
    LAST_SERIAL = 2958465
    PHANTOM = 60

    def __init__(self) -> None:
        self.months = {}
        for entry in NAMES.values():
            for month, names in enumerate(entry["months"], 1):
                for name in names:
                    self.months.setdefault(name.lower().rstrip("."), set()).add(month)

    def reads(self, dtype: str, text: str) -> bool:
        cell = canonical(text)
        if not cell:
            return True
        scripts = {ord(c) - unicodedata.decimal(c) for c in text if unicodedata.category(c) == "Nd"}
        if len(scripts) > 1 or any(unicodedata.category(c) == "No" for c in text):
            return False
        if dtype == "boolean":
            return bool(self.BOOLEAN.fullmatch(cell))
        return self.number(cell) if dtype in ("number", "integer") else self.date(cell)

    def number(self, cell: str) -> bool:
        cell = cell.replace("¬£", "£")
        cell = cell.strip(" -%()" + "".join(c for c in cell if unicodedata.category(c) == "Sc"))
        cell = self.EXPONENT.sub("", cell)
        if not self.NUMBER.fullmatch(cell) or not re.search("[0-9]", cell):
            return False
        marks = re.findall("[.,]", cell)
        if not marks:
            return True
        if len(set(marks)) == 2:
            decimal = marks[-1]
            return marks.count(decimal) == 1 and self.grouped(cell.rpartition(decimal)[0], ({".", ","} - {decimal}).pop())
        if len(marks) > 1:
            return self.grouped(cell, marks[0])
        before, _, after = cell.partition(marks[0])
        return not (len(after) == 3 and 1 <= len(before) <= 3 and not before.startswith("0"))

    @staticmethod
    def grouped(whole: str, mark: str) -> bool:
        """CLDR's two shapes: groups of three, or Indian, a three after twos."""
        first, *rest = whole.split(mark)
        if all(len(part) == 3 for part in rest):
            return 1 <= len(first) <= 3
        return len(rest[-1]) == 3 and all(len(part) == 2 for part in rest[:-1]) and 1 <= len(first) <= 2

    def date(self, cell: str) -> bool:
        if match := self.ISO.fullmatch(cell) or self.RUN.fullmatch(cell):
            year, month, day = (int(part) for part in match.groups())
            return bool(valid(year, month, day))
        if match := self.ORDER.fullmatch(cell):
            first, _, second, year = match.groups()
            readings = {d for d in (valid(int(year), int(second), int(first)), valid(int(year), int(first), int(second))) if d}
            return len(readings) == 1
        if self.SERIAL.fullmatch(cell):
            return 1 <= float(cell) <= self.LAST_SERIAL and int(float(cell)) != self.PHANTOM
        words = cell.replace(",", " ").split()
        if len(words) != 3 or not re.fullmatch("[0-9]{4}", words[2]):
            return False
        day, name = (words[0], words[1]) if words[0].isdigit() else (words[1], words[0])
        months = self.months.get(name.lower().rstrip("."), set())
        return day.isdigit() and len(months) == 1 and bool(valid(int(words[2]), next(iter(months)), int(day)))


def valid(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


COLD = Cold()


class Publisher:
    """One locale's way of writing a value, from its conventions alone."""

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.c = LOCALES[tag]
        self.digits = ZEROS.get(self.c["numbering"])

    def script(self, text: str) -> str:
        if not self.digits:
            return text
        return "".join(chr(ord(self.digits) + int(c)) if c.isascii() and c.isdigit() else c for c in text)

    def plain(self, value: Decimal, *, pattern: str, places: int | None = None) -> str:
        """The absolute value, in the marks and group sizes of `pattern`."""
        groups = re.search(r"[#,0]+", pattern).group().split(",")
        primary, secondary = len(groups[-1]), len(groups[-2]) if len(groups) > 2 else len(groups[-1])
        text = f"{abs(value):.{places}f}" if places is not None else format(abs(value).normalize(), "f")
        whole, _, fraction = text.partition(".")
        parts = [whole[-primary:]] if len(whole) > primary else [whole]
        rest = whole[: -primary] if len(whole) > primary else ""
        while rest:
            parts.insert(0, rest[-secondary:])
            rest = rest[: -secondary]
        written = self.c["group"].join(parts)
        return self.script(written + (self.c["decimal"] + fraction if fraction else ""))

    def patterned(self, value: Decimal, *, pattern: str, mark: str, symbol: str, places: int | None = None) -> str:
        """`value` through a CLDR pattern: its own negative subpattern if it has one, or else the minus before it."""
        positive, _, negative = pattern.partition(";")
        sub = negative if value < 0 and negative else positive
        number = re.search(r"[#,0]+(\.[0#]+)?", sub).group()
        written = sub.replace(number, self.plain(value, pattern=number, places=places)).replace(mark, symbol)
        return self.c["minus"] + written if value < 0 and not negative else written

    def amount(self, value: str) -> str:
        return self.patterned(
            Decimal(value), pattern=self.c["currencyPattern"], mark="¤", symbol=self.c["currencySymbol"], places=2
        )

    def balance(self, value: str) -> str:
        return self.patterned(
            Decimal(value), pattern=self.c["accountingPattern"], mark="¤", symbol=self.c["currencySymbol"], places=2
        )

    def rate(self, value: str) -> str:
        return self.patterned(Decimal(value) * 100, pattern=self.c["percentPattern"], mark="%", symbol=self.c["percent"])

    def count(self, value: str) -> str:
        return self.patterned(Decimal(value), pattern=self.c["decimalPattern"], mark="¤", symbol="", places=0)

    def date(self, value: str, pattern: str) -> str:
        day = date.fromisoformat(value)

        def field(match: re.Match) -> str:
            token = match.group()
            if token.startswith("'"):
                return token[1:-1]
            if token == "yy":
                return self.script(f"{day.year % 100:02d}")
            if token.startswith("y"):
                return self.script(str(day.year))
            if token == "MMM":
                return self.c["monthsAbbreviated"][day.month - 1]
            if token == "MMMM":
                return self.c["monthsWide"][day.month - 1]
            return self.script(str({"M": day.month, "d": day.day}[token[0]]).zfill(len(token)))

        return DATE_FIELD.sub(field, pattern)

    def row(self, values: dict) -> dict:
        written = {"id": values["id"], "name": values["name"]}
        for name in ("amount", "balance", "rate", "count"):
            written[name] = "" if values[name] is None else getattr(self, name)(values[name])
        written["start"] = "" if values["start"] is None else self.date(values["start"], self.c["dateShort"])
        written["end"] = "" if values["end"] is None else self.date(values["end"], self.c["dateMedium"])
        written["active"] = "" if values["active"] is None else ("Y" if values["active"] else "N")
        return written

    def number_format(self, pattern: str) -> dict:
        written = {"decimalChar": self.c["decimal"], "groupChar": self.c["group"]}
        groups = re.search(r"[#,0]+", pattern).group()
        if groups.count(",") > 1:
            written["pattern"] = groups.replace(",", self.c["group"])
        return written

    def declarations(self) -> dict:
        """What the wrangler declares, field by field, having looked at this locale's file."""
        c, currency = self.c, {"currency": [self.c["currencySymbol"]]}
        brackets = {"negative": ["(x)"]} if "(" in c["accountingPattern"] else {}
        return {
            "amount": {"format": self.number_format(c["currencyPattern"]), "rules": currency},
            "balance": {"format": self.number_format(c["accountingPattern"]), "rules": currency | brackets},
            "rate": {"format": self.number_format(c["percentPattern"]), "rules": {"percent": c["percent"]}},
            "count": {"format": self.number_format(c["decimalPattern"])},
            "start": self.date_policy(c["dateShort"]),
            "end": self.date_policy(c["dateMedium"]),
            "active": {"format": "Y|N"},
        }

    def date_policy(self, pattern: str) -> dict:
        rules = {}
        tokens = [t for t in DATE_FIELD.findall(pattern) if not t.startswith("'")]
        if "yy" in tokens:
            rules["yearStart"] = YEAR_START
        if {"MMM", "MMMM"} & set(tokens):
            rules["language"] = self.tag.split("_")[0]
        return {"format": pattern} | ({"rules": rules} if rules else {})


def canonical(text: str) -> str:
    """A cell as the reader's fixed steps leave it, apart from any declaration, computed here without whyqd."""
    text = unicodedata.normalize("NFKC", text).translate({ord(mark): None for mark in BIDI}).strip()
    return "".join(str(unicodedata.decimal(c)) if unicodedata.category(c) == "Nd" else c for c in text).replace("−", "-")


def halts(rows: list[dict]) -> dict:
    """How many cells each undeclared field refuses, read cold as its destination type."""
    found = {}
    for name, dtype in DESTINATION.items():
        if dtype == "string":
            continue
        count = sum(1 for row in rows if not COLD.reads(dtype, row[name]))
        if count:
            found[name] = count
    return found


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(DESTINATION))
        writer.writeheader()
        writer.writerows(rows)


def clean(tag: str) -> dict:
    publisher = Publisher(tag)
    rows = [publisher.row(values) for values in TRUE_VALUES]
    write_csv(TARGET / f"{tag}.csv", rows)
    return {
        "mime": "CSV",
        "locale": tag,
        "rounds": [
            {"declare": {}, "halts": halts(rows)},
            {"declare": {"fields": publisher.declarations()}, "halts": {}},
        ],
        "values": TRUE_VALUES,
    }


def mixed() -> dict:
    """en_GB's file with what a real column holds beside its numbers. Each round's fix exposes the next."""
    tag = "en_GB"
    publisher = Publisher(tag)
    rows = [publisher.row(values) for values in TRUE_VALUES]
    rows[0]["amount"], rows[2]["amount"] = "N/A", "#-43.40"
    rows[3]["count"] = ".."
    write_csv(TARGET / f"mixed-{tag}.csv", rows)
    fields = publisher.declarations()
    marked = {**fields["amount"], "rules": {**fields["amount"]["rules"], "marks": ["#"]}}
    values = [dict(values) for values in TRUE_VALUES]
    values[0]["amount"], values[3]["count"] = None, None
    return {
        "mime": "CSV",
        "locale": tag,
        "rounds": [
            {"declare": {}, "halts": halts(rows)},
            {"declare": {"fields": fields}, "halts": {"amount": 2, "count": 1}},
            {"declare": {"fields": fields, "missingValues": ["N/A", ".."]}, "halts": {"amount": 1}},
            {"declare": {"fields": fields | {"amount": marked}, "missingValues": ["N/A", ".."]}, "halts": {}},
        ],
        "values": values,
    }


def footer() -> dict:
    """de_DE's file with a totals row, its amount a good number and its date column not a date at all."""
    tag = "de_DE"
    publisher = Publisher(tag)
    rows = [publisher.row(values) for values in TRUE_VALUES]
    total = sum(Decimal(v["amount"]) for v in TRUE_VALUES if v["amount"])
    rows.append(
        {name: "" for name in DESTINATION}
        | {"id": "Summe", "amount": publisher.amount(str(total)), "start": "Stand: April"}
    )
    write_csv(TARGET / f"footer-{tag}.csv", rows)
    fields = publisher.declarations()
    return {
        "mime": "CSV",
        "locale": tag,
        "rounds": [
            {"declare": {}, "halts": halts(rows)},
            {"declare": {"fields": fields}, "halts": {"start": 1}},
            {"declare": {"fields": fields, "actions": [f"DELETE_ROWS < [{len(rows) - 1}]"]}, "halts": {}},
        ],
        "values": TRUE_VALUES,
    }


def excel() -> dict:
    """en_GB's file as Excel leaves it on opening: a day-first date whose day could be a month becomes a date cell with
    the two swapped, the rest stay text; `SEPT2` becomes a date; `2310009E13` a number; and amounts become numbers."""
    tag = "en_GB"
    publisher = Publisher(tag)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(DESTINATION))
    values = [dict(row) for row in TRUE_VALUES]
    values[1]["id"], values[3]["id"] = "2024-09-02", "23100090000000000000"
    refused = {"balance": 0, "rate": 0, "count": 0, "start": 0, "end": 0, "active": 0}
    for row in TRUE_VALUES:
        written = publisher.row(row)
        cells = dict(written)
        cells["amount"] = None if row["amount"] is None else float(row["amount"])
        cells["count"] = None if row["count"] is None else int(row["count"])
        if row["id"] == "R002":
            cells["id"] = datetime(2024, 9, 2)
        if row["id"] == "R004":
            cells["id"] = 2310009e13
        if row["start"]:
            day = date.fromisoformat(row["start"])
            cells["start"] = datetime(day.year, day.day, day.month) if day.day <= 12 else written["start"]
        sheet.append([None if cells[name] == "" else cells[name] for name in DESTINATION])
        for name in refused:
            cell = cells[name]
            if isinstance(cell, str) and not COLD.reads(DESTINATION[name], cell):
                refused[name] += 1
    save(workbook, TARGET / f"excel-{tag}.xlsx")
    fields = publisher.declarations()
    swapped = {**fields["start"], "rules": {"cellFormats": {"d": "yyyy-dd-MM"}}}
    return {
        "mime": "XLSX",
        "locale": tag,
        "warns": {"id": 2},
        "rounds": [
            {"declare": {}, "halts": {name: count for name, count in refused.items() if count}},
            {"declare": {"fields": fields}, "halts": {}, "differs": ["start"]},
            {"declare": {"fields": fields | {"start": swapped}}, "halts": {}},
        ],
        "values": values,
    }


def main():
    assert not TARGET.exists(), f"{TARGET} exists; fixtures are never overwritten"
    TARGET.mkdir(parents=True)
    files = {f"{tag}.csv": clean(tag) for tag in LOCALES}
    files["mixed-en_GB.csv"] = mixed()
    files["footer-de_DE.csv"] = footer()
    files["excel-en_GB.xlsx"] = excel()
    key = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "conventions": {"source": "Unicode CLDR", "babel": CONVENTIONS["babel"]},
        "destination": {
            "fields": [
                {"name": name, "type": dtype} | ({"policy": {"base": "decimal"}} if name in EXACT else {})
                for name, dtype in DESTINATION.items()
            ]
        },
        "files": files,
    }
    (TARGET / "answer-key.json").write_text(json.dumps(key, indent=2, ensure_ascii=False), encoding="utf-8")
    print(len(files), "files written")


if __name__ == "__main__":
    main()
