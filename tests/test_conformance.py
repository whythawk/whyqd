# SPDX-License-Identifier: BSD-3-Clause
"""A transform conforms to its destination schema or is not built, and says why.

A refused cell halts only where the crosswalk reads it, in a row that survives; each run finishes reading first, so one
report holds everything found; and a constraint applied is checked. Everywhere before the transform, a problem warns.
"""

import json
from pathlib import Path

import openpyxl
import pytest

import whyqd as qd
from whyqd.models import ActionScriptModel, PolicyModel

DATA = Path(__file__).resolve().parent / "data"


def _derived(datasource):
    schema = qd.SchemaDefinition()
    schema.derive_model(data=datasource.get)
    return schema


def build(tmp_path, rows, source=None, destination=None, scripts=None, missing=None):
    """A transform of a CSV `rows`, each column mapped by name unless `scripts` says otherwise."""
    path = tmp_path / "source.csv"
    path.write_text("\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8")
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(source=path, mimetype="CSV")
    derived = qd.SchemaDefinition()
    derived.derive_model(data=datasource.get)
    written = json.loads(derived.get_json())
    for field in written["fields"]:
        field |= (source or {}).get(field["name"], {})
    if missing:
        written["missingValues"] = missing
    schema_destination = qd.SchemaDefinition()
    schema_destination.set(schema={"name": "destination"})
    fields = destination or {name: {"type": "string"} for name in rows[0]}
    schema_destination.fields.add_multi(terms=[{"name": name, **parts} for name, parts in fields.items()])
    crosswalk = qd.CrosswalkDefinition()
    crosswalk.set(schema_source=qd.SchemaDefinition(source=written), schema_destination=schema_destination)
    named = [name for name in fields if name in rows[0]]
    crosswalk.actions.add_multi(terms=scripts or [f"RENAME > '{name}' < ['{name}']" for name in named])
    return qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get)


def faults(transform) -> list[tuple]:
    return sorted((f.field, f.code, f.count) for f in transform.report.findings if f.kind == "fault")


def warned(transform) -> list[tuple]:
    return sorted((f.field, f.code) for f in transform.report.findings if f.kind == "warning")


class TestHalting:
    def test_a_conforming_file_builds_and_reports_nothing(self, tmp_path):
        run = build(tmp_path, [["a", "b"], ["1", "2024-04-13"]], destination={"a": {"type": "number"}, "b": {"type": "date"}})
        run.process()
        assert run.data["a"].tolist() == [1.0]
        assert str(run.data["b"].tolist()[0]).startswith("2024-04-13")
        assert run.report.findings == []

    def test_a_refusal_at_the_destination_halts_and_builds_nothing(self, tmp_path):
        run = build(tmp_path, [["a"], ["£5"], ["7"]], destination={"a": {"type": "number"}})
        with pytest.raises(ValueError, match=r"\[whyqd:transform-halted\]"):
            run.process()
        assert run.data is None
        assert faults(run) == [("a", "undeclared-character", 1)]

    def test_a_halt_leaves_nothing_to_save(self, tmp_path):
        run = build(tmp_path, [["a"], ["£5"]], destination={"a": {"type": "number"}})
        with pytest.raises(ValueError):
            run.process()
        with pytest.raises(ValueError, match="No destination data"):
            run.save(directory=tmp_path)

    def test_each_run_reports_everything_it_can(self, tmp_path):
        run = build(
            tmp_path,
            [["a", "b"], ["£5", "13/04/2024"], ["x", "2024-04-13"]],
            destination={"a": {"type": "number"}, "b": {"type": "date"}},
        )
        with pytest.raises(ValueError):
            run.process()
        assert {f[0] for f in faults(run)} == {"a", "b"}
        assert sum(f[2] for f in faults(run)) == 3

    def test_a_deleted_row_cannot_halt(self, tmp_path):
        rows = [["a"], ["1"], ["Total"]]
        declared = {"a": {"type": "number"}}
        with pytest.raises(ValueError):
            build(tmp_path, rows, source=declared, destination=declared).process()
        run = build(
            tmp_path, rows, source=declared, destination=declared, scripts=["DELETE_ROWS < [1]", "RENAME > 'a' < ['a']"]
        )
        run.process()
        assert run.data["a"].tolist() == [1.0]

    def test_a_field_no_action_reads_only_warns(self, tmp_path):
        run = build(
            tmp_path,
            [["a", "b"], ["1", "x"]],
            source={"b": {"type": "number"}},
            destination={"a": {"type": "number"}},
        )
        run.process()
        assert faults(run) == []
        assert warned(run) == [("b", "unread-refusal")]

    def test_a_declared_field_is_named_at_its_source(self, tmp_path):
        run = build(
            tmp_path,
            [["a"], ["£5"]],
            source={"a": {"type": "number"}},
            destination={"a": {"type": "number"}},
        )
        with pytest.raises(ValueError):
            run.process()
        assert [f[:2] for f in faults(run)] == [("a", "undeclared-character")]

    def test_a_missing_value_is_not_a_refusal(self, tmp_path):
        run = build(tmp_path, [["a"], ["N/A"], ["5"]], source={"a": {"type": "number"}}, destination={"a": {"type": "number"}}, missing=["N/A"])
        run.process()
        assert run.data["a"].isna().tolist() == [True, False]


