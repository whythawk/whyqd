# SPDX-License-Identifier: BSD-3-Clause
"""Each cell reads by what its field declares, and a whole conversion ends on the true values.

`synthetic-typing/typing-key.json` states what each cell must read as under a policy. `synthetic-locales/answer-key.json`
states, for one table written as each locale's publisher would, what each round of declarations must do: a cold
transform halts and reports, and the last round holds the true values. Both are written apart from whyqd, by the builders
in `tests/data/builders/`. A reading does not depend on the machine's locale, so each conversion runs under several.

The tests of the reader and of the conversion fail until those are built, each pinned as a strict expected failure.
"""

import json
import math
from decimal import Decimal
from pathlib import Path

import pandas as pd
import polars as pl
import pytest

import whyqd as qd
from tests.test_locale import machine_locale  # noqa: F401
from whyqd import parsers
from whyqd.dtypes import RefusalReason
from whyqd.models import FieldModel, PolicyModel

DATA = Path(__file__).resolve().parent / "data"
TYPING = json.loads((DATA / "synthetic-typing" / "typing-key.json").read_text(encoding="utf-8"))
LOCALES = json.loads((DATA / "synthetic-locales" / "answer-key.json").read_text(encoding="utf-8"))
SOURCES = DATA / "synthetic-locales"
TYPES = ("number", "integer", "boolean", "date", "time", "datetime", "duration", "string")
READ = ("number", "integer", "boolean", "string")
GROUPS = [(dtype, name) for dtype in TYPES for name in TYPING[dtype]]
CASES = [
    (dtype, name, index) for dtype, name in GROUPS for index in range(len(TYPING[dtype][name]["cases"]))
]
DESTINATION = {f["name"]: f["type"] for f in LOCALES["destination"]["fields"]}
NOT_BUILT = (AttributeError, AssertionError, TypeError, ValueError, pytest.fail.Exception)


def case_id(value) -> str:
    return str(value)


class TestKeys:
    """Whatever the keys declare is a declaration whyqd accepts, so the reader's tests can only fail on reading."""

    @pytest.mark.parametrize("dtype, name", GROUPS, ids=case_id)
    def test_a_groups_policy_is_declarable(self, dtype, name):
        group = TYPING[dtype][name]
        FieldModel(name="field", type=group["type"], policy=group["policy"])

    @pytest.mark.parametrize("dtype, name", GROUPS, ids=case_id)
    def test_a_refusal_has_a_known_reason(self, dtype, name):
        for case in TYPING[dtype][name]["cases"]:
            if case["outcome"] == "refuse":
                RefusalReason(case["reason"])

    @pytest.mark.parametrize("name", list(LOCALES["files"]))
    def test_a_files_declarations_are_declarable(self, name):
        for round_ in LOCALES["files"][name]["rounds"]:
            for field, policy in round_["declare"].get("fields", {}).items():
                FieldModel(name=field, type=DESTINATION[field], policy=policy)


def check_reading(dtype: str, name: str, index: int) -> None:
    group = TYPING[dtype][name]
    case = group["cases"][index]
    policy = PolicyModel(**group["policy"]) if group["policy"] else None
    reading = parsers.ReadingParser().read(
        cells=[case["text"]], cell_types=[case.get("cell_type", "s")], dtype=group["type"], policy=policy
    )[0]
    assert reading.kind == {"refuse": "refused"}.get(case["outcome"], case["outcome"]), (case, reading)
    if case["outcome"] == "refuse":
        assert reading.reason == case["reason"], (case, reading)
    if case["outcome"] == "value":
        assert same(group["type"], reading.value, case["value"]), (case, reading)


