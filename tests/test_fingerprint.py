# SPDX-License-Identifier: BSD-3-Clause
"""Two proofs of a source: its byte hash, which any byte changes, and `fp0`, which only a cell changes.

`fp0` hashes the file's grid as parsed, every sheet in workbook order, each cell its stored type and whyqd's text,
before any row is skipped, joined, or taken as the header, and before any cell is trimmed: it proves the source, not
the selection. A file saved again without a cell changed keeps its `fp0`, so it verifies with a warning. A PDF has the
byte hash only, since its grid depends on how it is read.
"""

from pathlib import Path
import warnings

import openpyxl
import pytest

import whyqd as qd
from whyqd.parsers import CoreParser

DATA = Path(__file__).resolve().parent / "data"
SYNTHETIC = DATA / "synthetic"
ENCODINGS = {
    "fixture-utf8.csv": None,
    "fixture-utf8-bom.csv": None,
    "fixture-utf8-crlf.csv": None,
    "fixture-utf8-mixed-eol.csv": None,
    "fixture-utf16-bom.csv": None,
    "fixture-latin-1.csv": None,
    "fixture-windows-1252.csv": None,
    "fixture-mac-roman.csv": "macintosh",
}


def derive(source: Path, mimetype: str, dialect: dict | None = None) -> qd.DataSourceDefinition:
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(source=source, mimetype=mimetype, dialect=dialect)
    return datasource


def workbook(path: Path, cells: dict[str, object], sheets: tuple[str, ...] = ("Data",)) -> Path:
    wb = openpyxl.Workbook()
    wb.active.title = sheets[0]
    for name in sheets[1:]:
        wb.create_sheet(name)
    for ws in wb.worksheets:
        for ref, value in cells.items():
            ws[ref] = value
    wb.save(path)
    return path


class TestFp0:
    def test_one_file_in_any_encoding_has_one_fp0(self):
        models = [
            derive(SYNTHETIC / name, "CSV", None if encoding is None else {"encoding": encoding}).get
            for name, encoding in ENCODINGS.items()
        ]
        assert len({m.get_checksum("fp0") for m in models}) == 1
        # The Latin-1 and Windows-1252 fixtures hold no byte that tells the two apart, so are one file
        assert len({m.get_checksum("bytes") for m in models}) == len({(SYNTHETIC / n).read_bytes() for n in ENCODINGS})

    def test_fp0_is_blake2b_512(self):
        model = derive(SYNTHETIC / "fixture-utf8.csv", "CSV").get
        fp0 = next(c for c in model.checksums if c.content == "fp0")
        assert fp0.algorithm == "BLAKE2b-512"
        assert len(fp0.checksumValue) == 128

    def test_fp0_is_taken_before_the_dialect_selects(self, tmp_path):
        source = tmp_path / "padded.csv"
        source.write_text("Title\nName,Code\n a ,1\n", encoding="utf-8")
        plain = derive(source, "CSV").get
        selected = derive(source, "CSV", {"skipRows": 1, "trim": True}).get
        assert [c.name for c in selected.columns] == ["Name", "Code"]
        assert plain.get_checksum("fp0") and selected.get_checksum("fp0") == plain.get_checksum("fp0")

    def test_a_trimmed_cell_reads_trimmed(self, tmp_path):
        source = tmp_path / "padded.csv"
        source.write_text("Name,Code\n a ,1\n", encoding="utf-8")
        datasource = derive(source, "CSV", {"trim": True})
        df = datasource.get_data()
        assert df["Name"].tolist() == ["a"]

    def test_every_sheet_of_a_workbook_shares_one_fp0(self, tmp_path):
        source = workbook(tmp_path / "two.xlsx", {"A1": "Name", "A2": "a"}, sheets=("One", "Two"))
        models = derive(source, "XLSX").get
        assert len(models) == 2
        assert models[0].get_checksum("fp0") and models[0].get_checksum("fp0") == models[1].get_checksum("fp0")

    def test_every_sheet_is_in_fp0(self, tmp_path):
        one = derive(workbook(tmp_path / "one.xlsx", {"A1": "Name", "A2": "a"}), "XLSX").get
        two = derive(workbook(tmp_path / "two.xlsx", {"A1": "Name", "A2": "a"}, sheets=("Data", "More")), "XLSX").get
        assert one.get_checksum("fp0") != two[0].get_checksum("fp0")

    def test_a_cells_stored_type_is_in_fp0(self, tmp_path):
        number = derive(workbook(tmp_path / "number.xlsx", {"A1": "Code", "A2": 12}), "XLSX").get
        text = derive(workbook(tmp_path / "text.xlsx", {"A1": "Code", "A2": "12"}), "XLSX").get
        assert number.get_checksum("fp0") != text.get_checksum("fp0")

    def test_a_pdf_has_the_byte_hash_only(self):
        pytest.importorskip("pdfplumber")
        model = derive(DATA / "sample" / "pdf" / "NNDR EXEMPTIONS.pdf", "PDF").get
        assert model.get_checksum("bytes")
        assert model.get_checksum("fp0") is None


class TestVerify:
    def test_a_file_saved_again_verifies_by_fp0_with_a_warning(self, tmp_path):
        source = workbook(tmp_path / "data.xlsx", {"A1": "Name", "A2": "a"})
        datasource = derive(source, "XLSX")
        wb = openpyxl.load_workbook(source)
        wb.active.column_dimensions["A"].width = 40
        wb.save(source)
        with pytest.warns(UserWarning, match="saved again"):
            assert datasource.validate()

    def test_an_unchanged_file_verifies_without_a_warning(self, tmp_path):
        source = workbook(tmp_path / "data.xlsx", {"A1": "Name", "A2": "a"})
        datasource = derive(source, "XLSX")
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert datasource.validate()

    def test_a_changed_cell_fails(self, tmp_path):
        source = workbook(tmp_path / "data.xlsx", {"A1": "Name", "A2": "a"})
        datasource = derive(source, "XLSX")
        workbook(source, {"A1": "Name", "A2": "b"})
        with pytest.raises(AssertionError, match="cells"):
            datasource.validate()

    def test_a_verified_1x_checksum_gains_fp0_and_the_byte_hash(self):
        pytest.importorskip("openpyxl")
        model = CoreParser().load_json(source=DATA / "raw_E06000044_014_0.data")
        datasource = qd.DataSourceDefinition(source=model)
        assert datasource.get.get_checksum("fp0") is None
        assert datasource.validate()
        derived = derive(DATA / "raw_E06000044_014_0.XLSX", "XLSX").get
        assert derived.get_checksum("fp0") and datasource.get.get_checksum("fp0") == derived.get_checksum("fp0")
        assert datasource.get.get_checksum("bytes") == derived.get_checksum("bytes")
