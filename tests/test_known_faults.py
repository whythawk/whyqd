# SPDX-License-Identifier: BSD-3-Clause
"""Faults whyqd is known to have, each pinned as a strict expected failure.

Each test states the behaviour whyqd should have and fails today, for the reason given in `raises`. The change that
fixes a fault makes its test pass, which a strict mark reports as a failure until the mark is removed; a test failing
for any other reason is reported too.
"""

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from whyqd.crosswalk.actions.categorise import Action as Categorise
from whyqd.crosswalk.actions.pivot_categories import Action as PivotCategories
from whyqd.crosswalk.actions.pivot_longer import Action as PivotLonger
from whyqd.crosswalk.actions.separate import Action as Separate
from whyqd.models import CategoryModel, FieldModel
from whyqd.parsers import DataSourceParser

DATA = Path(__file__).resolve().parent / "data"
TYPING = json.loads((DATA / "synthetic-typing" / "typing-key.json").read_text(encoding="utf-8"))


def values(kind: str, policy: str) -> list[dict]:
    return [c for c in TYPING[kind][policy]["cases"] if c["outcome"] == "value"]


class TestKnownFaults:
    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="a whitespace-only cell counts as a value")
    def test_categorise_ignores_blank_cells(self):
        cases = TYPING["categorise"]["cases"]
        df = pd.DataFrame({"code": [c["text"] for c in cases]})
        df = Categorise().transform(
            df=df,
            destination=FieldModel(name="flag", type="string"),
            source=FieldModel(name="code", type="string"),
            category=CategoryModel(name="yes"),
            assigned=[CategoryModel(name=True)],
        )
        assert [v == "yes" for v in df["flag"]] == [c["is_value"] for c in cases]

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="signs lost, letters ignored, separators guessed")
    def test_numbers_read_as_published(self):
        reader = DataSourceParser()
        for case in values("number", "UK"):
            assert math.isclose(reader.parse_float(case["text"]), float(case["value"])), case["text"]

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="year-first read year-day-month; per-cell fallback")
    def test_dates_read_by_one_order(self):
        reader = DataSourceParser()
        for case in values("date", "day_first"):
            assert reader.parse_dates(case["text"]) == case["value"], case["text"]
        for case in values("date", "month_first"):
            assert reader.parse_usdates(case["text"]) == case["value"], case["text"]
        assert pd.isna(reader.parse_usdates("13/04/2024"))

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="coercion to a string cleans the text")
    def test_strings_keep_their_text(self):
        reader = DataSourceParser()
        for case in values("string", "default"):
            assert reader.parse_string(case["text"]) == case["value"], repr(case["text"])

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="kept columns are ordered by a set")
    def test_pivot_longer_keeps_columns_in_source_order(self):
        kept = [f"k{i}" for i in range(8)]
        df = pd.DataFrame({**{k: ["x"] for k in kept}, "a": ["1"], "b": ["2"]})
        destination = [FieldModel(name="name", type="string"), FieldModel(name="value", type="string")]
        source = [FieldModel(name="a", type="string"), FieldModel(name="b", type="string")]
        df = PivotLonger().transform(df=df, destination=destination, source=source)
        assert df.columns.tolist() == [*kept, "name", "value"]

    @pytest.mark.xfail(strict=True, raises=AttributeError, reason="a null in the source crashes the split")
    def test_separate_passes_nulls_through(self):
        df = pd.DataFrame({"s": ["a;b", None, "c;d"]})
        destination = [FieldModel(name="p", type="string"), FieldModel(name="q", type="string")]
        df = Separate().transform(df=df, destination=destination, source=[FieldModel(name="s", type="string")], source_param=";")
        assert df[["p", "q"]].values.tolist() == [["a", "b"], [None, None], ["c", "d"]]

    @pytest.mark.xfail(strict=True, raises=KeyError, reason="a null header row raises KeyError")
    def test_pivot_categories_refuses_a_null_header(self):
        df = pd.DataFrame({"c": ["Cat1", "t2", None, "t4"]})
        with pytest.raises(ValueError, match="2"):
            PivotCategories().transform(
                df=df, destination=FieldModel(name="cat", type="string"), source=FieldModel(name="c", type="string"), assigned=[0, 2]
            )
