# SPDX-License-Identifier: BSD-3-Clause
from collections.abc import Iterator
from datetime import date, time
import posixpath
import zipfile
from pathlib import Path
from typing import ClassVar
from xml.etree import ElementTree
from xml.parsers import expat

import fastexcel
import polars as pl
import python_calamine

from whyqd.config.patterns import PythonPatterns
from whyqd.dtypes import CellType, MimeType, Place
from whyqd.models import DialectModel
from whyqd.sources.cell import CellParser
from whyqd.sources.grid import GridParser, ReadFault
from whyqd.sources.reader import Reader


class ExcelParser(Reader):
    """A workbook's sheet as the grid: each cell its stored value in whyqd's text, never as displayed.

    Every sheet is read, a hidden one included, since it is the publisher's data; each is its own table. A cell is read
    from A1, so a sheet's rows are numbered as the spreadsheet numbers them. python-calamine gives each cell's value,
    but reads an error cell as empty, so fastexcel names the error cells, each read as its code (`#N/A`).

    A workbook stores a date as a number under a format, so the format decides how a number reads, by this rule, which
    a reader passes by matching the fixtures in `tests/test_cell_rule.py`:

    - **Which**: a stored code's first section alone. Quotes, whatever follows `\\`, `_`, or `*`, and brackets are not
      tokens, but for a bracket holding only `h`, `m`, or `s`, which makes a duration. The first of `d m y h s` makes a
      date; once an `a` has come, only `/`, `m`, or `p` still does. A built-in id with no stored code: 14 to 22, 45, and
      47 are dates, 46 a duration, every other a number. Anything else is a number.
    - **A date**: the value, plus 1462 in the 1904 system, plus 1 in the 1900 system if that is below 60, is the days
      since 1899-12-30; times 86,400,000 in double arithmetic, and rounded half away from zero, the milliseconds. So
      1900's serial 60, a day that never was, reads `1900-02-28`, as serial 59 does. From 0 up to 1, the time alone,
      unless it rounds up to a whole day, which reads as that date.
    - **A duration**: the value in days, to the millisecond by the same arithmetic, as `CellType` describes.
    - **No sensible date**: a value below 0 under a date's code, or past the year 9999, reads as the number.
    - **Too large**: a duration past what the reader can hold is refused, naming its sheet and row.

    python-calamine gives every value below 1 under a date's code as a time, losing a negative's value and a rounded
    day. An `.xlsx` is read back from its XML for those, and only where a sheet holds a time; an `.xls` stores its cells
    in another form, and is not, so there they read as python-calamine gives them.
    """

    PLACE: ClassVar[Place] = Place.ROW
    DIALECT: ClassVar[tuple[str, ...]] = ("sheet",)
    WORKBOOK: ClassVar[bool] = True
    # Each error's code, as Excel shows it: calamine's `CellErrorType` (https://github.com/tafia/calamine, `lib.rs`)
    ERRORS: ClassVar[dict[str, str]] = {
        "Div0": "#DIV/0!",
        "NA": "#N/A",
        "Name": "#NAME?",
        "Null": "#NULL!",
        "Num": "#NUM!",
        "Ref": "#REF!",
        "Value": "#VALUE!",
        "GettingData": "#DATA!",
    }
    # Each built-in format's code, stored as an id alone, for the ids every language shares: ECMA-376 Part 1,
    # section 18.8.30 (https://ecma-international.org/publications-and-standards/standards/ecma-376/)
    BUILT_IN: ClassVar[dict[int, str]] = {
        0: "General",
        1: "0",
        2: "0.00",
        3: "#,##0",
        4: "#,##0.00",
        9: "0%",
        10: "0.00%",
        11: "0.00E+00",
        12: "# ?/?",
        13: "# ??/??",
        14: "mm-dd-yy",
        15: "d-mmm-yy",
        16: "d-mmm",
        17: "mmm-yy",
        18: "h:mm AM/PM",
        19: "h:mm:ss AM/PM",
        20: "h:mm",
        21: "h:mm:ss",
        22: "m/d/yy h:mm",
        37: "#,##0 ;(#,##0)",
        38: "#,##0 ;[Red](#,##0)",
        39: "#,##0.00;(#,##0.00)",
        40: "#,##0.00;[Red](#,##0.00)",
        45: "mm:ss",
        46: "[h]:mm:ss",
        47: "mmss.0",
        48: "##0.0E+0",
        49: "@",
    }

    # The date of serial 1, by whether the workbook is in the 1904 date system
    SERIAL_ONE: ClassVar[dict[bool, date]] = {False: date(1900, 1, 1), True: date(1904, 1, 2)}
    CHUNK_BYTES: ClassVar[int] = 1 << 16

    def __init__(self) -> None:
        self.cell = CellParser()
        self.grids = GridParser()
        self.patterns = PythonPatterns()

    def sheets(self, *, source: Path) -> list[tuple[str, bool]]:
        """Each worksheet's name, in workbook order, and whether its publisher hid it.

        Raises
        ------
        ValueError
            For a file that is not a sound workbook.
        """
        return self.listed(workbook=self.opened(source=source))

    def opened(self, *, source: Path) -> python_calamine.CalamineWorkbook:
        """The workbook, open for reading, refused where the file is not a sound one."""
        try:
            return python_calamine.CalamineWorkbook.from_path(str(source))
        except python_calamine.CalamineError as e:
            raise self.unreadable(source=source, kind="a workbook") from e

    def listed(self, *, workbook: python_calamine.CalamineWorkbook) -> list[tuple[str, bool]]:
        """An open workbook's worksheets, in order, each with whether its publisher hid it."""
        return [
            (m.name, m.visible != python_calamine.SheetVisibleEnum.Visible)
            for m in workbook.sheets_metadata
            if m.typ == python_calamine.SheetTypeEnum.WorkSheet
        ]

    def grid(
        self, *, source: Path, mime: MimeType, dialect: DialectModel
    ) -> tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel]:
        """A sheet's grid and each cell's type, the spreadsheet's number for each grid row, and the dialect naming the
        sheet.

        Parameters
        ----------
        source: Path
        mime: MimeType
            Whether the workbook has XML to read a lost value back from.
        dialect: DialectModel
            Its `sheet` names the sheet; a workbook of one sheet needs none.

        Raises
        ------
        ValueError
            For a sheet the workbook does not have, naming those it has, or a duration too large to read.
        """
        workbook = self.opened(source=source)
        names = [name for name, _ in self.listed(workbook=workbook)]
        sheet = dialect.sheet
        if sheet is None and len(names) == 1:
            sheet = names[0]
        if sheet not in names:
            raise ReadFault(
                f"`{source.name}` has no sheet `{sheet}`. Name one of `{'`, `'.join(names)}` in the dialect's `sheet`. "
                "[whyqd:sheet-unknown]",
                setting="sheet",
            )
        read = workbook.get_sheet_by_name(sheet)
        try:
            rows = read.to_python(skip_empty_area=False)
        except OverflowError as e:
            raise ValueError(
                f"`{source.name}` sheet `{sheet}` row {self.overflow_row(read=read)} holds a duration too large to "
                "read. Change that cell's format to a number and derive from that copy. [whyqd:duration-range]"
            ) from e
        errors = self.errors(source=source, sheet=sheet, start=read.start)
        lost = {}
        if mime == MimeType.XLSX and any(isinstance(value, time) for row in rows for value in row):
            lost = self.below_one(source=source, sheet=sheet, rows=rows)
        width = max((len(r) for r in rows), default=0)
        columns, types = [[] for _ in range(width)], [[] for _ in range(width)]
        for i, row in enumerate(rows):
            for j in range(width):
                value = lost.get((i, j), row[j] if j < len(row) else None)
                code = errors.get((i, j))
                rendered = self.cell.render(value=code, error=True) if code else self.cell.render(value=value)
                columns[j].append(None if rendered is None else rendered[1])
                types[j].append(None if rendered is None else rendered[0].value)
        grid, types = self.grids.build(columns=columns, types=types)
        return grid, types, self.grids.numbers(grid=grid), dialect.model_copy(update={"sheet": sheet})

    def facts(self, *, source: Path, sheet: str | None, types: pl.DataFrame) -> dict[str, list[str]]:
        """What a sheet holds that its grid's text does not show: its `merged` ranges and its `errors`, each cell named
        as a workbook names it, in reading order."""
        read = self.opened(source=source).get_sheet_by_name(sheet)
        merged = sorted(read.merged_cell_ranges or [])
        errors = sorted(
            (i, j) for j, c in enumerate(types.columns) for i in types[c].eq(CellType.ERROR.value).arg_true().to_list()
        )
        reference = self.reference
        return {
            "merged": [f"{reference(row=a, column=b)}:{reference(row=c, column=d)}" for (a, b), (c, d) in merged],
            "errors": [self.reference(row=i, column=j) for i, j in errors],
        }

    def reference(self, *, row: int, column: int) -> str:
        """A cell's reference from its row and column, each counted from 0: `B3` is row 2, column 1."""
        letters, column = "", column + 1
        while column:
            column, remainder = divmod(column - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row + 1}"

    def formats(
        self, *, source: Path, mime: MimeType, sheet: str | None, height: int, width: int
    ) -> pl.DataFrame | None:
        """Each cell's number format code in a sheet of an `.xlsx`, in the shape of its grid.

        No engine whyqd reads a workbook with gives a cell's format, so it is read from the workbook's XML: the code
        the workbook stores, a built-in id's from ECMA-376, or `id 5` for an id the standard leaves to the application.
        An `.xls` stores its formats in another form, and is not read for them: `None`.
        """
        if mime != MimeType.XLSX:
            return None
        codes = {self.grids.COLUMN.format(j): [None] * height for j in range(width)}
        with zipfile.ZipFile(source) as book:
            _, parts, path = self.locate(book=book, sheet=sheet)
            styles = self.styles(book=book, path=parts["styles"][0][0]) if "styles" in parts else []
            for row, column, attributes, _ in self.walk(book=book, path=path):
                style = int(attributes.get("s", 0))
                if row < height and column < width:
                    codes[self.grids.COLUMN.format(column)][row] = (
                        styles[style] if style < len(styles) else self.BUILT_IN[0]
                    )
        return pl.DataFrame(codes, schema={c: pl.String for c in codes})

    def below_one(self, *, source: Path, sheet: str, rows: list[list]) -> dict[tuple[int, int], float | date]:
        """What each time in a sheet of an `.xlsx` reads as where the reader lost its value, by its row and column
        from A1: a stored number below 0 as that number, and one that rounded up to midnight as the date of serial 1.

        A value that small rounding down to midnight is a time, and stands.
        """
        lost = {}
        with zipfile.ZipFile(source) as book:
            workbook, _, path = self.locate(book=book, sheet=sheet)
            date1904 = any(
                self.local(e.tag) == "workbookPr" and e.get("date1904", "0") in ("1", "true") for e in workbook.iter()
            )
            for row, column, attributes, text in self.walk(book=book, path=path, values=True):
                value = rows[row][column] if row < len(rows) and column < len(rows[row]) else None
                if not isinstance(value, time) or attributes.get("t", "n") != "n":
                    continue
                stored = float(text)
                if stored < 0:
                    lost[(row, column)] = stored
                elif stored >= 0.5 and value == time(0):
                    lost[(row, column)] = self.SERIAL_ONE[date1904]
        return lost

    def overflow_row(self, *, read: python_calamine.CalamineSheet) -> int:
        """The spreadsheet's number for the row holding a duration too large to read, where the reader, counting
        from A1, stops."""
        count = 0
        try:
            for _ in read.iter_rows():
                count += 1
        except OverflowError:
            pass
        return count + 1

    def locate(self, *, book: zipfile.ZipFile, sheet: str) -> tuple[ElementTree.Element, dict, str]:
        """A workbook's root, its parts by their type's last word, and the path of this sheet's XML."""
        workbook = self.parts(book=book, path="_rels/.rels", where="")["officeDocument"][0][0]
        folder, name = posixpath.split(workbook)
        parts = self.parts(book=book, path=posixpath.join(folder, "_rels", f"{name}.rels"), where=folder)
        root = ElementTree.fromstring(book.read(workbook))
        ids = {
            e.get("name"): next(v for k, v in e.attrib.items() if self.local(k) == "id")
            for e in root.iter()
            if self.local(e.tag) == "sheet"
        }
        return root, parts, next(target for target, i in parts["worksheet"] if i == ids[sheet])

    def walk(
        self, *, book: zipfile.ZipFile, path: str, values: bool = False
    ) -> Iterator[tuple[int, int, dict[str, str], str | None]]:
        """Each cell in a sheet's XML by its row and column from A1, with its attributes and, where `values` asks, its
        stored value, streamed.

        Only a cell's start is handled unless its value is asked for, since building every element, or handling every
        run of text, is most of the time a large sheet takes. A cell is held back until the next one starts, so its value
        is whole when it is given.
        """
        cells: list[list] = []
        row = column = -1
        stored: list[str] | None = None

        def start(name: str, attributes: dict[str, str]) -> None:
            nonlocal row, column, stored
            tag = self.local(name)
            if tag == "row":
                row, column = (int(attributes["r"]) - 1 if "r" in attributes else row + 1), -1
            elif tag == "c":
                if reference := attributes.get("r"):
                    letters, number = self.patterns.CELL_REFERENCE.fullmatch(reference).groups()
                    row, column = int(number) - 1, self.column(letters=letters)
                else:
                    column += 1
                cells.append([row, column, attributes, None])
            elif tag == "v" and values:
                stored = []

        def text(data: str) -> None:
            if stored is not None:
                stored.append(data)

        def end(name: str) -> None:
            nonlocal stored
            if stored is not None and self.local(name) == "v":
                cells[-1][3], stored = "".join(stored), None

        parser = expat.ParserCreate(namespace_separator="}")
        parser.StartElementHandler = start
        if values:
            parser.buffer_text = True
            parser.CharacterDataHandler, parser.EndElementHandler = text, end
        with book.open(path) as xml:
            while chunk := xml.read(self.CHUNK_BYTES):
                parser.Parse(chunk, False)
                yield from (tuple(cell) for cell in cells[:-1])
                del cells[:-1]
            parser.Parse(b"", True)
            yield from (tuple(cell) for cell in cells)

    def parts(self, *, book: zipfile.ZipFile, path: str, where: str) -> dict[str, list[tuple[str, str]]]:
        """A relationships part's targets by their type's last word (`worksheet`, `styles`), each with its id."""
        found = {}
        for element in ElementTree.fromstring(book.read(path)).iter():
            if self.local(element.tag) == "Relationship":
                target = element.get("Target")
                target = (
                    target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(where, target))
                )
                found.setdefault(element.get("Type").rsplit("/", 1)[-1], []).append((target, element.get("Id")))
        return found

    def styles(self, *, book: zipfile.ZipFile, path: str) -> list[str]:
        """Each cell style's format code, by the style's index (`cellXfs`)."""
        root = ElementTree.fromstring(book.read(path))
        custom = {int(e.get("numFmtId")): e.get("formatCode") for e in root.iter() if self.local(e.tag) == "numFmt"}
        cell_styles = next((e for e in root.iter() if self.local(e.tag) == "cellXfs"), [])
        codes = []
        for xf in cell_styles:
            number = int(xf.get("numFmtId", 0))
            codes.append(custom.get(number, self.BUILT_IN.get(number, f"id {number}")))
        return codes

    def column(self, *, letters: str) -> int:
        """A column's index from 0, by its letters: `A` is 0, `AA` 26."""
        index = 0
        for letter in letters:
            index = index * 26 + ord(letter) - 64
        return index - 1

    def local(self, tag: str) -> str:
        """An XML name without its namespace, so a workbook in either of ECMA-376's namespaces reads."""
        return tag.rsplit("}", 1)[-1]

    def errors(self, *, source: Path, sheet: str, start: tuple[int, int] | None) -> dict[tuple[int, int], str]:
        """Each error cell's code, by its row and column from A1."""
        if start is None:
            return {}
        read = fastexcel.read_excel(str(source)).load_sheet(sheet, header_row=None, dtypes="string")
        _, found = read.to_arrow_with_errors()
        codes = {}
        for error in found.errors if found else []:
            if kind := self.patterns.EXCEL_ERROR.search(error.detail):
                row, column = error.position
                codes[(start[0] + row, start[1] + column)] = self.ERRORS.get(kind.group(1), kind.group(1))
        return codes
