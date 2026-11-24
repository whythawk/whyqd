# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.models import FieldModel
from whyqd.parsers.definition import DefinitionParser

SOURCE_DIRECTORY = Path(__file__).resolve().parent / "data"
SOURCE_SCHEMA_PATH = SOURCE_DIRECTORY / "test_source_schema.schema"
CROSSWALK_PATH = SOURCE_DIRECTORY / "test_crosswalk.crosswalk"
CROSSWALK = DefinitionParser().load(source=CROSSWALK_PATH)
CROSSWALK.pop("version", None)
CROSSWALK["schemaSource"].pop("version", None)
CROSSWALK["schemaDestination"].pop("version", None)
DESTINATION_SCHEMA_PATH = SOURCE_DIRECTORY / "test_schema.schema"
SCHEMA_SOURCE = qd.SchemaDefinition(source=SOURCE_SCHEMA_PATH)
SCHEMA_DESTINATION = qd.SchemaDefinition(source=DESTINATION_SCHEMA_PATH)
SCHEMA_SCRIPTS = [
    "NEW > 'la_code' < ['E06000044']",
    "RENAME > 'ba_ref' < ['Property Reference Number']",
    "RENAME > 'prop_ba_rates' < ['Current Rateable Value']",
    "RENAME > 'occupant_name' < ['Primary Liable party name']",
    "RENAME > 'postcode' < ['Full Property Address']",
    "CATEGORISE > 'occupation_state'::False < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
    "CATEGORISE > 'occupation_state_reliefs'::'small_business' < 'Current Relief Type'::['Small Business Relief England', 'Sbre Extension For 12 Months', 'Supporting Small Business Relief']",
    "CATEGORISE > 'occupation_state_reliefs'::'vacancy' < 'Current Relief Type'::['Empty Property Rate Non-Industrial', 'Empty Property Rate Industrial', 'Empty Property Rate Charitable']",
    "CATEGORISE > 'occupation_state_reliefs'::'retail' < 'Current Relief Type'::['Retail Discount']",
    "CATEGORISE > 'occupation_state_reliefs'::'other' < 'Current Relief Type'::['Sports Club (Registered CASC)', 'Mandatory']",
    "SELECT_NEWEST > 'occupation_state_date' < ['Current Relief Award Start Date' + 'Current Relief Award Start Date', 'Account Start date' + 'Account Start date']",
]
NEW_SCRIPT = "SELECT > 'occupation_state_date' < ['Account Start date', 'Current Relief Award Start Date']"


class TestCrosswalk:
    def test_create_validate(self, tmp_path):
        DIRECTORY = tmp_path
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(
            crosswalk={"name": "test_crosswalk"}, schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION
        )
        crosswalk.actions.add_multi(terms=SCHEMA_SCRIPTS)
        crosswalk.save(directory=DIRECTORY, hide_uuid=True)
        # Validate
        c = crosswalk.exclude_uuid(model=crosswalk.get)
        c.pop("version", None)
        c["schemaSource"].pop("version", None)
        c["schemaDestination"].pop("version", None)
        assert c == CROSSWALK

    def test_exclude_uuid_keeps_a_current_format(self):
        schema = {"formatVersion": "2.0", "name": "s", "fields": [{"name": "t", "type": "time"}]}
        source = qd.SchemaDefinition(source=schema)
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(crosswalk={"name": "c"}, schema_source=source, schema_destination=SCHEMA_DESTINATION)
        assert crosswalk.exclude_uuid(model=crosswalk.get)["schemaSource"]["fields"][0]["type"] == "time"

    def test_add_remove_update(self):
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(
            crosswalk={"name": "test_crosswalk"}, schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION
        )
        # Add
        for script in SCHEMA_SCRIPTS:
            crosswalk.actions.add(term=script)
        # Update
        script = crosswalk.actions.get_all()[-1]
        script.script = NEW_SCRIPT
        crosswalk.actions.update(term=script)
        # Remove
        script = crosswalk.actions.get_all()[0]
        script = crosswalk.actions.remove(name=script.uuid)
        # All there
        cw = {cw.script for cw in crosswalk.actions.get_all()}
        CW = set(SCHEMA_SCRIPTS)
        assert cw - CW == {NEW_SCRIPT}
        assert CW - cw == set([SCHEMA_SCRIPTS[0], SCHEMA_SCRIPTS[-1]])


GOOD = "CATEGORISE > 'group'::'g1' < 'kind'::['t1']"
UNKNOWN = "CATEGORISE > 'group'::'nowhere' < 'kind'::['t2']"