class TestReader:
    @pytest.mark.parametrize("dtype, name, index", [c for c in CASES if c[0] in READ], ids=case_id)
    def test_a_cell_reads_as_the_key_says(self, dtype, name, index):
        check_reading(dtype, name, index)

    @pytest.mark.xfail(strict=True, raises=AttributeError, reason="dates, times, and durations are not built")
    @pytest.mark.parametrize("dtype, name, index", [c for c in CASES if c[0] not in READ], ids=case_id)
    def test_a_later_type_reads_as_the_key_says(self, dtype, name, index):
        check_reading(dtype, name, index)

    def test_a_column_reads_each_cell_by_the_one_declaration(self):
        policy = PolicyModel(format={"decimalChar": ",", "groupChar": "."}, rules={"currency": ["€"]})
        read = parsers.ReadingParser().read(cells=["1.234,50 €", "1,234.50", "", "٣٤"], dtype="number", policy=policy)
        assert [r.kind for r in read] == ["value", "refused", "blank", "value"]
        assert read[0].value == 1234.5 and read[3].value == 34

    def test_a_decimal_column_takes_its_scale_from_its_cells(self):
        read = parsers.ReadingParser().read(cells=["1.5", "0.125", "2"], dtype="number", policy=PolicyModel(base="decimal"))
        assert [r.value for r in read] == [Decimal("1.5"), Decimal("0.125"), Decimal("2")]

    def test_a_stored_number_is_already_a_value(self):
        policy = PolicyModel(format={"decimalChar": ",", "groupChar": "."})
        read = parsers.ReadingParser().read(
            cells=["1234.5", "2.5e-05", "2024-01-01"], cell_types=["n", "n", "d"], dtype="number", policy=policy
        )
        assert read[0].value == 1234.5 and read[1].value == 2.5e-05
        assert read[2].reason == "not-in-format"

    def test_a_negative_is_never_read_twice_into_a_positive(self):
        read = parsers.ReadingParser().read(cells=["(-5)"], dtype="number", policy=PolicyModel(rules={"negative": ["(x)"]}))
        assert read[0].reason == "undeclared-sign"

    @pytest.mark.parametrize("name", ["count", "^a$", "*", "cell"])
    def test_a_columns_name_never_changes_its_reading(self, name):
        cells = pl.Series(name, ["1", "x"], dtype=pl.String)
        read = parsers.ReadingParser().column(cells=cells, dtype="number")
        assert read["kind"].to_list() == ["value", "refused"]

    def test_a_text_fields_stored_types_are_counted(self):
        types = pl.Series("id", ["s", "d", "n", "d", None], dtype=pl.String)
        assert parsers.ReadingParser().stored_types(types) == {"d": 2, "n": 1}

    def test_more_than_one_currency_is_counted(self):
        reader = parsers.ReadingParser()
        cells = pl.Series("amount", ["£5", "£6", "€7", "¬£8", "9"], dtype=pl.String)
        policy = PolicyModel(rules={"currency": ["£", "€", "¬£"]})
        assert reader.currencies(cells=cells, policy=policy) == {"£": 2, "€": 1, "¬£": 1}
        assert reader.currencies(cells=cells, policy=PolicyModel(rules={"currency": ["£"]})) == {}

    def test_refusals_group_by_shape(self):
        reader = parsers.ReadingParser()
        cells = pl.Series("amount", ["#-1.50", "#-99.99", "5", "N/A"], dtype=pl.String)
        findings = reader.findings(field="amount", cells=cells, readings=reader.column(cells=cells, dtype="number"))
        shapes = {f.shape: (f.code, f.count, f.rows) for f in findings}
        assert shapes["#-9.99"] == ("undeclared-character", 1, [1])
        assert shapes["N/A"] == ("undeclared-character", 1, [4])
        assert all("Next, " in f.message for f in findings)
        assert "1 cell shaped `#-9.99`" in findings[0].message and "(`#`)" in findings[0].message


def same(dtype: str, got, want) -> bool:
    """Whether a value read equals a key's: a number by its exact digits or, read as a float, to the float's precision."""
    if want == "NaN":
        return math.isnan(got)
    if want is None or pd.isna(got):
        return want is None and pd.isna(got)
    if dtype == "boolean":
        return bool(got) == want
    if dtype in ("number", "integer"):
        if isinstance(got, float):
            return math.isclose(got, float(want)) or (math.isnan(got) and want == "NaN")
        return Decimal(str(got)) == Decimal(want)
    return str(got)[: len(want)] == want


