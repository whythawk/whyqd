# SPDX-License-Identifier: BSD-3-Clause
import pytest

import whyqd as qd
from whyqd.parsers import DataSourceParser, RowKeyParser


class TestRowKey:
    def test_parts(self):
        row_key = RowKeyParser()
        assert row_key.part() == row_key.ROW == "__row__"
        assert row_key.part(index=1) == "__row__1"
        with pytest.raises(ValueError):
            row_key.part(index=-1)
        names = ["__row__", "__row__1", "__row__12", "__row__.1", "__row__0", "row", "x"]
        assert [row_key.is_part(c) for c in names] == [True, True, True, False, False, False, False]

    def test_source_columns_named_like_the_key_are_renamed(self):
        row_key = RowKeyParser()
        assert row_key.deconflict(columns=["__row__", "name"]) == ["__row__.1", "name"]
        assert row_key.deconflict(columns=["__row__", "name", "__row__.1"]) == ["__row__.2", "name", "__row__.1"]
        assert row_key.deconflict(columns=["__row__1", "__row__"]) == ["__row__1.1", "__row__.1"]

    def test_every_key_name_left_free(self):
        row_key = RowKeyParser()
        columns = ["__row__", "__row__", "__row__.1", "__row__1", "__row__1.1", "__row__0", "name", "name"]
        renamed = row_key.deconflict(columns=columns)
        assert not any(row_key.is_part(c) for c in renamed)
        assert len(set(renamed)) == len(columns)

    def test_sort_order(self):
        columns = ["name", "__row__2", "__row__", "__row__.1", "__row__1"]
        assert RowKeyParser().sort_order(columns=columns) == ["__row__", "__row__1", "__row__2"]

    @pytest.mark.parametrize("dialect", [{}, {"headerRowCount": 0}, {"skipRows": 1}])
    def test_numbering_matches_the_read(self, tmp_path, dialect):
        # Row numbers that DELETE_ROWS and PIVOT_CATEGORIES scripts hold come from this read
        source = tmp_path / "rows.csv"
        lines = ["title,", "name,value", "a,1", "b,2"]
        source.write_text("\n".join(lines) + "\n", encoding="utf-8")
        datasource = qd.DataSourceDefinition()
        datasource.derive_model(source=source, mimetype="CSV", dialect=dialect)
        df = DataSourceParser().get(source=datasource.get)
        start = RowKeyParser().first_position(dialect=datasource.get.dialect)
        assert df[RowKeyParser.ROW].tolist() == df.index.tolist() == list(range(len(lines) - start))
        assert df.iloc[0].tolist()[1] == lines[start].split(",")[0]
