# SPDX-License-Identifier: BSD-3-Clause
import re
from pathlib import Path

import fastexcel
import polars as pl
import python_calamine

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
    _ERROR = re.compile(r"Error\((\w+)\)")

    def __init__(self) -> None:
        self.cell = CellParser()
        self.grids = GridParser()

    def sheets(self, *, source: Path) -> list[tuple[str, bool]]:
        """Each worksheet's name, in workbook order, and whether its publisher hid it."""
        workbook = python_calamine.CalamineWorkbook.from_path(str(source))
        return [
            (m.name, m.visible != python_calamine.SheetVisibleEnum.Visible)
            for m in workbook.sheets_metadata
            if m.typ == python_calamine.SheetTypeEnum.WorkSheet
        ]

    def grid(self, *, source: Path, mime: MimeType, dialect: DialectModel) -> tuple[pl.DataFrame, list[int], DialectModel]:
        """A sheet's grid, the spreadsheet's number for each grid row, and the dialect naming the sheet.

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
                f"`{source.name}` has no sheet `{sheet}`. Its sheets are `{'`, `'.join(names)}`: name one in the "
                "dialect's `sheet`."
            )
        read = python_calamine.CalamineWorkbook.from_path(str(source)).get_sheet_by_name(sheet)
        rows = read.to_python(skip_empty_area=False)
        errors = self.errors(source=source, sheet=sheet, start=read.start)
        width = max((len(r) for r in rows), default=0)
        columns = {f"column_{j}": [] for j in range(width)}
        for i, row in enumerate(rows):
            for j in range(width):
                value = row[j] if j < len(row) else None
                code = errors.get((i, j))
                rendered = self.cell.render(value=code, error=True) if code else self.cell.render(value=value)
                columns[f"column_{j}"].append(None if rendered is None else rendered[1])
        grid = self.grids.trim(grid=pl.DataFrame(columns, schema={c: pl.String for c in columns}))
        return grid, list(range(1, grid.height + 1)), dialect.model_copy(update={"sheet": sheet})

    def errors(self, *, source: Path, sheet: str, start: tuple[int, int] | None) -> dict[tuple[int, int], str]:
        """Each error cell's code, by its row and column from A1."""
        if start is None:
            return {}
        read = fastexcel.read_excel(str(source)).load_sheet(sheet, header_row=None, dtypes="string")
        _, found = read.to_arrow_with_errors()
        codes = {}
        for error in found.errors if found else []:
            if kind := self._ERROR.search(error.detail):
                row, column = error.position
                codes[(start[0] + row, start[1] + column)] = self.ERRORS.get(kind.group(1), kind.group(1))
        return codes
