# SPDX-License-Identifier: BSD-3-Clause
"""What whyqd proposes a wrangler declare for a typed column, and that proposing changes nothing.

A proposal is a whole policy that whyqd has already read the column under: proposed where one reading reads every cell,
shown and not proposed where several do or none does.
"""

import json
from pathlib import Path

import polars as pl
import pytest

from tests import test_reading
from whyqd.dtypes import FindingKind
from whyqd.models import FindingModel, PolicyModel, ProposalModel, ReportModel
from whyqd.reading.proposal import ProposalParser
from whyqd.reading.reading import ReadingParser

LOCALES = Path(__file__).resolve().parent / "data" / "synthetic-locales"
KEY = json.loads((LOCALES / "answer-key.json").read_text(encoding="utf-8"))
CSV = [name for name in KEY["files"] if name.endswith(".csv")]


def propose(cells: list, dtype: str = "date", types: list | None = None) -> ProposalModel | FindingModel | None:
    column = pl.Series("cell", cells, dtype=pl.String)
    stored = None if types is None else pl.Series("cell", types, dtype=pl.String)
    return ProposalParser().propose(field="start", cells=column, types=stored, dtype=dtype)


def read(cells: list, policy: PolicyModel, dtype: str = "date", types: list | None = None) -> list:
    stored = None if types is None else pl.Series("cell", types, dtype=pl.String)
    readings = ReadingParser().column(
        cells=pl.Series("cell", cells, dtype=pl.String), dtype=dtype, policy=policy, types=stored
    )
    return [None if value is None else str(value) for value in readings["value"].to_list()]


NUMBERS = ("amount", "balance", "rate", "count")
# Locales whose marks are `.` and `,` and whose currency is a symbol, so every number column reads by one declaration
PLAIN = ("en_GB.csv", "en_US.csv", "ja_JP.csv")


def column(name: str, field: str) -> tuple[list, list]:
    text, types = test_reading.TestLocaleColumns.columns(LOCALES / name, "CSV")
    return text[field].to_list(), types[field].to_list()


class TestForm:
    def test_a_field_s_policy_is_proposed_whole(self):
        policy = PolicyModel(format="dd/MM/yyyy", rules={"serial": "excel-1900"})
        proposal = ProposalModel(setting="policy", field="start", value=policy, evidence="Read every cell.")
        assert isinstance(proposal.value, PolicyModel)
        assert proposal.value == policy

    def test_a_policy_proposal_round_trips_through_the_report(self):
        policy = PolicyModel(format={"decimalChar": ",", "groupChar": "."}, rules={"currency": ["€"]})
        report = ReportModel(
            path="data.csv",
            mime="text/csv",
            proposals=[ProposalModel(setting="policy", field="amount", value=policy, evidence="Read every cell.")],
        )
        again = ReportModel.model_validate_json(report.model_dump_json())
        assert again.proposals[0].value == policy

    def test_a_dialect_setting_is_proposed_as_before(self):
        proposal = ProposalModel(setting="delimiter", value=";", evidence="Every line splits alike.")
        assert proposal.value == ";"


