# SPDX-License-Identifier: BSD-3-Clause
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import whyqd as qd

DIRECTORY = Path(__file__).resolve().parent / "data"
DATA_SOURCE = DIRECTORY / "test_basildon_source.data"
SCHEMA = DIRECTORY / "test_schema.schema"

DIALECT = {
    "encoding": "windows-1252",
    "encodingStep": "declared",
    "delimiter": ";",
    "quoteChar": None,
    "doubleQuote": False,
    "skipRows": 2,
    "headerRowCount": 0,
    "skipBlankRows": True,
    "trim": "start",
    "rowsPerRecord": [47, 1],
    "sheet": "Rates",
}
PROFILE = {
    "cellTypes": {"s": 98, "n": 2},
    "blank": 3,
    "whitespace": 1,
    "hardSpace": 4,
    "zeroWidth": 1,
    "control": 1,
    "dateLike": 5,
    "zeroPadded": 6,
}
POLICIES = [
    {"base": "decimal", "format": {"decimalChar": ",", "groupChar": ".", "pattern": "#.##0,00"}},
    {"base": "date", "format": "dd.MM.yyyy", "rules": {"negative": "#-"}},
    {"base": "boolean", "format": "Y|N"},
]


def data_source(**parts) -> dict:
    """The stored data source, upgraded to 2.0 as a dict, with `parts` added to it and to its first column."""
    model = json.loads(qd.DataSourceDefinition(source=DATA_SOURCE).get_json())
    if "profile" in parts:
        model["columns"][0]["profile"] = parts.pop("profile")
    return model | parts


def schema(policy: dict) -> dict:
    model = json.loads(qd.SchemaDefinition(source=SCHEMA).get_json())
    model["fields"][0]["policy"] = policy
    return model


def round_trip(kind, model: dict) -> dict:
    return json.loads(kind(**{"source": model}).get_json())


class TestDataSourceSlots:
    def test_dialect_round_trips(self):
        model = data_source(dialect=DIALECT)
        assert round_trip(qd.DataSourceDefinition, model)["dialect"] == DIALECT

    def test_dialect_defaults_left_out(self):
        model = data_source(dialect={"encoding": "utf-8", "trim": False, "headerRowCount": 1})
        assert round_trip(qd.DataSourceDefinition, model)["dialect"] == {}

    def test_profile_round_trips(self):
        model = data_source(profile=PROFILE)
        assert round_trip(qd.DataSourceDefinition, model)["columns"][0]["profile"] == PROFILE

    def test_absent_by_default(self):
        written = round_trip(qd.DataSourceDefinition, data_source())
        assert "dialect" not in written
        assert all("profile" not in c for c in written["columns"])

    @pytest.mark.parametrize("parts", [{"dialect": DIALECT}, {"profile": PROFILE}], ids=["dialect", "profile"])
    def test_1x_save_refused(self, parts):
        definition = qd.DataSourceDefinition(source=data_source(**parts))
        with pytest.raises(ValueError, match=rf"`{next(iter(parts))}`.*1\.x cannot hold it"):
            definition.get_json(format="1.x")

    @pytest.mark.parametrize("dialect", [{"encodingStep": "guessed"}, {"skipRows": -1}, {"trim": "middle"}], ids=str)
    def test_dialect_refuses_what_it_does_not_know(self, dialect):
        with pytest.raises(ValueError):
            qd.DataSourceDefinition(source=data_source(dialect=dialect))


class TestFieldPolicy:
    @pytest.mark.parametrize("policy", POLICIES, ids=lambda p: p["base"])
    def test_round_trips(self, policy):
        assert round_trip(qd.SchemaDefinition, schema(policy))["fields"][0]["policy"] == policy

    def test_1x_save_refused(self):
        definition = qd.SchemaDefinition(source=schema(POLICIES[0]))
        with pytest.raises(ValueError, match=r"`policy`.*1\.x cannot hold it"):
            definition.get_json(format="1.x")


CROSSWALK = DIRECTORY / "test_crosswalk.crosswalk"
REFERENCE = {"source": "https://example.org/reliefs", "version": "2026-04"}
REASON = {
    "justification": "semapv:MappingReview",
    "comment": "Codes per the 2026 relief schedule",
    "author": ["orcid:0000-0002-1825-0097"],
    "date": "2026-10-26",
    "confidence": 0.9,
    "seeAlso": ["https://example.org/schedule"],
    "reference": REFERENCE,
}
CATEGORISE = 5
RENAME = 1


def crosswalk(**parts) -> dict:
    """The stored crosswalk, upgraded to 2.0 as a dict, with `parts` set on its steps by index."""
    model = json.loads(qd.CrosswalkDefinition(crosswalk=CROSSWALK).get_json())
    for index, part in parts.get("steps", {}).items():
        model["actions"][index] |= part
    if "termList" in parts:
        model["schemaDestination"]["fields"][5]["termList"] = parts["termList"]
    if "code" in parts:
        model["schemaDestination"]["fields"][5]["constraints"]["enum"][0]["code"] = parts["code"]
    return model