def categories() -> tuple[qd.SchemaDefinition, qd.SchemaDefinition]:
    terms = lambda *names: {"category": [{"name": n} for n in names]}  # noqa: E731
    source = qd.SchemaDefinition(
        source={"name": "source", "fields": [{"name": "kind", "type": "string", "constraints": terms("t1", "t2")}]}
    )
    destination = qd.SchemaDefinition(
        source={
            "name": "destination",
            "fields": [{"name": "group", "type": "string", "constraints": terms("g1", "g2")}],
        }
    )
    return source, destination


class TestUnknownCategory:
    def test_refused_when_written(self):
        source, destination = categories()
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(crosswalk={"name": "c"}, schema_source=source, schema_destination=destination)
        with pytest.raises(ValueError, match=r"`nowhere`.*`g1`, `g2`.*\[whyqd:category-unknown\]"):
            crosswalk.actions.add(term=UNKNOWN)

    def test_diagnose_finds_it_and_proposes_dropping_it(self):
        source, destination = categories()
        stored = {"name": "c", "actions": [{"script": GOOD}, {"script": UNKNOWN}]}
        report = qd.CrosswalkDefinition().diagnose(
            crosswalk=stored, schema_source=source, schema_destination=destination, propose=True
        )
        (finding,) = report.findings
        assert finding.code == "category-unknown" and "`nowhere`" in finding.message
        (proposal,) = report.proposals
        assert (proposal.setting, proposal.value) == ("drop", finding.step)

    def test_diagnose_reports_an_uncoded_refusal_as_its_step(self):
        source, destination = categories()
        stored = {"name": "c", "actions": [{"script": GOOD}, {"script": "RENAME > 'group' < ['nowhere']"}]}
        report = qd.CrosswalkDefinition().diagnose(
            crosswalk=stored, schema_source=source, schema_destination=destination
        )
        assert [(f.code, f.step) for f in report.findings] == [("step-refused", 1)]

    def test_set_drops_the_steps_named(self):
        source, destination = categories()
        stored = {"name": "c", "actions": [{"script": GOOD}, {"script": UNKNOWN}]}
        report = qd.CrosswalkDefinition().diagnose(
            crosswalk=stored, schema_source=source, schema_destination=destination
        )
        crosswalk = qd.CrosswalkDefinition()
        crosswalk.set(
            crosswalk=stored, schema_source=source, schema_destination=destination, drop=[report.findings[0].step]
        )
        assert [step.script for step in crosswalk.actions.get_all()] == [GOOD]


NESTED = "CALCULATE > 'x' < [+ 'a', + [CALCULATE < [+ 'b', + 'c']]]"


def numbers() -> qd.CrosswalkDefinition:
    source = qd.SchemaDefinition(source={"name": "source", "fields": [{"name": n, "type": "number"} for n in "abc"]})
    destination = qd.SchemaDefinition(source={"name": "destination", "fields": [{"name": "x", "type": "number"}]})
    crosswalk = qd.CrosswalkDefinition()
    crosswalk.set(crosswalk={"name": "nested"}, schema_source=source, schema_destination=destination)
    return crosswalk


class TestMapped:
    def test_removing_one_of_two_steps_keeps_the_field_mapped(self):
        crosswalk = numbers()
        crosswalk.actions.add_multi(terms=["RENAME > 'x' < ['a']", "RENAME > 'x' < ['b']"])
        first, second = crosswalk.actions.get_all()
        crosswalk.actions.remove(name=first.uuid)
        assert [field.name for field in crosswalk.actions.validate()] == []
        crosswalk.actions.remove(name=second.uuid)
        assert [field.name for field in crosswalk.actions.validate()] == ["x"]


class TestNestedScripts:
    @pytest.mark.xfail(strict=True, raises=NameError, reason="a nested script is not yet parsed")
    def test_a_nested_script_parses(self):
        parsed = numbers().actions.parse(script=NESTED)
        (nested,) = [term for term in parsed["source"] if isinstance(term, dict)]
        assert [term.name for term in parsed["source"] if isinstance(term, FieldModel)] == ["a"]
        assert nested["action"].name == "CALCULATE"
        assert [term.name for term in nested["source"] if isinstance(term, FieldModel)] == ["b", "c"]

    @pytest.mark.xfail(strict=True, raises=NameError, reason="a nested script is not yet parsed, so not run")
    def test_a_nested_script_runs(self):
        data = pd.DataFrame({"a": ["1"], "b": ["2"], "c": ["3"]})
        assert numbers().actions.transform(df=data, script=NESTED)["x"].tolist() == [6]