class TestDates:
    @staticmethod
    def expected(name: str) -> str:
        """What a locale file's `start` should give, from its key alone: a two-digit year's century is the wrangler's to
        declare, so ambiguous; ISO reads as it is, so nothing; a footer holds text no date reads, so mixed."""
        declared = KEY["files"][name]["rounds"][-1]["declare"]["fields"].get("start", {})
        if name.startswith("footer"):
            return "mixed"
        if "yearStart" in declared.get("rules", {}):
            return "ambiguous"
        if KEY["files"][name]["rounds"][0]["halts"].get("start") is None:
            return "nothing"
        return "proposed"

    @pytest.mark.parametrize("name", CSV)
    def test_each_locale_s_dates_as_its_key_says(self, name):
        text, types = test_reading.TestLocaleColumns.columns(LOCALES / name, "CSV")
        cells = text["start"].to_list()
        found = propose(cells, types=types["start"].to_list())
        expected = self.expected(name)
        if expected == "nothing":
            assert found is None
        elif expected == "proposed":
            assert isinstance(found, ProposalModel) and found.field == "start"
            want = [value["start"] for value in KEY["files"][name]["values"]]
            assert read(cells, found.value, types=types["start"].to_list()) == want
        else:
            assert isinstance(found, FindingModel) and found.kind == FindingKind.FACT
            assert found.code == f"policy-{expected}"

    def test_every_cell_read_two_ways_is_shown_not_proposed(self):
        found = propose(["01/02/2024", "03/04/2024", "05/06/2024"])
        assert isinstance(found, FindingModel) and found.code == "policy-ambiguous"
        assert "dd/MM/yyyy" in found.message and "MM/dd/yyyy" in found.message

    def test_cells_that_can_tell_settle_a_column_none_votes_for(self):
        cells = ["31.12.2024", "04.01.1997", "13.04.2024"]
        found = propose(cells)
        assert isinstance(found, ProposalModel) and found.value.format == "dd.MM.yyyy"
        assert read(cells, found.value) == ["2024-12-31", "1997-01-04", "2024-04-13"]

    def test_one_stored_serial_among_dates_is_proposed_its_rule(self):
        cells, types = ["2024-04-01", "2024-05-02", "45295"], ["d", "d", "n"]
        found = propose(cells, types=types)
        assert isinstance(found, ProposalModel)
        assert found.value.format is None and found.value.rules.serial == "excel-1900"

    def test_a_column_that_reads_silently_needs_nothing(self):
        assert propose(["2024-04-13", "1997-01-04", None]) is None

    def test_month_names_are_shown_with_the_languages_that_read_them(self):
        cells = ["31 Dec 2024", "4 Jan 1997", "13 Apr 2024"]
        found = propose(cells)
        assert isinstance(found, FindingModel) and found.code == "policy-language"
        assert "`en`" in found.message and "d MMM yyyy" in found.message
        english = PolicyModel(format="d MMM yyyy", rules={"language": "en"})
        assert read(cells, english) == ["2024-12-31", "1997-01-04", "2024-04-13"]

    def test_proposing_leaves_the_cells_as_they_were(self):
        cells = pl.Series("cell", ["31.12.2024", "04.01.1997"], dtype=pl.String)
        before = cells.clone()
        ProposalParser().propose(field="start", cells=cells, types=None, dtype="date")
        assert cells.equals(before)


class TestNumbers:
    @pytest.mark.parametrize("field", NUMBERS)
    @pytest.mark.parametrize("name", CSV)
    def test_every_proposal_reads_as_the_key(self, name, field):
        cells, types = column(name, field)
        found = propose(cells, dtype="number", types=types)
        if isinstance(found, ProposalModel):
            readings = ReadingParser().column(
                cells=pl.Series("cell", cells, dtype=pl.String),
                dtype="number",
                policy=found.value,
                types=pl.Series("cell", types, dtype=pl.String),
            )
            want = [value[field] for value in KEY["files"][name]["values"]]
            got = readings["value"].to_list()[: len(want)]
            assert all(test_reading.same("number", g, w) for g, w in zip(got, want, strict=True)), (found.value, got)

    @pytest.mark.parametrize("field", NUMBERS)
    @pytest.mark.parametrize("name", PLAIN)
    def test_a_plain_locale_s_numbers_are_proposed(self, name, field):
        cells, types = column(name, field)
        assert isinstance(propose(cells, dtype="number", types=types), ProposalModel)

    def test_a_lone_group_of_three_is_shown_not_proposed(self):
        found = propose(["1,234"], dtype="number")
        assert isinstance(found, FindingModel) and found.code == "policy-ambiguous"

    def test_a_word_beside_a_number_is_shown_not_proposed(self):
        found = propose(["1 234,50 kr", "15,00 kr", "0,00 kr"], dtype="number")
        assert isinstance(found, FindingModel) and found.code == "policy-ambiguous"

    def test_a_marker_among_numbers_is_mixed(self):
        found = propose(["N/A", "£1,234.50", "£0.00"], dtype="number")
        assert isinstance(found, FindingModel) and found.code == "policy-mixed"


class TestBooleans:
    def test_a_word_pair_is_shown_not_proposed(self):
        found = propose(["Y", "N", "Y", None], dtype="boolean")
        assert isinstance(found, FindingModel) and found.code == "policy-ambiguous"

    def test_a_pair_the_reader_knows_needs_nothing(self):
        assert propose(["true", "false", "1", "0"], dtype="boolean") is None
