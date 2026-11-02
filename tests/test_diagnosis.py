# SPDX-License-Identifier: BSD-3-Clause
"""A report on how a file was read and what was found there, held to the layout fixtures' answer key.

Each file is read with no setting declared, as a wrangler first loads it. A report interprets nothing: its findings are
what the file holds, and it proposes a setting only for a file that cannot be read as written, and only when asked.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.models import FindingModel, ReportModel

LAYOUTS = Path(__file__).resolve().parent / "data" / "synthetic-layouts"
KEY = json.loads((LAYOUTS / "answer-key.json").read_text(encoding="utf-8"))
CSV = [(name, "CSV", {}, case) for name, case in KEY["csv"].items()]
WORKBOOK = [
    (name, "XLSX", {"sheet": sheet}, case)
    for name, sheets in KEY["workbook"].items()
    if name.endswith(".xlsx")
    for sheet, case in sheets.items()
]
CASES = CSV + WORKBOOK
IDS = [f"{name}-{dialect.get('sheet', '')}" for name, _, dialect, _ in CASES]
SYNTHETIC = LAYOUTS.parent / "synthetic"
FENLAND = LAYOUTS.parent / "sample" / "fenland" / "2026-10-25-Fenland District Council.csv"
ASTERISK = sorted((LAYOUTS.parent / "sample" / "voa").glob("*.csv"))


def diagnose_source(source: Path, mimetype: str, dialect: dict, propose: bool = False) -> ReportModel:
    reports = qd.DataSourceDefinition().diagnose(
        source=source, mimetype=mimetype, dialect=dialect or None, propose=propose
    )
    assert len(reports) == 1
    return reports[0]


def diagnose(name: str, mimetype: str, dialect: dict, propose: bool = False) -> ReportModel:
    return diagnose_source(LAYOUTS / name, mimetype, dialect, propose)


def found(report: ReportModel) -> dict[str, dict]:
    return {
        f.code: {k: getattr(f, k) for k in ("rows", "columns", "cells", "setting") if getattr(f, k)}
        for f in report.findings
    }


@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_each_layout_finds_what_its_key_says(name, mimetype, dialect, case):
    assert found(diagnose(name, mimetype, dialect)) == case["findings"]


@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_each_layout_proposes_what_its_key_says(name, mimetype, dialect, case):
    report = diagnose(name, mimetype, dialect, propose=True)
    assert {p.setting: p.value for p in report.proposals} == case["proposals"]
    assert all(p.evidence for p in report.proposals)


@pytest.mark.parametrize("name", [n for n, case in KEY["csv"].items() if case["proposals"]])
def test_each_proposal_once_declared_reads_to_the_key(name):
    case = KEY["csv"][name]
    report = diagnose(name, "CSV", {}, propose=True)
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(
        source=LAYOUTS / name, mimetype="CSV", dialect={p.setting: p.value for p in report.proposals}
    )
    df = datasource.get_data()
    assert [c.name for c in datasource.get.columns] == case["names"]
    assert [[None if pd.isna(c) else c for c in row] for row in df[case["names"]].values.tolist()] == [
        [c if c != "" else None for c in row] for row in case["rows"]
    ]


def test_fenland_is_proposed_its_records():
    report = diagnose_source(FENLAND, "CSV", {}, propose=True)
    assert [(p.setting, p.value) for p in report.proposals] == [("rowsPerRecord", [47, 1])]


def test_a_file_declared_its_records_is_not_proposed_them_again():
    assert diagnose_source(FENLAND, "CSV", {"rowsPerRecord": [47, 1]}, propose=True).proposals == []


@pytest.mark.parametrize(
    "name,dialect,proposed",
    [
        ("fixture-mac-roman.csv", {}, "macintosh"),
        ("fixture-windows-1252.csv", {}, None),
        ("fixture-windows-1252.csv", {"encoding": "utf-8"}, "windows-1252"),
        ("fixture-utf8.csv", {}, None),
        ("fixture-utf8-bom.csv", {}, None),
    ],
)
def test_an_encoding_is_proposed_only_for_a_file_that_did_not_decode_as_itself(name, dialect, proposed):
    report = diagnose_source(SYNTHETIC / name, "CSV", dialect, propose=True)
    assert [p.value for p in report.proposals if p.setting == "encoding"] == ([proposed] if proposed else [])


def test_without_the_extra_a_finding_says_so_where_an_encoding_would_be_proposed(monkeypatch):
    monkeypatch.setitem(sys.modules, "charset_normalizer", None)
    report = diagnose_source(SYNTHETIC / "fixture-mac-roman.csv", "CSV", {}, propose=True)
    assert report.proposals == []
    assert "diagnose-extra" in [f.code for f in report.findings]
    assert diagnose_source(SYNTHETIC / "fixture-utf8.csv", "CSV", {}, propose=True).findings == []


def test_detection_does_not_run_in_a_load(monkeypatch):
    monkeypatch.setitem(sys.modules, "charset_normalizer", None)
    qd.DataSourceDefinition().derive_model(source=SYNTHETIC / "fixture-mac-roman.csv", mimetype="CSV")


def test_a_clean_comma_file_with_semicolons_in_its_cells_is_not_second_guessed(tmp_path):
    source = tmp_path / "semis.csv"
    source.write_text("a,b\n1;2,3\n4;5,6\n", encoding="utf-8")
    assert diagnose_source(source, "CSV", {}, propose=True).proposals == []


def test_an_uneven_comma_file_with_a_character_on_every_line_is_not_second_guessed(tmp_path):
    source = tmp_path / "uneven.csv"
    source.write_text("a/b,c,d\n1/2,3,4\n5/6,7\n", encoding="utf-8")
    assert diagnose_source(source, "CSV", {}, propose=True).proposals == []


@pytest.mark.parametrize("source", ASTERISK, ids=[p.name[:40] for p in ASTERISK])
def test_any_character_may_be_proposed_as_a_delimiter(source):
    # One holds commas in its addresses and gives each line 34 cells; the other no comma, and several kinds of record
    report = diagnose_source(source, "CSV", {}, propose=True)
    assert [(p.setting, p.value) for p in report.proposals] == [("delimiter", "*")]
    assert diagnose_source(source, "CSV", {"delimiter": "*"}, propose=True).proposals == []


def test_a_delimiter_is_proposed_where_the_one_read_by_is_in_no_line(tmp_path):
    source = tmp_path / "no-commas.csv"
    source.write_text("a*b*c\n1*2*3\n4*5*6\n", encoding="utf-8")
    assert [p.value for p in diagnose_source(source, "CSV", {}, propose=True).proposals] == ["*"]


def test_a_single_column_is_not_given_a_delimiter(tmp_path):
    source = tmp_path / "single.csv"
    source.write_text("name\nalpha\nbeta\n", encoding="utf-8")
    assert diagnose_source(source, "CSV", {}, propose=True).proposals == []


def test_two_characters_that_both_fit_leave_the_delimiter_unproposed(tmp_path):
    source = tmp_path / "mixed.csv"
    source.write_text("a*b;c\n1*2;3\n4*5;6\n", encoding="utf-8")
    assert diagnose_source(source, "CSV", {}, propose=True).proposals == []


@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_nothing_is_proposed_unasked(name, mimetype, dialect, case):
    assert diagnose(name, mimetype, dialect).proposals == []


@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_two_runs_give_the_same_report(name, mimetype, dialect, case):
    assert diagnose(name, mimetype, dialect, propose=True) == diagnose(name, mimetype, dialect, propose=True)


def test_diagnosing_changes_nothing_about_the_read():
    def derived() -> qd.models.DataSourceModel:
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=LAYOUTS / "title-above.csv", mimetype="CSV")
        return datasource.get

    before = derived()
    definition = qd.DataSourceDefinition()
    definition.diagnose(source=LAYOUTS / "title-above.csv", mimetype="CSV", propose=True)
    assert definition.get is None
    after = derived()
    assert after.dialect == before.dialect
    assert after.checksums == before.checksums


def test_a_declared_setting_is_reported_as_declared():
    report = diagnose("title-above.csv", "CSV", {"skipRows": 3})
    sources = {s.name: s.source for s in report.settings}
    assert sources["skipRows"] == "declared"
    assert sources["delimiter"] == "default"
    assert sources["encoding"] == "file"


def test_a_file_that_will_not_read_still_gives_a_report():
    report = diagnose("stray-quote.csv", "CSV", {})
    assert report.findings[0].kind == "fault"
    assert report.findings[0].code == "csv-quote"
    assert report.settings == []


def test_a_backslash_file_is_told_to_declare_double_quote():
    with pytest.raises(ValueError, match="declare `doubleQuote` as false"):
        qd.DataSourceDefinition().derive_model(source=LAYOUTS / "backslash-escape.csv", mimetype="CSV")


@pytest.mark.parametrize(
    "name,mimetype",
    [
        ("bad.xlsx", "XLSX"),
        ("bad.xls", "XLS"),
        ("bad.parquet", "PARQUET"),
        ("bad.feather", "FEATHER"),
        ("bad.pdf", "PDF"),
    ],
)
def test_a_file_that_is_not_its_format_is_a_finding_in_whyqds_terms(tmp_path, name, mimetype):
    source = tmp_path / name
    source.write_bytes(b"not what it says")
    with pytest.raises(ValueError, match=r"\[whyqd:file-unreadable\]"):
        qd.DataSourceDefinition().derive_model(source=source, mimetype=mimetype)
    reports = qd.DataSourceDefinition().diagnose(source=source, mimetype=mimetype)
    assert [f.code for r in reports for f in r.findings] == ["file-unreadable"]


def test_an_unknown_sheet_is_a_finding_naming_the_setting():
    assert found(diagnose("layouts.xlsx", "XLSX", {"sheet": "Nope"})) == {"sheet-unknown": {"setting": "sheet"}}


def test_a_declaration_the_file_does_not_fit_is_a_finding_beside_the_read():
    report = diagnose("title-above.csv", "CSV", {"skipRows": 50})
    assert found(report) == {"header-past-end": {"setting": "skipRows"}, "blank-rows": {"rows": [2, 3]}}
    assert report.settings and report.height == 10


def test_a_declaration_whyqd_cannot_read_is_refused_not_reported():
    with pytest.raises(ValueError, match=r"\[whyqd:dialect-unknown\]"):
        diagnose("title-above.csv", "CSV", {"header": 3})


def test_bytes_that_did_not_decode_are_a_fault_naming_the_encoding_setting():
    report = diagnose_source(SYNTHETIC / "fixture-windows-1252.csv", "CSV", {"encoding": "utf-8"})
    assert report.findings[0].code == "encoding-replaced"
    assert report.findings[0].kind == "fault"
    assert report.findings[0].setting == "encoding"
    assert "commonest" in report.findings[0].message


def test_a_merged_range_reads_the_same_from_both_workbook_formats():
    cells = {"merged-range": {"cells": ["A1:A2", "B1:C1", "D1:E1"]}}
    assert found(diagnose("layouts.xlsx", "XLSX", {"sheet": "MergedHeader"})) == cells
    assert found(diagnose("layouts.xls", "XLS", {"sheet": "MergedHeader"})) == cells


def test_each_sheet_of_a_workbook_has_its_own_report():
    reports = qd.DataSourceDefinition().diagnose(source=LAYOUTS / "layouts.xlsx", mimetype="XLSX")
    assert [r.sheet for r in reports] == list(KEY["workbook"]["layouts.xlsx"])
    assert [f.code for f in reports[-1].findings] == ["hidden-sheet"]


def test_row_widths_show_a_files_shape_without_a_finding():
    # Fenland's records each span two lines: 47 fields, then one
    report = diagnose_source(FENLAND, "CSV", {})
    assert report.rowWidths == {1: 51, 47: 51}
    assert report.findings == []


def test_the_rows_above_a_header_can_be_seen_in_the_preview():
    report = diagnose("title-above.csv", "CSV", {"skipRows": 3})
    assert report.place == "line"
    assert "line 1: Business rates reliefs, April 2026" in report.preview


def test_the_preview_shows_the_top_and_end_of_a_long_file_with_cells_cut(tmp_path):
    source = tmp_path / "long.csv"
    source.write_text("".join(f"{i},{'x' * 60}\n" for i in range(100)), encoding="utf-8")
    preview = diagnose_source(source, "CSV", {}).preview.splitlines()
    assert preview[0].startswith("line 1: 0 | xxx")
    assert preview[0].endswith("…")
    assert preview[15] == "... 80 lines not shown ..."
    assert preview[-1].startswith("line 100: 99 | ")
    assert len(preview) == 21


def test_a_columnar_file_reports_with_no_settings_of_a_text_file():
    report = diagnose_source(LAYOUTS.parent / "2023-05-09-human-development-report-interim.PARQUET", "PARQUET", {})
    assert report.place == "row"
    assert "delimiter" not in {s.name for s in report.settings}


def test_a_finding_prints_with_its_code_and_stores_it_apart():
    finding = FindingModel(code="blank-rows", kind="fact", message="Line 5 is blank.", rows=[5])
    assert finding.message == "Line 5 is blank."
    assert str(finding) == "Line 5 is blank. [whyqd:blank-rows]"