def source_schema(datasource: qd.DataSourceDefinition, declare: dict) -> qd.SchemaDefinition:
    derived = qd.SchemaDefinition()
    derived.derive_model(data=datasource.get)
    written = json.loads(derived.get_json())
    for field in written["fields"]:
        if field["name"] in declare.get("fields", {}):
            field |= {"type": DESTINATION[field["name"]], "policy": declare["fields"][field["name"]]}
    written["missingValues"] = declare.get("missingValues", [])
    return qd.SchemaDefinition(source=written)


def transform(name: str, declare: dict) -> qd.TransformDefinition:
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(source=SOURCES / name, mimetype=LOCALES["files"][name]["mime"])
    destination = qd.SchemaDefinition()
    destination.set(schema={"name": "destination"})
    for field in LOCALES["destination"]["fields"]:
        destination.fields.add(term=field)
    crosswalk = qd.CrosswalkDefinition()
    crosswalk.set(
        crosswalk={"name": name}, schema_source=source_schema(datasource, declare), schema_destination=destination
    )
    renames = [f"RENAME > '{field}' < ['{field}']" for field in DESTINATION]
    crosswalk.actions.add_multi(terms=[*declare.get("actions", []), *renames])
    return qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get)


class TestLocaleColumns:
    """Each locale's own file, loaded by whyqd and read by its declarations, before any transform is wired to it."""

    READ_FIELDS = {name: dtype for name, dtype in DESTINATION.items() if dtype in READ}
    CLEAN = [name for name, entry in LOCALES["files"].items() if name == f"{entry['locale']}.csv"]
    MIXED = [name for name in LOCALES["files"] if name.startswith(("mixed", "footer"))]

    @staticmethod
    def columns(name: str) -> dict[str, pl.Series]:
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=SOURCES / name, mimetype=LOCALES["files"][name]["mime"])
        frame = parsers.DataSourceParser().get(source=datasource.get)
        return {f: pl.Series(f, [None if pd.isna(v) else v for v in frame[f]], dtype=pl.String) for f in DESTINATION}

    @pytest.mark.parametrize("name", CLEAN)
    def test_a_clean_file_reads_as_the_true_values(self, name, machine_locale):  # noqa: F811
        entry = LOCALES["files"][name]
        columns = self.columns(name)
        declared = entry["rounds"][-1]["declare"]["fields"]
        for field, dtype in self.READ_FIELDS.items():
            policy = PolicyModel(**declared[field]) if field in declared else None
            read = parsers.ReadingParser().column(cells=columns[field], dtype=dtype, policy=policy)
            assert read["reason"].drop_nulls().to_list() == [], (field, read)
            for got, want in zip(read["value"].to_list(), entry["values"]):
                assert same(dtype, got, want[field]), (field, got, want[field])

    @pytest.mark.parametrize("name", MIXED)
    def test_a_declaration_leaves_only_the_damage(self, name):
        entry = LOCALES["files"][name]
        columns = self.columns(name)
        round_ = entry["rounds"][1]
        for field, dtype in self.READ_FIELDS.items():
            policy = round_["declare"]["fields"].get(field)
            read = parsers.ReadingParser().column(
                cells=columns[field], dtype=dtype, policy=PolicyModel(**policy) if policy else None
            )
            assert read["reason"].drop_nulls().len() == round_["halts"].get(field, 0), (field, read)


class TestConversion:
    @pytest.mark.xfail(strict=True, raises=NOT_BUILT, reason="typing and conformance are not built")
    @pytest.mark.parametrize("name", list(LOCALES["files"]))
    def test_a_file_converts_round_by_round(self, name, machine_locale):  # noqa: F811
        entry = LOCALES["files"][name]
        for round_ in entry["rounds"]:
            run = transform(name, round_["declare"])
            if round_["halts"]:
                with pytest.raises(ValueError):
                    run.process()
                counts = {f.field: f.count for f in run.report.findings if f.kind == "fault" and f.field}
                assert counts == round_["halts"]
                continue
            run.process()
            if "differs" in round_:
                continue
        rows = run.data.astype(object).where(run.data.notna(), None).to_dict("records")
        assert len(rows) == len(entry["values"])
        for got, want in zip(rows, entry["values"]):
            for field, dtype in DESTINATION.items():
                assert same(dtype, got[field], want[field]), (field, got[field], want[field])
