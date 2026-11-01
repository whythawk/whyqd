# SPDX-License-Identifier: BSD-3-Clause
"""Workbooks that hold a reader to the rule for a cell's type and text, and the key that rule gives for each.

The rule is `CellType.describe` and `ExcelParser`'s docstring. `build` writes a workbook in each date system as raw XML,
so that no library decides what it holds; `key` reads what each file holds, its XML or, for an `.xls`, through xlrd, and
applies the rule written out below. Neither imports whyqd or the reader under test, so a key cannot agree with a reader
by construction. A cell the rule reads where today's reader may not is named in the key's `cases`.

    python tests/data/builders/cells.py build tests/data/synthetic-cells
    soffice --headless --convert-to xls --outdir <directory> cells-1900.xlsx   # and cells-1904.xlsx, overflow.xlsx
    soffice --headless --convert-to xlsx --outdir <elsewhere> cells-1900.xlsx  # moved in as cells-1900-resaved.xlsx
    python tests/data/builders/cells.py key tests/data/synthetic-cells
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
import json
from pathlib import Path
import posixpath
import re
import sys
import zipfile
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import xlrd

CODES = [
    "General",
    "0.00",
    "0.0,,",
    "0.00E+00",
    "@",
    "#,##0.00_);[Red](#,##0.00)",
    '"Ref "0',
    '"date"0',
    "\\d0",
    '0" s"',
    "0*y",
    "[Red]0",
    "[$£-809]#,##0.00",
    "[>=100][Magenta].00",
    "yyyy-mm-dd",
    "*-yyyy-mm-dd",
    "dd/mm/yyyy",
    "d-mmm-yy",
    "mmm",
    "d",
    "y",
    "h:mm",
    "h:mm:ss",
    "h:mm AM/PM",
    "mm:ss",
    "mm:ss.000",
    "yyyy-mm-dd hh:mm:ss",
    "yyyy-mm-dd hh:mm:ss.000",
    "[h]:mm",
    "[mm]:ss",
    "[ss]",
    "[h]:mm:ss.000",
    "[Blue]\\+[h]:mm",
    "[$-409]d-mmm-yy",
    "[$-F800]dddd, mmmm dd, yyyy",
    "[$-F400]h:mm:ss AM/PM",
    "0;yyyy-mm-dd",
    "yyyy-mm-dd;0",
    "[>100]0;d-m-yy",
    'ggge"Y"m"M"d"D"',
    "ggge",
    "b2yyyy-mm-dd",
    "dd/mm/yyyy;@",
    "A/P",
    "aaa yyyy",
    "aaa/m/d",
]
BUILT_IN_IDS = [14, 15, 22, 30, 31, 36, 45, 46, 47, 50, 57, 5, 6, 7, 8, 41, 42, 43, 44, 81]
SERIALS = [
    "45383",
    "45383.5",
    "0.5",
    "1.5",
    "1",
    "59",
    "60",
    "61",
    "0",
    "45383.123456789",
    "0.99999999",
    "0.999999999",
    "0.000000001",
]
BEYOND = ["-1", "-0.5", "2958465", "2958465.9999", "2958466", "1000000000000000"]
SHARED = [
    "<si><t> </t></si>",
    '<si><t xml:space="preserve">  </t></si>',
    '<si><t xml:space="preserve"> a </t></si>',
    "<si><t> b </t></si>",
    "<si><t> c </t></si>",
    "<si><t></t></si>",
    "<si><t>12</t></si>",
    "<si><t>012</t></si>",
    "<si><t>2024-04-01</t></si>",
    "<si><t>01/04/2024</t></si>",
    "<si><t>TRUE</t></si>",
    "<si><t>#N/A</t></si>",
    "<si><t>a_x000D_b</t></si>",
    '<si><r><t>rich</t></r><r><t xml:space="preserve"> text</t></r></si>',
    '<si><t>x</t><rPh sb="0" eb="1"><t>phonetic</t></rPh></si>',
]
CELLS = [
    *[("s", str(i)) for i in range(len(SHARED))],
    ("str", "12"),
    ("str", " "),
    ("inlineStr", "inline"),
    ("b", "1"),
    ("b", "0"),
    ("e", "#N/A"),
    ("e", "#DIV/0!"),
    ("e", "#REF!"),
    ("e", "#NAME?"),
    ("e", "#NULL!"),
    ("e", "#NUM!"),
    ("e", "#VALUE!"),
    ("d", "2024-04-01T09:30:00"),
    ("d", "2024-04-01"),
    ("n", "0.30000000000000004"),
    ("n", "0.1"),
    ("n", "1E22"),
    ("n", "1E23"),
    ("n", "1E-7"),
    ("n", "0.0001"),
    ("n", "0.00001234"),
    ("n", "-0.00001234"),
    ("n", "1.0E+2"),
    ("n", "100.0"),
    ("n", "-12"),
    ("n", "12345678901234567"),
    ("n", "123456789012345678901234567890"),
    ("n", "-0"),
    ("n", "1.7976931348623157E308"),
    ("n", "0.1234567890123456789"),
]
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
PACKAGE = "http://schemas.openxmlformats.org/package/2006"
RELATIONSHIP = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SPREADSHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml"
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
SPACE = "{http://www.w3.org/XML/1998/namespace}space"
ESCAPED = re.compile(r"_x([0-9A-Fa-f]{4})_")
REFERENCE = re.compile(r"([A-Z]+)(\d+)")
DATE_IDS = {*range(14, 23), 45, 47}
DURATION_IDS = {46}
DAY = 86_400_000.0
FIRST_1904 = 1462.0
XML_WHITESPACE = " \t\r\n"


def column(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name


def worksheet(body: str) -> str:
    return f'{XML}<worksheet xmlns="{MAIN}"><sheetData>{body}</sheetData></worksheet>'


def number_sheet(rows: list[list[tuple[str, int]]]) -> str:
    body = []
    for i, row in enumerate(rows):
        cells = "".join(f'<c r="{column(j)}{i + 1}" s="{s}"><v>{v}</v></c>' for j, (v, s) in enumerate(row))
        body.append(f'<row r="{i + 1}">{cells}</row>')
    return worksheet("".join(body))


def cell_sheet() -> str:
    body = []
    for i, (t, v) in enumerate(CELLS):
        if t == "inlineStr":
            cell = f'<c r="A{i + 1}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
        elif t == "n":
            cell = f'<c r="A{i + 1}"><v>{v}</v></c>'
        else:
            preserve = ' xml:space="preserve"' if t == "str" and v != v.strip() else ""
            cell = f'<c r="A{i + 1}" t="{t}"><v{preserve}>{escape(v)}</v></c>'
        body.append(f'<row r="{i + 1}">{cell}</row>')
    return worksheet("".join(body))


def package(path: Path, sheets: dict[str, str], ids: list[int], custom: list[str], date1904: bool = False) -> None:
    """A workbook of these sheets' XML, its members dated alike, so a rebuild is the same bytes."""
    formats = "".join(
        f'<numFmt numFmtId="{164 + i}" formatCode="{escape(c, {chr(34): "&quot;"})}"/>' for i, c in enumerate(custom)
    )
    xfs = "".join(
        f'<xf numFmtId="{n}" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>' for n in ids
    )
    styles = (
        f'{XML}<styleSheet xmlns="{MAIN}"><numFmts count="{len(custom)}">{formats}</numFmts>'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
        '</fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        f'<cellXfs count="{len(ids)}">{xfs}</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
    )
    names = list(sheets)
    listed = "".join(f'<sheet name="{n}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(names))
    system = ' date1904="1"' if date1904 else ""
    workbook = f'{XML}<workbook xmlns="{MAIN}" xmlns:r="{RELATIONSHIP}"><workbookPr{system}/><sheets>{listed}</sheets></workbook>'
    relations = "".join(
        f'<Relationship Id="rId{i + 1}" Type="{RELATIONSHIP}/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
        for i in range(len(names))
    )
    relations += (
        f'<Relationship Id="rIdStyles" Type="{RELATIONSHIP}/styles" Target="styles.xml"/>'
        f'<Relationship Id="rIdStrings" Type="{RELATIONSHIP}/sharedStrings" Target="sharedStrings.xml"/>'
    )
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="{SPREADSHEET}.worksheet+xml"/>'
        for i in range(len(names))
    )
    parts = {
        "[Content_Types].xml": (
            f'{XML}<Types xmlns="{PACKAGE}/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{SPREADSHEET}.sheet.main+xml"/>{overrides}'
            f'<Override PartName="/xl/styles.xml" ContentType="{SPREADSHEET}.styles+xml"/>'
            f'<Override PartName="/xl/sharedStrings.xml" ContentType="{SPREADSHEET}.sharedStrings+xml"/></Types>'
        ),
        "_rels/.rels": (
            f'{XML}<Relationships xmlns="{PACKAGE}/relationships">'
            f'<Relationship Id="rId1" Type="{RELATIONSHIP}/officeDocument" Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": workbook,
        "xl/_rels/workbook.xml.rels": f'{XML}<Relationships xmlns="{PACKAGE}/relationships">{relations}</Relationships>',
        "xl/styles.xml": styles,
        "xl/sharedStrings.xml": (
            f'{XML}<sst xmlns="{MAIN}" count="{len(SHARED)}" uniqueCount="{len(SHARED)}">{"".join(SHARED)}</sst>'
        ),
        **{f"xl/worksheets/sheet{i + 1}.xml": sheets[n] for i, n in enumerate(names)},
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as book:
        for name, content in parts.items():
            book.writestr(zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)), content, zipfile.ZIP_DEFLATED)


