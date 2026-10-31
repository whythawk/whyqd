# SPDX-License-Identifier: BSD-3-Clause
import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import fastexcel
import polars as pl
import python_calamine

from whyqd.config.patterns import PythonPatterns
from whyqd.dtypes import MimeType
from whyqd.models import DialectModel
from whyqd.parsers.cell import CellParser
from whyqd.parsers.grid import GridParser


class ExcelParser:
    """A workbook's sheet as the grid: each cell its stored value in whyqd's text, never as displayed.

    Every sheet is read, a hidden one included, since it is the publisher's data; each is its own table. A cell is read
    from A1, so a sheet's rows are numbered as the spreadsheet numbers them. python-calamine gives each cell's value,
    but reads an error cell as empty, so fastexcel names the error cells, each read as its code (`#N/A`).
    """

    PLACE = "row"
    # Each error's code, as Excel shows it: calamine's `CellErrorType` (https://github.com/tafia/calamine, `lib.rs`)
    ERRORS = {
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
    BUILT_IN = {
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

    def __init__(self) -> None:
        self.cell = CellParser()
        self.grids = GridParser()
        self.patterns = PythonPatterns()

    def sheets(self, *, source: Path) -> list[tuple[str, bool]]:
        """Each worksheet's name, in workbook order, and whether its publisher hid it."""
        workbook = python_calamine.CalamineWorkbook.from_path(str(source))
        return [
            (m.name, m.visible != python_calamine.SheetVisibleEnum.Visible)
            for m in workbook.sheets_metadata
            if m.typ == python_calamine.SheetTypeEnum.WorkSheet
        ]

    def grid(
        self, *, source: Path, mime: MimeType, dialect: DialectModel
    ) -> tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel]:
        """A sheet's grid and each cell's stored type, the spreadsheet's number for each grid row, and the dialect
        naming the sheet.

        Parameters
        ----------
        source: Path
        mime: MimeType
            Read only to share the interface every reader has.
        dialect: DialectModel
            Its `sheet` names the sheet; a workbook of one sheet needs none.

        Raises
        ------
        ValueError
            For a sheet the workbook does not have, naming those it has.
        """
        names = [name for name, _ in self.sheets(source=source)]
        sheet = dialect.sheet
        if sheet is None and len(names) == 1:
            sheet = names[0]
        if sheet not in names:
            raise ValueError(
                f"`{source.name}` has no sheet `{sheet}`. Name one of `{'`, `'.join(names)}` in the dialect's `sheet`. "
                "[whyqd:sheet-unknown]"
            )
        read = python_calamine.CalamineWorkbook.from_path(str(source)).get_sheet_by_name(sheet)
        rows = read.to_python(skip_empty_area=False)
        errors = self.errors(source=source, sheet=sheet, start=read.start)
        width = max((len(r) for r in rows), default=0)
        columns = {f"column_{j}": [] for j in range(width)}
        types = {f"column_{j}": [] for j in range(width)}
        for i, row in enumerate(rows):
            for j in range(width):
                value = row[j] if j < len(row) else None
                code = errors.get((i, j))
                rendered = self.cell.render(value=code, error=True) if code else self.cell.render(value=value)
                columns[f"column_{j}"].append(None if rendered is None else rendered[1])
                types[f"column_{j}"].append(None if rendered is None else rendered[0].value)
        schema = {c: pl.String for c in columns}
        grid, types = self.grids.trim(grid=pl.DataFrame(columns, schema=schema), types=pl.DataFrame(types, schema=schema))
        return grid, types, list(range(1, grid.height + 1)), dialect.model_copy(update={"sheet": sheet})

    def formats(self, *, source: Path, sheet: str, height: int, width: int) -> pl.DataFrame:
        """Each cell's number format code in a sheet of an `.xlsx`, in the shape of its grid.

        No engine whyqd reads a workbook with gives a cell's format, so it is read from the workbook's XML: the code
        the workbook stores, a built-in id's from ECMA-376, or `id 5` for an id the standard leaves to the application.
        An `.xls` stores its formats in another form, and is not read for them.
        """
        codes = {f"column_{j}": [None] * height for j in range(width)}
        with zipfile.ZipFile(source) as book:
            workbook = self.parts(book=book, path="_rels/.rels", where="")["officeDocument"][0][0]
            folder, name = posixpath.split(workbook)
            parts = self.parts(book=book, path=posixpath.join(folder, "_rels", f"{name}.rels"), where=folder)
            ids = {}
            for element in ElementTree.fromstring(book.read(workbook)).iter():
                if self.local(element.tag) == "sheet":
                    ids[element.get("name")] = next(v for k, v in element.attrib.items() if self.local(k) == "id")
            path = next(target for target, i in parts["worksheet"] if i == ids[sheet])
            styles = self.styles(book=book, path=parts["styles"][0][0]) if "styles" in parts else []
            row = column = -1
            with book.open(path) as xml:
                for event, element in ElementTree.iterparse(xml, events=("start", "end")):
                    tag = self.local(element.tag)
                    if event == "start" and tag == "row":
                        row, column = (int(element.get("r")) - 1 if element.get("r") else row + 1), -1
                    elif event == "end" and tag == "c":
                        if reference := element.get("r"):
                            letters, number = self.patterns.CELL_REFERENCE.fullmatch(reference).groups()
                            row, column = int(number) - 1, self.column(letters=letters)
                        else:
                            column += 1
                        style = int(element.get("s", 0))
                        if row < height and column < width:
                            codes[f"column_{column}"][row] = styles[style] if style < len(styles) else self.BUILT_IN[0]
                        element.clear()
        return pl.DataFrame(codes, schema={c: pl.String for c in codes})

    def parts(self, *, book: zipfile.ZipFile, path: str, where: str) -> dict[str, list[tuple[str, str]]]:
        """A relationships part's targets by their type's last word (`worksheet`, `styles`), each with its id."""
        found = {}
        for element in ElementTree.fromstring(book.read(path)).iter():
            if self.local(element.tag) == "Relationship":
                target = element.get("Target")
                target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(where, target))
                found.setdefault(element.get("Type").rsplit("/", 1)[-1], []).append((target, element.get("Id")))
        return found

    def styles(self, *, book: zipfile.ZipFile, path: str) -> list[str]:
        """Each cell style's format code, by the style's index (`cellXfs`)."""
        root = ElementTree.fromstring(book.read(path))
        custom = {
            int(e.get("numFmtId")): e.get("formatCode") for e in root.iter() if self.local(e.tag) == "numFmt"
        }
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