class TestTypes:
    def test_a_conflict_is_found_with_no_cell_read(self, tmp_path):
        run = build(
            tmp_path, [["a"], ["2024-04-13"]], source={"a": {"type": "date"}}, destination={"a": {"type": "number"}}
        )
        with pytest.raises(ValueError):
            run.process()
        assert [(f.field, f.code, f.count) for f in run.report.findings] == [("a", "type-conflict", None)]

    def test_a_datetime_mapped_to_a_date_drops_its_time_and_says_so(self, tmp_path):
        run = build(
            tmp_path,
            [["a"], ["2024-04-13 12:45:00"], ["2024-04-14 00:00:00"]],
            source={"a": {"type": "datetime"}},
            destination={"a": {"type": "date"}},
        )
        with pytest.warns(UserWarning, match=r"\[whyqd:transform-warned\]"):
            run.process()
        assert [str(v)[:19] for v in run.data["a"].tolist()] == ["2024-04-13 00:00:00", "2024-04-14 00:00:00"]
        assert warned(run) == [("a", "time-dropped")]

    def test_several_written_dates_become_one_date(self, tmp_path):
        policy = {"format": "dd/mm/yyyy", "rules": {"alternateFormats": ["yyyy-mm-dd", "d mmmm yyyy"], "language": "en"}}
        run = build(
            tmp_path,
            [["a"], ["13/04/2024"], ["2024-04-14"], ["15 April 2024"]],
            source={"a": {"type": "date", "policy": policy}},
            destination={"a": {"type": "date"}},
        )
        run.process()
        assert [str(v)[:10] for v in run.data["a"].tolist()] == ["2024-04-13", "2024-04-14", "2024-04-15"]

    def test_a_workbooks_bare_serial_reads_once_declared(self, tmp_path):
        path = tmp_path / "source.xlsx"
        book = openpyxl.Workbook()
        for row in (["a"], [45295], ["13/04/2024"]):
            book.active.append(row)
        book.save(path)
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=path, mimetype="XLSX")
        derived = json.loads(_derived(datasource).get_json())
        destination = qd.SchemaDefinition()
        destination.set(schema={"name": "destination"})
        destination.fields.add(term={"name": "a", "type": "date"})

        def run(policy):
            derived["fields"][0] |= {"type": "date", "policy": policy}
            crosswalk = qd.CrosswalkDefinition()
            crosswalk.set(schema_source=qd.SchemaDefinition(source=derived), schema_destination=destination)
            crosswalk.actions.add(term="RENAME > 'a' < ['a']")
            return qd.TransformDefinition(crosswalk=crosswalk, data_source=datasource.get)

        halted = run({"format": "dd/mm/yyyy"})
        with pytest.raises(ValueError):
            halted.process()
        named = [str(found) for found in halted.report.findings if found.shape == "99999"]
        assert len(named) == 1 and "`rules.serial`" in named[0]
        built = run({"format": "dd/mm/yyyy", "rules": {"serial": "excel-1900"}})
        built.process()
        assert [str(v)[:10] for v in built.data["a"].tolist()] == ["2024-01-04", "2024-04-13"]

    def test_a_whole_float_becomes_an_integer_and_a_fraction_never_rounds(self, tmp_path):
        run = build(tmp_path, [["a"], ["5.0"], ["6"]], source={"a": {"type": "number"}}, destination={"a": {"type": "integer"}})
        run.process()
        assert run.data["a"].tolist() == [5, 6]

    def test_a_declared_number_writes_as_text(self, tmp_path):
        run = build(tmp_path, [["a"], ["5"]], source={"a": {"type": "number"}}, destination={"a": {"type": "string"}})
        run.process()
        assert run.data["a"].tolist() == ["5.0"]

    def test_text_is_kept_exactly(self, tmp_path):
        run = build(tmp_path, [["a"], ["'  x  y"], ["a\\b"]])
        run.process()
        assert run.data["a"].tolist() == ["'  x  y", "a\\b"]

    def test_whitespace_in_a_text_field_is_kept_and_fails_required(self, tmp_path):
        run = build(tmp_path, [["k", "a"], ["1", "   "]])
        run.process()
        assert run.data["a"].tolist() == ["   "]
        run = build(
            tmp_path,
            [["k", "a"], ["1", "   "]],
            destination={"k": {"type": "string"}, "a": {"type": "string", "constraints": {"required": True}}},
        )
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("a", "constraint-required", 1)]

    def test_a_number_field_becomes_a_whole_number_where_it_is_one(self, tmp_path):
        run = build(tmp_path, [["a"], ["5"], ["5.5"]], source={"a": {"type": "number"}}, destination={"a": {"type": "integer"}})
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("a", "not-an-integer", 1)]

    def test_a_date_reads_as_its_period(self, tmp_path):
        run = build(tmp_path, [["a"], ["2024-04-13"]], source={"a": {"type": "date"}}, destination={"a": {"type": "month"}})
        run.process()
        assert str(run.data["a"].tolist()[0]).startswith("2024-04-30")

    def test_an_exact_destination_keeps_its_digits(self, tmp_path):
        run = build(
            tmp_path,
            [["a"], ["1234.10"], ["0.125"]],
            destination={"a": {"type": "number", "policy": {"base": "decimal"}}},
        )
        run.process()
        assert [str(v) for v in run.data["a"].tolist()] == ["1234.100", "0.125"]