def build(directory: Path) -> None:
    """The cells' workbook in each date system, and a workbook with a duration too large to read: in row 3, and in row
    5 of a sheet whose data starts at row 4."""
    directory.mkdir(parents=True, exist_ok=True)
    ids = [164 + i for i in range(len(CODES))] + BUILT_IN_IDS
    date_style, duration_style = CODES.index("yyyy-mm-dd"), CODES.index("[h]:mm")
    sheets = {
        "Dates": number_sheet([[(s, i) for s in SERIALS] for i in range(len(ids))]),
        "Beyond": number_sheet(
            [[(s, date_style) for s in BEYOND], [(s, duration_style) for s in BEYOND if s != "1000000000000000"]]
        ),
        "Cells": cell_sheet(),
    }
    package(directory / "cells-1900.xlsx", sheets, ids, CODES)
    package(directory / "cells-1904.xlsx", sheets, ids, CODES, date1904=True)
    overflow = number_sheet([[("1", 0)], [("2", 0)], [("1000000000000", 1)], [("4", 0)]])
    late = worksheet('<row r="4"><c r="B4"><v>1</v></c></row><row r="5"><c r="B5" s="1"><v>1000000000000</v></c></row>')
    package(
        directory / "overflow.xlsx",
        {"Plain": number_sheet([[("1", 0)]]), "Lengths": overflow, "Late": late},
        [0, 164],
        ["[h]:mm"],
    )


