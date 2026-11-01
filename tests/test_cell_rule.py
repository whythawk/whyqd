# SPDX-License-Identifier: BSD-3-Clause
"""How a cell reads is whyqd's rule, not its reader's: every reader passes by giving what the rule gives.

The rule is `CellType.describe` and `ExcelParser`'s docstring. `tests/data/builders/cells.py` applies it to what each
workbook holds, with neither whyqd nor the reader in its path, so a reader's upgrade or replacement meets the rule or
fails here. A re-save that changes a cell's type or text changes that sheet's `fp0`, as it should.
"""

import json
from pathlib import Path
import shutil

import pytest

import whyqd as qd
from whyqd.dtypes import MimeType
from whyqd.models import DialectModel
from whyqd.parsers.excel_reader import ExcelParser

CELLS = Path(__file__).resolve().parent / "data" / "synthetic-cells"
KEY = json.loads((CELLS / "answer-key.json").read_text(encoding="utf-8"))
SHEETS = [(name, sheet) for name, entry in KEY.items() for sheet in entry["sheets"]]


def faults(name: str, sheet: str) -> list[str]:
    """The cells below 1 under a date's code that an `.xls` cannot read back, having no XML; none in an `.xlsx`."""
    if not name.endswith(".xls"):
        return []
    return [ref for refs in KEY[name]["sheets"][sheet]["cases"].values() for ref in refs]


def column(index: int) -> str:
    letters, index = "", index + 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def read(name: str, sheet: str) -> dict[str, list[str]]:
    mime = MimeType.XLS if name.endswith(".xls") else MimeType.XLSX
    grid, types, _, _ = ExcelParser().grid(source=CELLS / name, mime=mime, dialect=DialectModel(sheet=sheet))
    return {
        f"{column(j)}{i + 1}": [tag, text]
        for j, c in enumerate(grid.columns)
        for i, (text, tag) in enumerate(zip(grid[c].to_list(), types[c].to_list(), strict=True))
        if text is not None
    }


FAULTS = [
    pytest.param(
        name,
        sheet,
        marks=pytest.mark.xfail(strict=True, reason="the reader collapses values below 1, and an .xls has no XML"),
        id=f"{name}-{sheet}",
    )
    for name, sheet in SHEETS
    if faults(name, sheet)
]


class TestRule:
    @pytest.mark.parametrize(("name", "sheet"), SHEETS)
    def test_every_cell_reads_as_the_rule_gives(self, name, sheet):
        wanted, found = KEY[name]["sheets"][sheet]["cells"], read(name, sheet)
        leave = set(faults(name, sheet))
        assert {r: c for r, c in found.items() if r not in leave} == {r: c for r, c in wanted.items() if r not in leave}

    @pytest.mark.parametrize(("name", "sheet"), FAULTS)
    def test_a_value_below_one_in_an_xls_keeps_its_value(self, name, sheet):
        wanted, found = KEY[name]["sheets"][sheet]["cells"], read(name, sheet)
        assert {r: found.get(r) for r in faults(name, sheet)} == {r: wanted[r] for r in faults(name, sheet)}

    def test_the_date_systems_differ_by_their_days(self):
        one, four = (KEY[f"cells-{system}.xlsx"]["sheets"]["Dates"]["cells"] for system in (1900, 1904))
        row = next(r for r in range(1, 100) if one[f"A{r}"] == ["d", "2024-04-01"])
        assert four[f"A{row}"] == ["d", "2028-04-02"]

    def test_the_day_that_never_was_reads_as_the_day_before(self):
        one = KEY["cells-1900.xlsx"]["sheets"]["Dates"]["cells"]
        row = next(r for r in range(1, 100) if one[f"A{r}"] == ["d", "2024-04-01"])
        assert one[f"F{row}"] == one[f"G{row}"] == ["d", "1900-02-28"]


class TestResave:
    def test_a_resave_that_changes_cells_fails_where_it_changes_them(self, tmp_path):
        source = tmp_path / "cells.xlsx"
        shutil.copy(CELLS / "cells-1900.xlsx", source)
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=source, mimetype="XLSX")
        models = datasource.get
        shutil.copy(CELLS / "cells-1900-resaved.xlsx", source)
        before, after = (KEY[n]["sheets"] for n in ("cells-1900.xlsx", "cells-1900-resaved.xlsx"))
        changed = {s for s in before if before[s]["cells"] != after[s]["cells"]}
        assert changed
        for model in models:
            definition = qd.DataSourceDefinition(source=model)
            if model.dialect.sheet in changed:
                with pytest.raises(AssertionError, match="source-changed"):
                    definition.validate()
            else:
                with pytest.warns(UserWarning, match="source-saved-again"):
                    assert definition.validate()


class TestBelowOne:
    def test_a_sheet_with_no_time_does_not_open_its_xml(self, monkeypatch):
        def refuse(*args, **kwargs):
            raise AssertionError("The sheet's XML was opened.")

        monkeypatch.setattr("whyqd.parsers.excel_reader.zipfile.ZipFile", refuse)
        assert read("cells-1900.xlsx", "Cells")

    def test_a_tiny_value_rounding_down_stays_a_time(self):
        found = read("cells-1900.xlsx", "Dates")
        row = next(r for r in range(1, 100) if found[f"A{r}"] == ["d", "2024-04-01"])
        assert found[f"M{row}"] == ["d", "00:00:00"]


class TestOverflow:
    @pytest.mark.parametrize("suffix", [("xlsx", MimeType.XLSX), ("xls", MimeType.XLS)], ids=["xlsx", "xls"])
    @pytest.mark.parametrize(("sheet", "row"), [("Lengths", 3), ("Late", 5)])
    def test_a_duration_too_large_is_refused_by_sheet_and_row(self, suffix, sheet, row):
        name = f"overflow.{suffix[0]}"
        with pytest.raises(ValueError, match=rf"overflow\.{suffix[0]}.*{sheet}.*row {row} .*\[whyqd:duration-range\]"):
            ExcelParser().grid(source=CELLS / name, mime=suffix[1], dialect=DialectModel(sheet=sheet))

    def test_a_sheet_beside_it_reads(self):
        grid, _, _, _ = ExcelParser().grid(
            source=CELLS / "overflow.xlsx", mime=MimeType.XLSX, dialect=DialectModel(sheet="Plain")
        )
        assert grid.to_dict(as_series=False) == {"column_0": ["1"]}

    def test_it_blocks_deriving_the_workbook(self):
        datasource = qd.DataSourceDefinition()
        with pytest.raises(ValueError, match="duration-range"):
            datasource.derive_model(source=CELLS / "overflow.xlsx", mimetype="XLSX")
