# SPDX-License-Identifier: BSD-3-Clause
"""A CSV's encoding, as the wrangler declares it or as the ladder settles it, recorded so the read repeats.

The ladder decodes as the WHATWG Encoding Standard does, which CSVW's dialect names its encodings by: a byte-order mark,
over any declaration; otherwise the declared encoding; otherwise strict UTF-8, then `windows-1252`, which in the standard
decodes any byte and loses none. Nothing is detected: a file the ladder reads as `windows-1252` that is in fact another
encoding loads with every byte kept, and reads to its text once the wrangler declares the encoding.
"""

import csv
import io
import json
from pathlib import Path

import pandas as pd
import pytest

import whyqd as qd
from whyqd.models import DialectModel
from whyqd.parsers import DataSourceParser, RowKeyParser

SYNTHETIC = Path(__file__).resolve().parent / "data" / "synthetic"
KEY = json.loads((SYNTHETIC / "answer-key.json").read_text(encoding="utf-8"))["csv"]
ROW = RowKeyParser.ROW
# Today the data source keeps no dialect, and a dialect given reaches pandas' reader, which refuses it
NOT_BUILT = pytest.mark.xfail(strict=True, raises=(AssertionError, ValueError), reason="the reader takes no dialect")
# The bytes Python's `cp1252` leaves undefined, which the standard decodes to the code point of their value
UNDEFINED = {0x81, 0x8D, 0x8F, 0x90, 0x9D}


def read(name: str, dialect: dict | None = None) -> tuple[qd.models.DataSourceModel, pd.DataFrame]:
    datasource = qd.DataSourceDefinition()
    settings = {} if dialect is None else {"dialect": dialect}
    datasource.derive_model(source=SYNTHETIC / name, mimetype="CSV", **settings)
    assert datasource.get.dialect is not None
    return datasource.get, DataSourceParser().get(source=datasource.get)


def windows_1252(data: bytes) -> str:
    return "".join(chr(b) if b in UNDEFINED else bytes([b]).decode("cp1252") for b in data)


def rows(df: pd.DataFrame, names: list[str]) -> list[list[str | None]]:
    assert df[ROW].tolist() == list(range(len(df)))
    return [[None if pd.isna(c) else c for c in row] for row in df[names].values.tolist()]


def cells(rows: list[list[str]]) -> list[list[str | None]]:
    # The key writes an empty cell as the file does; the table holds it as missing, as `CellParser.render` gives it
    return [[c if c != "" else None for c in row] for row in rows]


class TestLadder:
    @pytest.mark.parametrize(
        "name, step, encoding",
        [
            ("fixture-utf8.csv", "utf-8", "utf-8"),
            ("fixture-utf8-crlf.csv", "utf-8", "utf-8"),
            ("fixture-utf8-mixed-eol.csv", "utf-8", "utf-8"),
            ("fixture-utf8-bom.csv", "bom", "utf-8"),
            ("fixture-utf16-bom.csv", "bom", "utf-16le"),
        ],
    )
    @NOT_BUILT
    def test_a_file_reads_to_its_key_and_records_the_step(self, name, step, encoding):
        model, df = read(name)
        assert (model.dialect.encodingStep, model.dialect.encoding) == (step, encoding)
        assert [c.name for c in model.columns] == KEY[name]["header"]
        assert rows(df, KEY[name]["header"]) == cells(KEY[name]["rows"])

    @pytest.mark.parametrize("name", ["fixture-windows-1252.csv", "fixture-latin-1.csv", "fixture-mac-roman.csv"])
    @NOT_BUILT
    def test_bytes_not_utf8_are_read_as_windows_1252_and_every_byte_kept(self, name):
        model, df = read(name)
        assert (model.dialect.encodingStep, model.dialect.encoding) == ("windows-1252", "windows-1252")
        header, *expected = list(csv.reader(io.StringIO(windows_1252((SYNTHETIC / name).read_bytes()))))
        assert rows(df, header) == cells(expected)

    @NOT_BUILT
    def test_text_is_kept_as_written(self):
        # Zero-width characters, a byte-order mark inside text, control characters, NFC beside NFD, full-width digits
        name = "fixture-unicode-utf8.csv"
        model, df = read(name)
        assert rows(df, KEY[name]["header"]) == cells(KEY[name]["rows"])


class TestDeclared:
    @pytest.mark.parametrize(
        "name, encoding",
        [
            ("fixture-mac-roman.csv", "macintosh"),
            ("fixture-windows-1252.csv", "windows-1252"),
            ("fixture-utf8.csv", "utf-8"),
        ],
    )
    @NOT_BUILT
    def test_a_declared_encoding_reads_to_the_key(self, name, encoding):
        model, df = read(name, {"encoding": encoding})
        assert (model.dialect.encodingStep, model.dialect.encoding) == ("declared", encoding)
        assert rows(df, KEY[name]["header"]) == cells(KEY[name]["rows"])

    @NOT_BUILT
    def test_a_byte_order_mark_overrides_the_declaration(self):
        name = "fixture-utf8-bom.csv"
        model, df = read(name, {"encoding": "windows-1252"})
        assert (model.dialect.encodingStep, model.dialect.encoding) == ("bom", "utf-8")
        assert rows(df, KEY[name]["header"]) == cells(KEY[name]["rows"])

    # `pytest.warns` reports pandas' `Invalid dialect` as no warning
    @pytest.mark.xfail(strict=True, raises=pytest.fail.Exception, reason="the reader takes no dialect")
    def test_bytes_a_declared_encoding_cannot_decode_are_replaced_with_one_warning(self):
        # CSVW reads with the standard's replacement error mode; the declaration still stands, and the source is unchanged
        name = "fixture-windows-1252.csv"
        text = (SYNTHETIC / name).read_bytes().decode("utf-8", errors="replace")
        with pytest.warns(UserWarning) as record:
            model, df = read(name, {"encoding": "utf-8"})
        assert (model.dialect.encodingStep, model.dialect.encoding) == ("declared", "utf-8")
        header, *expected = list(csv.reader(io.StringIO(text)))
        assert rows(df, header) == cells(expected)
        # One summary, never a line per byte: the count, and the encoding to declare instead
        messages = [str(w.message) for w in record if "utf-8" in str(w.message)]
        assert len(messages) == 1
        assert str(text.count("�")) in messages[0] and "windows-1252" in messages[0]

    @pytest.mark.xfail(strict=True, raises=pytest.fail.Exception, reason="`detected` is still an encoding step")
    def test_detected_is_not_a_step(self):
        # A detected encoding is a proposal, recorded as `declared` once the wrangler accepts it
        with pytest.raises(ValueError):
            DialectModel(encodingStep="detected")