def kind(code: str) -> str:
    """Whether a number under this format code reads as a `date`, a `duration`, or a `number`, by the rule.

    The first section alone; quotes, whatever follows `\\`, `_`, or `*`, and brackets are never tokens, but for a
    bracket holding only `h`, `m`, or `s`, which is a duration. The first of `d m y h s` is a date. Once an `a` has
    come, only `/`, `m`, or `p` still makes one, so `aaa yyyy` is a number and `A/P` a date.
    """
    escaped = quoted = after_a = False
    i = 0
    while i < len(code):
        c, i = code[i], i + 1
        if escaped:
            escaped = False
        elif quoted:
            quoted = c != '"'
        elif c in "\\_*":
            escaped = True
        elif c == '"':
            quoted = True
        elif c == ";":
            return "number"
        elif c == "[":
            end = code.find("]", i)
            inner = code[i : len(code) if end < 0 else end].lower()
            if inner and inner[0] in "hms" and set(inner) == {inner[0]}:
                return "duration"
            i = len(code) if end < 0 else end + 1
        elif after_a:
            if c.lower() in "/mp":
                return "date"
        elif c.lower() == "a":
            after_a = True
        elif c.lower() in "dmyhs":
            return "date"
    return "number"


def whole_milliseconds(value: float) -> int:
    """A count of days as whole milliseconds: the double times 86,400,000 in double arithmetic, half away from zero."""
    return int(Decimal(value * DAY).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def number_text(value: float) -> str:
    """A whole number's exact integer digits; any other's shortest digits that return the same double, as `repr` lays
    them out: fixed from 1e-4 up, and below that `d.ddde-XX`."""
    return str(int(value)) if value == int(value) else repr(value)


def date_text(value: float, date1904: bool) -> tuple[str, str, str | None]:
    """A number under a date code: its type, its text, and the case a reader may not meet, if it is one."""
    if value < 0:
        return "n", number_text(value), "below-zero"
    days = value + FIRST_1904 if date1904 else value
    # The 1900 system's serial 60 is a day that never was, so it reads as serial 59 does, and those below it a day on
    days = days if days >= 60 else days + 1
    try:
        moment = datetime(1899, 12, 30) + timedelta(milliseconds=whole_milliseconds(days))
    except OverflowError:
        return "n", number_text(value), None
    midnight = moment.time() == datetime.min.time()
    if value >= 1 or (value >= 0.5 and midnight):
        return "d", moment.date().isoformat() if midnight else moment.isoformat(), None if value >= 1 else "rounds-up"
    return "d", moment.time().isoformat(), None


def duration_text(value: float) -> str:
    """A number under a duration code as ISO 8601, in hours, minutes, and seconds, a fraction's trailing zeros gone."""
    milliseconds = whole_milliseconds(value)
    sign, milliseconds = ("-", -milliseconds) if milliseconds < 0 else ("", milliseconds)
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, fraction = divmod(rest, 1000)
    second = f"{seconds}.{fraction:03d}".rstrip("0") if fraction else str(seconds)
    parts = f"{f'{hours}H' if hours else ''}{f'{minutes}M' if minutes else ''}{f'{second}S' if rest else ''}"
    return f"{sign}PT{parts or '0S'}"


def number_rule(value: float, reading: str, date1904: bool) -> tuple[str, str, str | None]:
    if reading == "date":
        return date_text(value, date1904)
    if reading == "duration":
        return "d", duration_text(value), None
    return "n", number_text(value), None


def text_rule(text: str, marked: bool) -> tuple[str, str, None] | None:
    """Text as the file holds it, XML's whitespace trimmed from its ends unless marked to keep it; empty, an empty
    cell."""
    text = text if marked else text.strip(XML_WHITESPACE)
    return ("s", text, None) if text else None


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def relations(book: zipfile.ZipFile, path: str, where: str) -> dict[str, dict[str, str]]:
    found = {}
    for e in ElementTree.fromstring(book.read(path)):
        target = e.get("Target")
        target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(where, target))
        found.setdefault(e.get("Type").rsplit("/", 1)[-1], {})[e.get("Id")] = target
    return found


