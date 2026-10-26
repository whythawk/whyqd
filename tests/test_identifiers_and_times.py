# SPDX-License-Identifier: BSD-3-Clause
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest

import whyqd as qd
from whyqd.models import CategoryModel, VersionModel
from whyqd.models.identifier import IdentifierParser
from whyqd.parsers import CoreParser

DIRECTORY = Path(__file__).resolve().parent / "data"
SCHEMA = DIRECTORY / "test_schema.schema"


class TestIdentifiers:
    def test_layout(self):
        identifiers = [IdentifierParser().new() for _ in range(10_000)]
        assert {i.version for i in identifiers} == {7}
        assert {i.variant for i in identifiers} == {"specified in RFC 4122"}
        assert len(set(identifiers)) == len(identifiers)

    def test_opens_with_the_time(self):
        before = time.time_ns() // 1_000_000
        identifier = IdentifierParser().new()
        after = time.time_ns() // 1_000_000
        assert before <= identifier.int >> 80 <= after

    def test_sorts_by_time(self):
        first = IdentifierParser().new()
        time.sleep(0.002)
        second = IdentifierParser().new()
        assert first < second
        assert str(first) < str(second)

    def test_new_model_gets_one(self):
        assert CategoryModel(name="term").uuid.version == 7

    def test_stored_identifier_kept(self):
        stored = "3f2b6a9e-1d2c-4b8a-9e7f-0a1b2c3d4e5f"
        assert CategoryModel(uuid=stored, name="term").uuid == UUID(stored)

    def test_derived_definition_gets_them(self):
        schema = qd.SchemaDefinition()
        schema.set(schema={"name": "made", "fields": [{"name": "a", "type": "string"}]})
        assert schema.get.uuid.version == 7
        assert schema.get.fields[0].uuid.version == 7


class TestTimes:
    def test_new_time_is_utc(self):
        updated = VersionModel().updated
        assert updated.tzinfo is timezone.utc
        assert abs(datetime.now(timezone.utc) - updated) < timedelta(seconds=5)

    def test_naive_reads_as_utc(self):
        updated = VersionModel(updated="2023-12-12T11:05:46.819971").updated
        assert updated == datetime(2023, 12, 12, 11, 5, 46, 819971, tzinfo=timezone.utc)

    def test_zoned_converts_to_utc(self):
        updated = VersionModel(updated="2026-01-01T12:00:00+02:00").updated
        assert updated == datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
        assert updated.tzinfo is timezone.utc

    def test_writes_with_z(self):
        assert VersionModel(updated="2023-12-12T11:05:46.819971").model_dump(mode="json")["updated"] == (
            "2023-12-12T11:05:46.819971Z"
        )

    def test_formats_write_their_own(self):
        original = json.loads(SCHEMA.read_text(encoding="utf-8"))
        schema = qd.SchemaDefinition(source=SCHEMA)
        current = json.loads(schema.get_json())
        written = json.loads(schema.get_json(format="1.x"))
        assert [v["updated"] for v in current["version"]] == [f"{v['updated']}Z" for v in original["version"]]
        assert [v["updated"] for v in written["version"]] == [v["updated"] for v in original["version"]]

    @pytest.mark.parametrize("zone", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
    def test_output_date_is_utc(self, zone, monkeypatch):
        monkeypatch.setenv("TZ", zone)
        time.tzset()
        try:
            assert CoreParser().get_now() == datetime.now(timezone.utc).date().isoformat()
        finally:
            monkeypatch.undo()
            time.tzset()
