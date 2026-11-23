# SPDX-License-Identifier: BSD-3-Clause
"""A transform conforms to its destination schema or is not built, and says why.

A refused cell halts only where the crosswalk reads it, in a row that survives; each run finishes reading first, so one
report holds everything found; and a constraint applied is checked. Everywhere before the transform, a problem warns.
"""

import json
from datetime import timedelta
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

import whyqd as qd
from whyqd import ConformanceError
from whyqd.models import ActionScriptModel, FieldModel, PolicyModel
from whyqd.reading.frame import FrameParser

DATA = Path(__file__).resolve().parent / "data"
PRESENCE = json.loads((DATA / "synthetic-typing" / "typing-key.json").read_text(encoding="utf-8"))["categorise"]


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
        run = build(tmp_path, [["a"], ["<5"], ["7"]], destination={"a": {"type": "number"}})
        with pytest.raises(ValueError, match=r"\[whyqd:transform-halted\]"):
            run.process()
        assert run.data is None
        assert faults(run) == [("a", "undeclared-character", 1)]

    def test_a_halt_is_a_conformance_error(self, tmp_path):
        assert issubclass(ConformanceError, ValueError)
        run = build(tmp_path, [["a"], ["<5"]], destination={"a": {"type": "number"}})
        with pytest.raises(ConformanceError):
            run.process()

    def test_strict_halts_on_a_warning(self, tmp_path):
        run = build(tmp_path, [["a"], ["£5"]], destination={"a": {"type": "number"}})
        with pytest.raises(ConformanceError, match=r"\[whyqd:transform-halted\]"):
            run.process(strict=True)
        assert run.data is None
        assert [f[:2] for f in faults(run)] == [("a", "currency-read")]

    def test_a_halt_leaves_nothing_to_save(self, tmp_path):
        run = build(tmp_path, [["a"], ["<5"]], destination={"a": {"type": "number"}})
        with pytest.raises(ValueError):
            run.process()
        with pytest.raises(ValueError, match="No destination data"):
            run.save(directory=tmp_path)

    def test_each_run_reports_everything_it_can(self, tmp_path):
        run = build(
            tmp_path,
            [["a", "b"], ["<5", "01/02/2024"], ["x", "2024-04-13"]],
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
            [["a"], ["<5"]],
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
    def test_a_number_written_as_text_reads_as_a_cell_would(self, tmp_path):
        run = build(
            tmp_path, [["a"], ["1"], ["1.5"], ["1e20"]], source={"a": {"type": "number"}}, destination={"a": {"type": "string"}}
        )
        run.process()
        assert run.data["a"].tolist() == ["1", "1.5", "100000000000000000000"]

    def test_a_built_value_has_one_text_whichever_path_it_takes(self):
        cells, tags = FrameParser().as_cells(
            pd.Series([timedelta(hours=25, minutes=30), pd.Timestamp("2024-04-01 09:30"), pd.Timestamp("2024-04-01"), ""])
        )
        assert cells.to_list() == ["PT25H30M", "2024-04-01T09:30:00", "2024-04-01", ""]
        assert tags.to_list() == ["d", "d", "d", "s"]

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

    def test_a_workbooks_bare_serial_reads_and_warns_until_declared(self, tmp_path):
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

        warned_run = run({"format": "dd/mm/yyyy"})
        with pytest.warns(UserWarning, match=r"\[whyqd:transform-warned\]"):
            warned_run.process()
        assert [str(v)[:10] for v in warned_run.data["a"].tolist()] == ["2024-01-04", "2024-04-13"]
        named = [str(found) for found in warned_run.report.findings if found.code == "serial-read"]
        assert len(named) == 1 and "`rules.serial`" in named[0]
        confirmed = run({"format": "dd/mm/yyyy", "rules": {"serial": "excel-1900"}})
        confirmed.process()
        assert [str(v)[:10] for v in confirmed.data["a"].tolist()] == ["2024-01-04", "2024-04-13"]
        assert warned(confirmed) == []

    def test_a_number_becomes_an_integer_rounding_half_away_from_zero(self, tmp_path):
        run = build(
            tmp_path,
            [["a"], ["5.0"], ["6"], ["5.5"], ["-5.5"], ["2.5"]],
            source={"a": {"type": "number"}},
            destination={"a": {"type": "integer"}},
        )
        with pytest.warns(UserWarning, match=r"\[whyqd:transform-warned\]"):
            run.process()
        assert run.data["a"].tolist() == [5, 6, 6, -6, 3]
        assert warned(run) == [("a", "integer-rounded")]

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
    @pytest.mark.parametrize(
        "cell, code",
        [("£5", "currency-read"), ("(5)", "sign-read"), ("5%", "percent-read"), ("1.234.567", "marks-read"), ("1e3", "exponent-read")],
    )
    def test_a_declared_type_reads_what_has_one_reading_and_warns(self, tmp_path, cell, code):
        run = build(tmp_path, [["a"], [cell]], destination={"a": {"type": "number"}})
        with pytest.warns(UserWarning, match=r"\[whyqd:transform-warned\]"):
            run.process()
        assert warned(run) == [("a", code)]

    def test_declaring_a_reading_confirms_it(self, tmp_path):
        declared = {"a": {"type": "number", "policy": {"rules": {"currency": ["£"]}}}}
        run = build(tmp_path, [["a"], ["£5"]], source=declared, destination={"a": {"type": "number"}})
        run.process()
        assert run.data["a"].tolist() == [5.0]
        assert warned(run) == []

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

    def test_several_undeclared_currencies_warn(self, tmp_path):
        run = build(tmp_path, [["a"], ["£5"], ["$6"]], destination={"a": {"type": "number"}})
        with pytest.warns(UserWarning):
            run.process()
        assert warned(run) == [("a", "currency-read"), ("a", "several-currencies")]

    def test_one_currency_seen_does_not_warn(self, tmp_path):
        declared = {"a": {"type": "number", "policy": {"rules": {"currency": ["£", "€"]}}}}
        run = build(tmp_path, [["a"], ["£5"]], source=declared, destination={"a": {"type": "number"}})
        run.process()
        assert warned(run) == []


class TestActions:
    def test_a_built_date_reads_by_the_actions_policy(self, tmp_path):
        run = build(
            tmp_path,
            [["d", "m", "y"], ["01", "02", "2024"]],
            destination={"when": {"type": "date"}},
            scripts=["UNITE > 'when' < '/'::['d','m','y']"],
        )
        with pytest.raises(ValueError):
            run.process()
        assert faults(run) == [("when", "two-readings", 1)]
        script = run.crosswalk.crud.get_all()[0]
        script.policy = PolicyModel(format="dd/mm/yyyy")
        run.crosswalk.crud.get_all()[0].policy = script.policy
        run.process()
        assert str(run.data["when"].tolist()[0]).startswith("2024-02-01")

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
            [["a", "b"], ["<5", "2"]],
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
        path.write_text("a,b\n<5,x\n7,y\n", encoding="utf-8")
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


class TestPresence:
    """A field's categories derived as booleans, and `CATEGORISE` assigning `True` to a cell holding a value of its type."""

    RELIEF = {"k": {"type": "string"}, "relief": {"type": "string", "constraints": {"category": [{"name": "present"}]}}}
    SCRIPTS = ["RENAME > 'k' < ['k']", "CATEGORISE > 'relief'::'present' < 'a'::[True]"]
    HALTS = [(name, c["text"]) for name, g in PRESENCE["groups"].items() for c in g["cases"] if c["outcome"] == "halts"]

    @staticmethod
    def field(group: dict) -> dict:
        constraints = {"category": [{"name": True}, {"name": False}]}
        return {"type": group["type"], "constraints": constraints | ({"zeroAsTrue": True} if group["zeroAsTrue"] else {})}

    @pytest.mark.parametrize("name", list(PRESENCE["groups"]))
    def test_a_cell_is_present_as_the_key_says(self, tmp_path, name):
        group = PRESENCE["groups"][name]
        cases = [c for c in group["cases"] if c["outcome"] != "halts"]
        rows = [["k", "a"], *[[str(i), c["text"]] for i, c in enumerate(cases)]]
        run = build(tmp_path, rows, source={"a": self.field(group)}, destination=self.RELIEF, scripts=self.SCRIPTS)
        run.process()
        assert run.data["relief"].eq("present").fillna(False).tolist() == [c["outcome"] == "present" for c in cases]

    @pytest.mark.parametrize("name, text", HALTS)
    def test_a_cell_that_cannot_be_its_type_halts(self, tmp_path, name, text):
        group = PRESENCE["groups"][name]
        run = build(tmp_path, [["k", "a"], ["0", text]], source={"a": self.field(group)}, destination=self.RELIEF, scripts=self.SCRIPTS)
        with pytest.raises(ValueError):
            run.process()

    def test_zero_as_true_is_written_by_set_categories(self):
        schema = qd.SchemaDefinition()
        schema.set(schema={"name": "source"})
        schema.fields.add(term={"name": "a", "type": "number"})
        schema.fields.set_categories(name="a", as_bool=True, zero_as_true=True)
        assert schema.fields.get(name="a").constraints.zeroAsTrue is True

    @pytest.mark.parametrize("dtype", ["date", "string", "boolean"])
    def test_zero_as_true_is_refused_on_a_field_with_no_zero(self, dtype):
        with pytest.raises(ValueError):
            FieldModel(name="a", type=dtype, constraints={"zeroAsTrue": True})


class TestBarkingAndDagenham:
    """A fixed-width export split into a workbook: each relief is present where its start date is, and a spacer of
    padding is blank, never present."""

    HERE = DATA / "sample" / "barking-dagenham"
    RELIEFS = {
        "empty_from": "empty",
        "mand_from": "mandatory",
        "disc_from": "discretionary",
        "sbrr_from": "small_business",
        "rtl_from": "retail",
    }

    def transform(self, declared: bool) -> qd.TransformDefinition:
        stored = qd.TransformDefinition(transform=self.HERE / "barking-dagenham.TRANSFORM")
        source = stored.get.dataSource.model_copy(update={"path": str(self.HERE / "source-data.XLSX")})
        crosswalk = stored.get.crosswalk
        for field in crosswalk.schemaSource.fields:
            if field.name.strip() in [*self.RELIEFS, "liable_from"]:
                field.dtype = "date"
                field.policy = PolicyModel(format="dd.MM.yyyy") if declared else None
        return qd.TransformDefinition(crosswalk=crosswalk, data_source=source)

    def cells(self, name: str) -> list[str]:
        """A column's cells as the workbook holds them, read apart from whyqd."""
        rows = list(openpyxl.load_workbook(self.HERE / "source-data.XLSX", read_only=True).active.iter_rows(values_only=True))
        column = [str(h).strip() for h in rows[0]].index(name)
        return ["" if row[column] is None else str(row[column]).strip() for row in rows[1:]]

    def test_a_day_that_could_be_a_month_halts_until_the_order_is_declared(self):
        run = self.transform(declared=False)
        with pytest.raises(ValueError):
            run.process()
        want = {}
        for name in self.RELIEFS:
            for cell in self.cells(name):
                day, month, _ = (cell.split(".") + ["", "", ""])[:3]
                if cell and int(day) <= 12 and day != month:
                    want[name] = want.get(name, 0) + 1
        got = {}
        for found in run.report.findings:
            if found.kind == "fault" and found.code == "two-readings" and found.field.strip() in self.RELIEFS:
                got[found.field.strip()] = got.get(found.field.strip(), 0) + found.count
        assert got == want

    def test_a_relief_is_present_where_its_start_date_is(self):
        run = self.transform(declared=True)
        run.process()
        types = [value or [] for value in run.data["occupierReliefType"].tolist()]
        for name, term in self.RELIEFS.items():
            assert [term in held for held in types] == [bool(cell) for cell in self.cells(name)], name


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
