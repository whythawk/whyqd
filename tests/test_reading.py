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


class TestReader:
    @pytest.mark.xfail(strict=True, raises=AttributeError, reason="the reader is not built")
    @pytest.mark.parametrize("dtype, name, index", CASES, ids=case_id)
    def test_a_cell_reads_as_the_key_says(self, dtype, name, index):
        group = TYPING[dtype][name]
        case = group["cases"][index]
        policy = PolicyModel(**group["policy"]) if group["policy"] else None
        reading = parsers.ReadingParser().read(
            cells=[case["text"]], cell_types=[case.get("cell_type", "s")], dtype=group["type"], policy=policy
        )[0]
        assert reading.kind == {"refuse": "refused"}.get(case["outcome"], case["outcome"]), case
        if case["outcome"] == "refuse":
            assert reading.reason == case["reason"], case
        if case["outcome"] == "value":
            assert same(group["type"], reading.value, case["value"]), case


def same(dtype: str, got, want) -> bool:
    """Whether a value read equals a key's: a number by its exact digits or, read as a float, to the float's precision."""
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
