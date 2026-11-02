# SPDX-License-Identifier: BSD-3-Clause
"""A report on how a file was read and what was found there, held to the layout fixtures' answer key.

Each file is read with no setting declared, as a wrangler first loads it. A report interprets nothing: its findings are
what the file holds, and it proposes a setting only for a file that cannot be read as written, and only when asked.
"""

import json
from pathlib import Path

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
UNBUILT = pytest.mark.xfail(strict=True, reason="diagnose is not built")


def diagnose(name: str, mimetype: str, dialect: dict, propose: bool = False) -> ReportModel:
    reports = qd.DataSourceDefinition().diagnose(
        source=LAYOUTS / name, mimetype=mimetype, dialect=dialect or None, propose=propose
    )
    assert len(reports) == 1
    return reports[0]


def found(report: ReportModel) -> dict[str, dict]:
    return {
        f.code: {k: getattr(f, k) for k in ("rows", "columns", "cells", "setting") if getattr(f, k)}
        for f in report.findings
    }


@UNBUILT
@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_each_layout_finds_what_its_key_says(name, mimetype, dialect, case):
    assert found(diagnose(name, mimetype, dialect)) == case["findings"]


@UNBUILT
@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_each_layout_proposes_what_its_key_says(name, mimetype, dialect, case):
    report = diagnose(name, mimetype, dialect, propose=True)
    assert {p.setting: p.value for p in report.proposals} == case["proposals"]
    assert all(p.evidence for p in report.proposals)


@UNBUILT
@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_nothing_is_proposed_unasked(name, mimetype, dialect, case):
    assert diagnose(name, mimetype, dialect).proposals == []


@UNBUILT
@pytest.mark.parametrize("name,mimetype,dialect,case", CASES, ids=IDS)
def test_two_runs_give_the_same_report(name, mimetype, dialect, case):
    assert diagnose(name, mimetype, dialect, propose=True) == diagnose(name, mimetype, dialect, propose=True)


@UNBUILT
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


@UNBUILT
def test_a_declared_setting_is_reported_as_declared():
    report = diagnose("title-above.csv", "CSV", {"skipRows": 3})
    sources = {s.name: s.source for s in report.settings}
    assert sources["skipRows"] == "declared"
    assert sources["delimiter"] == "default"
    assert sources["encoding"] == "file"


@UNBUILT
def test_a_file_that_will_not_read_still_gives_a_report():
    report = diagnose("stray-quote.csv", "CSV", {})
    assert report.findings[0].kind == "fault"
    assert report.findings[0].code == "csv-quote"
    assert report.settings == []


@UNBUILT
def test_each_sheet_of_a_workbook_has_its_own_report():
    reports = qd.DataSourceDefinition().diagnose(source=LAYOUTS / "layouts.xlsx", mimetype="XLSX")
    assert [r.sheet for r in reports] == list(KEY["workbook"]["layouts.xlsx"])


@UNBUILT
def test_the_rows_above_a_header_can_be_seen_in_the_preview():
    report = diagnose("title-above.csv", "CSV", {"skipRows": 3})
    assert report.place == "line"
    assert "Business rates reliefs, April 2026" in report.preview


def test_a_finding_prints_with_its_code_and_stores_it_apart():
    finding = FindingModel(code="blank-rows", kind="fact", message="Line 5 is blank.", rows=[5])
    assert finding.message == "Line 5 is blank."
    assert str(finding) == "Line 5 is blank. [whyqd:blank-rows]"
