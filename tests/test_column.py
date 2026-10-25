# SPDX-License-Identifier: BSD-3-Clause
import io
import pandas as pd
import pytest

from whyqd.parsers import ColumnParser

REPEATS = [
    ["name", "value"],
    ["a", "a", "a"],
    ["a", "a", "a.1"],
    ["a.1", "a", "a"],
    ["a", "b", "a", "b", "a"],
    ["a", "a.1", "a", "a.2", "a"],
]


class TestColumn:
    @pytest.mark.parametrize("columns", REPEATS, ids=[",".join(c) for c in REPEATS])
    def test_repeats_named_as_the_read_names_them(self, columns):
        # Stored source schemas hold the names this read gave
        read = pd.read_csv(io.StringIO(",".join(columns) + "\n" + ",".join("1" * len(columns)) + "\n"))
        assert ColumnParser().deconflict(columns=columns) == read.columns.tolist()

    def test_reserved_renamed_even_once(self):
        column = ColumnParser()
        assert column.deconflict(columns=["x", "y"], reserved=lambda c: c == "x") == ["x.1", "y"]
        assert column.deconflict(columns=["x", "x.1"], reserved=lambda c: c == "x") == ["x.2", "x.1"]