def round_trip_crosswalk(model: dict) -> dict:
    return json.loads(qd.CrosswalkDefinition(crosswalk=model).get_json())


class TestReasonsAndReferences:
    def test_reason_round_trips(self):
        written = round_trip_crosswalk(crosswalk(steps={RENAME: {"reason": REASON}}))
        assert written["actions"][RENAME]["reason"] == REASON

    def test_reason_justified_by_hand_by_default(self):
        written = round_trip_crosswalk(crosswalk(steps={RENAME: {"reason": {"comment": "Same column"}}}))
        assert qd.CrosswalkDefinition(crosswalk=written).get.actions[RENAME].reason.justification == (
            "semapv:ManualMappingCuration"
        )

    def test_confidence_bounded(self):
        with pytest.raises(ValueError):
            qd.CrosswalkDefinition(crosswalk=crosswalk(steps={RENAME: {"reason": {"confidence": 1.5}}}))

    def test_correspondence_round_trips(self):
        written = round_trip_crosswalk(crosswalk(steps={CATEGORISE: {"correspondence": REFERENCE}}))
        assert written["actions"][CATEGORISE]["correspondence"] == REFERENCE

    def test_correspondence_only_categorises(self):
        with pytest.raises(ValueError, match="Only a `CATEGORISE` step"):
            qd.CrosswalkDefinition(crosswalk=crosswalk(steps={RENAME: {"correspondence": REFERENCE}}))

    def test_reference_needs_its_version(self):
        with pytest.raises(ValueError):
            qd.CrosswalkDefinition(crosswalk=crosswalk(termList={"source": REFERENCE["source"]}))

    def test_term_list_and_code_round_trip(self):
        written = round_trip_crosswalk(crosswalk(termList=REFERENCE, code="EPR"))
        field = written["schemaDestination"]["fields"][5]
        assert field["termList"] == REFERENCE
        assert field["constraints"]["enum"][0]["code"] == "EPR"

    @pytest.mark.parametrize(
        "parts, key",
        [
            ({"steps": {RENAME: {"reason": REASON}}}, "reason"),
            ({"steps": {CATEGORISE: {"correspondence": REFERENCE}}}, "correspondence"),
            ({"termList": REFERENCE}, "termList"),
            ({"code": "EPR"}, "code"),
        ],
        ids=lambda p: p if isinstance(p, str) else "",
    )
    def test_1x_save_refused(self, parts, key):
        definition = qd.CrosswalkDefinition(crosswalk=crosswalk(**parts))
        with pytest.raises(ValueError, match=rf"`{key}`.*1\.x cannot hold it"):
            definition.get_json(format="1.x")


class TestRelease:
    def test_round_trips(self):
        model = crosswalk()
        model["schemaDestination"]["release"] = "2026 relief categories"
        assert round_trip_crosswalk(model)["schemaDestination"]["release"] == "2026 relief categories"

    def test_not_in_the_content_checksum(self):
        # The stored crosswalk hides its UUIDs, so each load mints new ones: label a copy of one load
        model = crosswalk()
        labelled = json.loads(json.dumps(model))
        labelled["schemaDestination"]["release"] = "2026 relief categories"
        checksums = [round_trip_crosswalk(m)["schemaDestination"]["checksums"] for m in (model, labelled)]
        assert checksums[0] == checksums[1]

    def test_1x_save_refused(self):
        model = crosswalk()
        model["schemaDestination"]["release"] = "2026 relief categories"
        with pytest.raises(ValueError, match=r"`release`.*1\.x cannot hold it"):
            qd.CrosswalkDefinition(crosswalk=model).get_json(format="1.x")


@pytest.fixture(scope="module")
def transform() -> qd.TransformDefinition:
    before = datetime.now(timezone.utc)
    definition = qd.TransformDefinition(crosswalk=CROSSWALK, data_source=DIRECTORY / "raw_E06000044_014_0.data")
    definition.process()
    definition.before = before
    return definition


class TestTransformRecord:
    def test_run_recorded(self, transform):
        model = transform.get
        assert transform.before <= model.started <= model.ended <= datetime.now(timezone.utc)
        assert model.whyqd == qd.__version__

    def test_written_in_utc(self, transform):
        written = json.loads(transform.get_json())
        assert written["started"].endswith("Z") and written["ended"].endswith("Z")
        assert written["whyqd"] == qd.__version__

    def test_unrun_has_none(self):
        written = json.loads(qd.TransformDefinition(crosswalk=CROSSWALK).get_json())
        assert not {"started", "ended", "whyqd", "references"} & written.keys()

    def test_references_round_trip(self, transform):
        used = REFERENCE | {"checksums": [{"algorithm": "BLAKE2b-512", "checksumValue": "ab12", "content": "bytes"}]}
        written = json.loads(transform.get_json()) | {"references": [used]}
        assert json.loads(qd.TransformDefinition(transform=written).get_json())["references"] == [used]

    def test_1x_save_refused(self, transform):
        with pytest.raises(ValueError, match=r"`started`.*1\.x cannot hold it"):
            transform.get_json(format="1.x")