class TestConstraints:
    @pytest.mark.parametrize(
        "constraints, cells, code, count",
        [
            ({"required": True}, ["1", "", "2"], "constraint-required", 1),
            ({"unique": True}, ["1", "1", "2"], "constraint-unique", 2),
            ({"minimum": 2}, ["1", "2", "3"], "constraint-minimum", 1),
            ({"maximum": 2}, ["1", "2", "3"], "constraint-maximum", 1),
        ],
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_a_number_constraint_is_checked(self, tmp_path, constraints, cells, code, count):
        rows = [["key", "a"], *[[str(i), cell] for i, cell in enumerate(cells)]]
        run = build(
            tmp_path, rows, destination={"key": {"type": "string"}, "a": {"type": "number", "constraints": constraints}}
        )
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("a", code, count)]

    @pytest.mark.parametrize(
        "constraints, code", [({"minLength": 2}, "constraint-min-length"), ({"maxLength": 2}, "constraint-max-length")]
    )
    def test_a_string_length_is_checked(self, tmp_path, constraints, code):
        cell = "x" if "minLength" in constraints else "xyz"
        run = build(tmp_path, [["a"], [cell]], destination={"a": {"type": "string", "constraints": constraints}})
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("a", code, 1)]

    def test_a_refused_cell_is_not_counted_again_by_required(self, tmp_path):
        run = build(tmp_path, [["a"], ["x"]], destination={"a": {"type": "number", "constraints": {"required": True}}})
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("a", "undeclared-character", 1)]


class TestWarnings:
    def test_a_read_with_something_to_check_warns_and_builds(self, tmp_path):
        run = build(
            tmp_path,
            [["a"], ["2024-04-13 12:45"]],
            source={"a": {"type": "date"}},
            destination={"a": {"type": "date"}},
        )
        with pytest.warns(UserWarning, match=r"\[whyqd:transform-warned\]"):
            run.process()
        assert warned(run) == [("a", "time-dropped")]

    def test_several_currencies_warn(self, tmp_path):
        policy = {"rules": {"currency": ["£", "€"]}}
        declared = {"a": {"type": "number", "policy": policy}}
        run = build(tmp_path, [["a"], ["£5"], ["€6"]], source=declared, destination={"a": {"type": "number"}})
        with pytest.warns(UserWarning):
            run.process()
        assert warned(run) == [("a", "several-currencies")]

    def test_one_currency_seen_does_not_warn(self, tmp_path):
        declared = {"a": {"type": "number", "policy": {"rules": {"currency": ["£", "€"]}}}}
        run = build(tmp_path, [["a"], ["£5"]], source=declared, destination={"a": {"type": "number"}})
        run.process()
        assert warned(run) == []


