from datetime import date, datetime, time
from decimal import Decimal
import pytest

from whyqd.dtypes import CellType
from whyqd.parsers import CellParser

# One stored cell as each Excel reader hands it over: python-calamine, openpyxl, and xlrd
SAME_CELL = [
    ("whole number", [1.0, 1, 1.0], (CellType.NUMBER, "1")),
    ("decimal", [43.4, 43.4, 43.4], (CellType.NUMBER, "43.4")),
    ("date", [datetime(2024, 4, 1), datetime(2024, 4, 1), date(2024, 4, 1)], (CellType.DATE, "2024-04-01")),
    ("date and time", [datetime(2024, 4, 1, 9, 30)] * 3, (CellType.DATE, "2024-04-01T09:30:00")),
    ("boolean", [True, True, bool(1)], (CellType.BOOLEAN, "TRUE")),
    ("empty", [None, "", None], None),
]


class TestCell:
    @pytest.mark.parametrize("name,values,expected", SAME_CELL, ids=[c[0] for c in SAME_CELL])
    def test_every_reader_gives_one_text(self, name, values, expected):
        cell = CellParser()
        assert {cell.render(value=v) for v in values} == {expected}

    def test_errors(self):
        cell = CellParser()
        assert cell.render(value="#N/A", error=True) == (CellType.ERROR, "#N/A")
        assert cell.render(value="#NAME?", error=True) == (CellType.ERROR, "#NAME?")

    def test_text_stays_text(self):
        cell = CellParser()
        for text in [" ", "\xa0", "0000130842", "TRUE", "1.0", "2024-04-01"]:
            assert cell.render(value=text) == (CellType.STRING, text)

    def test_numbers(self):
        cell = CellParser()
        assert cell.render(value=False) == (CellType.BOOLEAN, "FALSE")
        assert cell.render(value=2**60 + 1) == (CellType.NUMBER, "1152921504606846977")
        assert cell.render(value=-0.0) == (CellType.NUMBER, "0")
        assert cell.render(value=0.1) == (CellType.NUMBER, "0.1")
        assert cell.render(value=1e20) == (CellType.NUMBER, "100000000000000000000")
        for value in [float("nan"), float("inf")]:
            with pytest.raises(ValueError):
                cell.render(value=value)

    def test_times(self):
        cell = CellParser()
        assert cell.render(value=time(0)) == (CellType.DATE, "00:00:00")
        assert cell.render(value=datetime(2024, 4, 1, 0, 0, 0, 500)) == (CellType.DATE, "2024-04-01T00:00:00.000500")

    def test_other_types_refused(self):
        with pytest.raises(TypeError):
            CellParser().render(value=Decimal("1.5"))
