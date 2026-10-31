# SPDX-License-Identifier: BSD-3-Clause
"""A row count belongs to one file, so a reused schema carries none.

Under format 2.0 a schema has no row count, and a row-level action's rows are checked against the data source's `index`
where the crosswalk meets its file: a schema derived from one file runs on a longer or a shorter one, and only a row
past the end of the file being read is refused.
"""

from pathlib import Path

import pytest

import whyqd as qd


def write(tmp_path: Path, name: str, count: int) -> qd.DataSourceDefinition:
    source = tmp_path / name
    source.write_text("a\n" + "".join(f"r{i}\n" for i in range(count)), encoding="utf-8")
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(source=source, mimetype="CSV")
    return datasource


def crosswalk(datasource: qd.DataSourceDefinition, rows: list[int]) -> qd.CrosswalkDefinition:
    source = qd.SchemaDefinition()
    source.derive_model(data=datasource.get)
    destination = qd.SchemaDefinition()
    destination.set(schema={"name": "destination"})
    destination.fields.add(term={"name": "x", "type": "string"})
    definition = qd.CrosswalkDefinition()
    definition.set(crosswalk={"name": "reused"}, schema_source=source, schema_destination=destination)
    definition.actions.add_multi(terms=[f"DELETE_ROWS < {rows}", "RENAME > 'x' < ['a']"])
    return definition


def run(definition: qd.CrosswalkDefinition, datasource: qd.DataSourceDefinition) -> list[str]:
    transform = qd.TransformDefinition(crosswalk=definition, data_source=datasource.get)
    transform.process()
    return transform.data["x"].tolist()


class TestRowCounts:
    def test_a_derived_schema_has_no_row_count(self, tmp_path):
        schema = qd.SchemaDefinition()
        schema.derive_model(data=write(tmp_path, "short.csv", 3).get)
        assert schema.get.index is None

    def test_a_row_past_the_schemas_file_runs_on_a_longer_one(self, tmp_path):
        # The schema came from 3 rows; the file read has 5, so row 4 is in it
        definition = crosswalk(write(tmp_path, "short.csv", 3), [4])
        assert run(definition, write(tmp_path, "long.csv", 5)) == ["r0", "r1", "r2", "r3"]

    def test_a_row_past_the_file_read_is_refused_naming_it(self, tmp_path):
        # The schema came from 5 rows, so row 3 passes its check; the file read has 3
        definition = crosswalk(write(tmp_path, "long.csv", 5), [3])
        with pytest.raises(ValueError, match=r"\b3\b"):
            run(definition, write(tmp_path, "short.csv", 3))

    def test_a_row_in_both_files_runs_on_either(self, tmp_path):
        definition = crosswalk(write(tmp_path, "long.csv", 5), [1])
        assert run(definition, write(tmp_path, "short.csv", 3)) == ["r0", "r2"]
