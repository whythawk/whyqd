# SPDX-License-Identifier: BSD-3-Clause
"""A PDF's tables, read by what the file shows and by what the wrangler declares.

What a PDF shows is read, never asked: whether it has text at all, its orientation, and whether its table is ruled,
which sets how cells are found (`lines`, by the ruling, else `text`, by where the text sits), recorded in `cells`. A row
equal to the header row is the header repeated atop a page and is dropped. What it cannot show is declared: the pages
(`pages`), the columns of an unruled table (`columns`, their left edges in points), and the names. A cell's line
breaks are kept as extracted, since a wrap and a break look the same in a PDF, so the tests compare a cell's words.
"""

import csv
import json
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.parsers import DataSourceParser, RowKeyParser

DATA = Path(__file__).resolve().parent / "data"
SOURCE = DATA / "synthetic-layouts" / "pdf-source.pdf"
KEY = json.loads((DATA / "synthetic-layouts" / "answer-key.json").read_text(encoding="utf-8"))["pdf"]["pdf-source.pdf"]
SAMPLE = DATA / "sample" / "pdf"
ROW = RowKeyParser.ROW
# The pages each sheet of `pdf-source.xlsx` printed to
PAGES = {"Ruled": "1", "MergedHeader": "2", "Landscape": "4", "RepeatedHeader": "5-7", "HeaderOnce": "8-10"}
# Today no PDF is read
NOT_BUILT = pytest.mark.xfail(strict=True, raises=(ValueError, TypeError), reason="no PDF reader")


def read(source: Path, dialect: dict, names: list[str] | None = None) -> tuple[qd.models.DataSourceModel, pd.DataFrame]:
    datasource = qd.DataSourceDefinition()
    datasource.derive_model(
        source=source, mimetype="PDF", dialect=dialect, **({} if names is None else {"names": names})
    )
    model = datasource.get[0] if isinstance(datasource.get, list) else datasource.get
    df = DataSourceParser().get(source=model)
    assert df[ROW].tolist() == list(range(len(df)))
    return model, df


def words(rows: list[list[str | None]]) -> list[list[str | None]]:
    # A cell's words, so a wrap kept as a line break compares equal to the space it replaced; an empty cell is missing
    return [
        [None if c is None or pd.isna(c) or not str(c).split() else " ".join(str(c).split()) for c in r] for r in rows
    ]


def table(df: pd.DataFrame, names: list[str]) -> list[list[str | None]]:
    return words(df[names].values.tolist())


def expected(path: Path) -> tuple[list[str], list[list[str | None]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        header, *rows = list(csv.reader(f))
    return header, words(rows)


class TestRead:
    @pytest.mark.parametrize("name", ["Ruled", "Landscape", "RepeatedHeader", "HeaderOnce"])
    @NOT_BUILT
    def test_a_ruled_table_reads_to_its_key(self, name):
        # Landscape needs no setting; a header repeated atop each page is dropped
        model, df = read(SOURCE, {"pages": PAGES[name]})
        assert model.dialect.cells == "lines"
        assert [c.name for c in model.columns] == KEY[name]["names"]
        assert table(df, KEY[name]["names"]) == words(KEY[name]["rows"])

    @NOT_BUILT
    def test_a_line_break_in_a_cell_is_kept(self):
        model, df = read(SOURCE, {"pages": PAGES["Ruled"]})
        assert any("\n" in str(v) for v in df["Property Address"])

    @NOT_BUILT
    def test_a_header_over_two_rows_takes_the_names_given(self):
        names = ["Propref", "Address", "Postcode", "Relief Code", "R/V"]
        model, df = read(SOURCE, {"pages": PAGES["MergedHeader"], "headerRowCount": 2}, names)
        assert table(df, names) == words(KEY["MergedHeader"]["rows"])

    @NOT_BUILT
    def test_an_unruled_table_reads_by_text_position(self):
        model, df = read(SOURCE, {"pages": "11"})
        assert model.dialect.cells == "text"
        # Undeclared, each wrapped line is a row of its own: loaded, not refused, for the wrangler to see and declare
        assert len(df) > len(KEY["UnruledWrapped"]["rows"])

    @pytest.mark.xfail(strict=True, raises=AssertionError, reason="no PDF reader")
    def test_a_scanned_page_is_refused_saying_why(self):
        with pytest.raises(ValueError, match=r"(?is)(image|scan).*text|text.*(image|scan)"):
            read(SAMPLE / "maldon-page-1-scanned.pdf", {})


class TestSample:
    """The sample's PDFs against the extractions saved beside them."""

    @NOT_BUILT
    def test_west_berkshire_reliefs_reads_by_its_ruling(self):
        header, rows = expected(SAMPLE / "west-berkshire-reliefs.csv")
        model, df = read(SAMPLE / "NNDR RELIEFS 15 04 2026 pages 1-3.pdf", {})
        assert [c.name for c in model.columns] == header
        assert table(df, header) == rows

    @NOT_BUILT
    def test_west_berkshire_exemptions_reads_with_its_repeated_headers_dropped(self):
        header, rows = expected(SAMPLE / "west-berkshire-exemptions.csv")
        model, df = read(SAMPLE / "NNDR EXEMPTIONS.pdf", {})
        assert model.dialect.cells == "lines"
        assert table(df, header) == rows

    @NOT_BUILT
    def test_maldon_reads_with_its_columns_declared(self):
        # Unruled: read by text position its words split mid-word, so the columns' left edges, from its header line
        header, rows = expected(SAMPLE / "2026-03-27-maldon-empty.CSV")
        dialect = {"skipRows": 1, "cells": "text", "columns": [19, 151, 262, 364, 463, 496, 533, 679]}
        model, df = read(SAMPLE / "NDR_Empty_Property_List___March_2026.pdf", dialect)
        assert [c.name for c in model.columns] == header
        assert table(df, header) == rows