class TestActions:
    def test_a_built_date_reads_by_the_actions_policy(self, tmp_path):
        run = build(
            tmp_path,
            [["d", "m", "y"], ["13", "04", "2024"]],
            destination={"when": {"type": "date"}},
            scripts=["UNITE > 'when' < '/'::['d','m','y']"],
        )
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("when", "not-in-format", 1)]
        script = run.crosswalk.crud.get_all()[0]
        script.policy = PolicyModel(format="dd/mm/yyyy")
        run.crosswalk.crud.get_all()[0].policy = script.policy
        run.process()
        assert str(run.data["when"].tolist()[0]).startswith("2024-04-13")

    def test_an_actions_policy_is_checked_against_its_destination(self, tmp_path):
        run = build(
            tmp_path,
            [["d", "m"], ["13", "04"]],
            destination={"when": {"type": "number"}},
            scripts=["UNITE > 'when' < '/'::['d','m']"],
        )
        run.crosswalk.crud.get_all()[0].policy = PolicyModel(format="dd/MM")
        with pytest.raises(ValueError, match=r"\[whyqd:policy-conflict\]"):
            run.process()

    def test_a_destination_cannot_say_how_a_publisher_wrote_it(self, tmp_path):
        run = build(tmp_path, [["a"], ["5"]], destination={"a": {"type": "date", "policy": {"format": "dd/MM/yyyy"}}})
        with pytest.raises(ValueError, match=r"\[whyqd:policy-on-destination\]"):
            run.process()

    def test_calculate_reads_each_input_by_its_declaration(self, tmp_path):
        pounds = {"type": "number", "policy": {"rules": {"currency": ["£"]}}}
        run = build(
            tmp_path,
            [["a", "b"], ["£5", "2"]],
            source={"a": pounds},
            destination={"total": {"type": "number"}},
            scripts=["CALCULATE > 'total' < [+ 'a', - 'b']"],
        )
        run.process()
        assert run.data["total"].tolist() == [3.0]

    def test_calculate_halts_on_an_input_it_cannot_read(self, tmp_path):
        run = build(
            tmp_path,
            [["a", "b"], ["£5", "2"]],
            destination={"total": {"type": "number"}},
            scripts=["CALCULATE > 'total' < [+ 'a', - 'b']"],
        )
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("a", "undeclared-character", 1)]

    def test_select_newest_reads_its_dates_by_their_declaration(self, tmp_path):
        run = build(
            tmp_path,
            [["old", "old_date", "new", "new_date"], ["a", "01/02/2020", "b", "01/02/2024"]],
            source={"old_date": {"type": "date", "policy": {"format": "dd/mm/yyyy"}}, "new_date": {"type": "date", "policy": {"format": "dd/mm/yyyy"}}},
            destination={"latest": {"type": "string"}},
            scripts=["SELECT_NEWEST > 'latest' < ['old' + 'old_date', 'new' + 'new_date']"],
        )
        run.process()
        assert run.data["latest"].tolist() == ["b"]


class TestDiagnose:
    def test_a_schema_is_checked_before_any_crosswalk_exists(self, tmp_path):
        path = tmp_path / "source.csv"
        path.write_text("a,b\n£5,x\n7,y\n", encoding="utf-8")
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=path, mimetype="CSV")
        schema = qd.SchemaDefinition()
        schema.derive_model(data=datasource.get)
        schema.fields.get(name="a").dtype = "number"
        report = qd.DataSourceDefinition().diagnose(source=path, mimetype="CSV", schema=schema)[0]
        assert [(f.field, f.code, f.count) for f in report.findings if f.kind == "fault"] == [
            ("a", "undeclared-character", 1)
        ]

    def test_without_a_schema_nothing_is_typed(self, tmp_path):
        path = tmp_path / "source.csv"
        path.write_text("a\n£5\n", encoding="utf-8")
        report = qd.DataSourceDefinition().diagnose(source=path, mimetype="CSV")[0]
        assert [f for f in report.findings if f.field] == []


class TestUsdate:
    def test_a_1x_usdate_upgrades_to_a_month_first_date(self):
        stored = json.loads((DATA / "test_basildon_source.schema").read_text(encoding="utf-8"))
        stored["fields"][0]["type"] = "usdate"
        field = qd.SchemaDefinition(source=stored).get.fields[0]
        assert field.dtype == "date"
        assert field.policy.format == "MM/dd/yyyy"

    def test_it_saves_back_as_1x_wrote_it(self):
        stored = json.loads((DATA / "test_basildon_source.schema").read_text(encoding="utf-8"))
        stored["fields"][0]["type"] = "usdate"
        written = json.loads(qd.SchemaDefinition(source=stored).get_json(format="1.x"))
        assert written["fields"][0]["type"] == "usdate"
        assert "policy" not in written["fields"][0]

    def test_it_reads_month_first(self, tmp_path):
        run = build(tmp_path, [["a"], ["04/13/2024"], ["04-13-2024"]], source={"a": {"type": "usdate"}}, destination={"a": {"type": "date"}})
        run.process()
        assert [str(v)[:10] for v in run.data["a"].tolist()] == ["2024-04-13", "2024-04-13"]


def test_an_action_script_model_holds_its_policy():
    held = ActionScriptModel(script="NEW > 'a' < ['1']", policy={"format": "dd/MM/yyyy"})
    assert held.policy.format == "dd/MM/yyyy"
