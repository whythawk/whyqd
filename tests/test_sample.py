# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path

import pytest

import whyqd as qd

from tests.test_json_schema import errors

SAMPLE = Path(__file__).resolve().parent / "data" / "sample"
TRANSFORMS = sorted(SAMPLE.glob("*/*.TRANSFORM"))


def without_nulls(value):
    if isinstance(value, dict):
        return {k: without_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [without_nulls(v) for v in value]
    return value


def source_file(transform: Path) -> Path:
    """The spreadsheet beside a stored transform, which was saved with the path it had where it was made."""
    (found,) = [p for p in transform.parent.iterdir() if p.suffix.lower() in {".xlsx", ".xls", ".csv"}]
    return found


class TestStoredTransforms:
    @pytest.mark.parametrize("path", TRANSFORMS, ids=lambda p: p.parent.name)
    def test_reads_and_writes_both_formats(self, path):
        original = json.loads(path.read_text(encoding="utf-8"))
        transform = qd.TransformDefinition(transform=path)
        assert json.loads(transform.get_json(format="1.x")) == without_nulls(original)
        written = json.loads(transform.get_json())
        assert written["formatVersion"] == "2.0"
        assert errors("transform", original, format="1.x") == []
        assert errors("transform", written, format="2.0") == []

    @pytest.mark.parametrize("path", TRANSFORMS, ids=lambda p: p.parent.name)
    def test_source_checksum_verifies(self, path):
        model = qd.TransformDefinition(transform=path).get.dataSource
        model = model.model_copy(update={"path": str(source_file(path))})
        assert qd.DataSourceDefinition(source=model).validate()