def style_readings(book: zipfile.ZipFile, path: str) -> list[str]:
    """Each style's reading: its code where the workbook stores one, else its id's."""
    root = ElementTree.fromstring(book.read(path))
    codes = {int(e.get("numFmtId")): e.get("formatCode") for e in root.iter() if local(e.tag) == "numFmt"}
    xfs = next((e for e in root.iter() if local(e.tag) == "cellXfs"), [])
    return [id_reading(int(xf.get("numFmtId", 0)), codes) for xf in xfs]


def id_reading(number: int, codes: dict[int, str]) -> str:
    if number in codes:
        return kind(codes[number])
    return "date" if number in DATE_IDS else "duration" if number in DURATION_IDS else "number"


def unescape(text: str) -> str:
    return ESCAPED.sub(lambda m: chr(int(m.group(1), 16)), text)


def shared_strings(book: zipfile.ZipFile, path: str) -> list[tuple[str, bool]]:
    strings = []
    for si in ElementTree.fromstring(book.read(path)):
        phonetic = {id(t) for e in si if local(e.tag) == "rPh" for t in e.iter()}
        runs = [e for e in si.iter() if local(e.tag) == "t" and id(e) not in phonetic]
        strings.append((unescape("".join(e.text or "" for e in runs)), any(e.get(SPACE) == "preserve" for e in runs)))
    return strings


