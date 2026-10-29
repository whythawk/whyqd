# SPDX-License-Identifier: BSD-3-Clause
"""Column names a script can name: every name the read gives resolves, in any script, to its own field.

The script parser never sees the file. It resolves each quoted term against the schemas, so the read must give names
that are exact (nothing trimmed or joined), unique, and clear of the row key, and the parser must resolve any such name.
"""

import json
from pathlib import Path

import pytest

import whyqd as qd
from whyqd.parsers import DataSourceParser, RowKeyParser

LAYOUTS = Path(__file__).resolve().parent / "data" / "synthetic-layouts"
HOSTILE = json.loads((LAYOUTS / "answer-key.json").read_text(encoding="utf-8"))["csv"]["hostile-headers.csv"]
NAMES = HOSTILE["names"]
# Read as nesting, or split at the comma, by the morph parser, which does not hex a script before splitting it
MORPH_FAULTS = {"Rate [2026]", "Code, Local"}


def crosswalk() -> qd.CrosswalkDefinition:
    source = qd.SchemaDefinition()
    source.set(schema={"name": "hostile"})
    source.fields.add_multi(
        terms=[{"name": n, "type": "string", "constraints": {"category": [{"name": "v00"}]}} for n in NAMES]
    )
    destination = qd.SchemaDefinition()
    destination.set(schema={"name": "destination"})
    destination.fields.add_multi(
        terms=[
            {"name": "target", "type": "string"},
            {"name": "other", "type": "string"},
            {"name": "flag", "type": "boolean"},
        ]
    )
    definition = qd.CrosswalkDefinition()
    definition.set(crosswalk={"name": "hostile"}, schema_source=source, schema_destination=destination)
    return definition


def first_field(source):
    while isinstance(source, list):
        source = next(s for s in source if s)
    return source


def scripts(name: str) -> list[pytest.param]:
    term = f"'{name}'"
    morph = (
        pytest.mark.xfail(strict=True, raises=ValueError, reason="the morph parser splits names")
        if name in MORPH_FAULTS
        else ()
    )
    return [
        pytest.param(name, f"RENAME > 'target' < [{term}]", id=f"rename-{name!r}"),
        pytest.param(name, f"UNITE > 'target' < ', '::[{term}, 'Rate Relief']", marks=morph, id=f"unite-{name!r}"),
        pytest.param(name, f"SEPARATE > ['target', 'other'] < ';;'::[{term}]", marks=morph, id=f"separate-{name!r}"),
        pytest.param(name, f"CATEGORISE > 'flag'::True < {term}::['v00']", id=f"categorise-{name!r}"),
        pytest.param(name, f"PIVOT_CATEGORIES > 'target' < {term}::[0]", id=f"pivot-categories-{name!r}"),
    ]


class TestColumnNames:
    @pytest.mark.parametrize("name, script", [p for n in NAMES for p in scripts(n)])
    def test_every_name_resolves_to_its_field(self, name, script):
        definition = crosswalk()
        parsed = definition.actions.parse(script=script)
        assert first_field(parsed["source"]).uuid == definition.schema_source.fields.get(name=name).uuid

    def test_names_are_unique_and_clear_of_the_row_key(self):
        row_key = RowKeyParser()
        assert len(set(NAMES)) == len(NAMES)
        assert not any(row_key.is_part(n) for n in NAMES)

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="the reader is not built")
    def test_read_gives_every_name_exactly(self):
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=LAYOUTS / "hostile-headers.csv", mimetype="CSV")
        assert datasource.get.dialect is not None
        assert [c.name for c in datasource.get.columns] == NAMES
        df = DataSourceParser().get(source=datasource.get)
        assert [c for c in df.columns if c != RowKeyParser.ROW] == NAMES
        assert df[RowKeyParser.ROW].tolist() == list(range(len(HOSTILE["rows"])))
        assert df[NAMES].values.tolist() == HOSTILE["rows"]