def xlsx_cell(e: ElementTree.Element, shared: list[tuple[str, bool]], readings: list[str], date1904: bool):
    t = e.get("t", "n")
    v = next((x for x in e if local(x.tag) == "v"), None)
    value = None if v is None else v.text or ""
    if t == "inlineStr":
        runs = [x for x in e.iter() if local(x.tag) == "t"]
        return text_rule(unescape("".join(x.text or "" for x in runs)), any(x.get(SPACE) == "preserve" for x in runs))
    if value is None:
        return None
    if t == "s":
        return text_rule(*shared[int(value)])
    if t == "str":
        return text_rule(unescape(value), v.get(SPACE) == "preserve")
    if t == "b":
        return "b", "TRUE" if value in ("1", "true") else "FALSE", None
    if t == "e":
        return "e", value, None
    if t == "d":
        moment = datetime.fromisoformat(value)
        return "d", moment.date().isoformat() if moment.time() == datetime.min.time() else moment.isoformat(), None
    if value == "":
        return None
    style = int(e.get("s", 0))
    return number_rule(float(value), readings[style] if style < len(readings) else "number", date1904)


def xlsx_sheets(path: Path) -> tuple[bool, dict]:
    with zipfile.ZipFile(path) as book:
        workbook = relations(book, "_rels/.rels", "")["officeDocument"]
        workbook = next(iter(workbook.values()))
        folder, name = posixpath.split(workbook)
        parts = relations(book, posixpath.join(folder, "_rels", f"{name}.rels"), folder)
        root = ElementTree.fromstring(book.read(workbook))
        date1904 = any(local(e.tag) == "workbookPr" and e.get("date1904", "0") in ("1", "true") for e in root.iter())
        ids = {
            e.get("name"): next(v for k, v in e.attrib.items() if local(k) == "id")
            for e in root.iter()
            if local(e.tag) == "sheet"
        }
        readings = style_readings(book, next(iter(parts["styles"].values())))
        shared = shared_strings(book, next(iter(parts["sharedStrings"].values()))) if "sharedStrings" in parts else []
        sheets = {}
        for sheet, rid in ids.items():
            cells = {}
            for e in ElementTree.fromstring(book.read(parts["worksheet"][rid])).iter():
                if local(e.tag) == "c":
                    cells[e.get("r")] = xlsx_cell(e, shared, readings, date1904)
            sheets[sheet] = cells
    return date1904, sheets


def xls_sheets(path: Path) -> tuple[bool, dict]:
    book = xlrd.open_workbook(path, formatting_info=True)
    date1904 = bool(book.datemode)
    codes = {f.format_key: f.format_str for f in book.format_list}
    sheets = {}
    for sheet in book.sheets():
        cells = {}
        for r in range(sheet.nrows):
            for c in range(sheet.ncols):
                kind_of, value = sheet.cell_type(r, c), sheet.cell_value(r, c)
                if kind_of in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    continue
                if kind_of == xlrd.XL_CELL_TEXT:
                    found = text_rule(value, True)
                elif kind_of == xlrd.XL_CELL_BOOLEAN:
                    found = "b", "TRUE" if value else "FALSE", None
                elif kind_of == xlrd.XL_CELL_ERROR:
                    found = "e", xlrd.error_text_from_code[value], None
                else:
                    number = book.xf_list[sheet.cell_xf_index(r, c)].format_key
                    found = number_rule(float(value), id_reading(number, codes), date1904)
                cells[f"{column(c)}{r + 1}"] = found
        sheets[sheet.name] = cells
    return date1904, sheets


def key(directory: Path) -> None:
    """The answer key for every workbook in this directory, each cell `[type, text]`, and the cells of each case."""
    found = {}
    for path in sorted(p for p in directory.iterdir() if p.suffix in (".xlsx", ".xls") and p.stem != "overflow"):
        date1904, sheets = xlsx_sheets(path) if path.suffix == ".xlsx" else xls_sheets(path)
        entry = {"date1904": date1904, "sheets": {}}
        for name, cells in sheets.items():
            kept = {ref: cell for ref, cell in cells.items() if cell is not None}
            cases = {}
            for ref, (_, _, case) in kept.items():
                if case:
                    cases.setdefault(case, []).append(ref)
            entry["sheets"][name] = {"cells": {r: [c[0], c[1]] for r, c in kept.items()}, "cases": cases}
        found[path.name] = entry
    (directory / "answer-key.json").write_text(json.dumps(found, indent=0, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    {"build": build, "key": key}[sys.argv[1]](Path(sys.argv[2]))
