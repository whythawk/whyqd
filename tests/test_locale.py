from pathlib import Path
import locale
import math
import subprocess
import sys
import pytest

from whyqd.parsers import DataSourceParser

LOCALES = ["C.UTF-8", "en_US.UTF-8", "de_DE.UTF-8"]
NAN = float("nan")
# Text, then parse_float's and parse_int's answers. Some are wrong (lost signs, ignored letters) and are
# pinned as they are: these tests prove only that the machine's locale cannot change them.
CASES = [
    ("£43.40", 43.4, None),
    ("¬£43.40", 43.4, None),
    ("£-826.80", 826.8, None),
    ("-£826.80", 826.8, None),
    ("£1,234.50", 1234.5, None),
    ("£.00", 0.0, None),
    ("12.50", 12.5, 12),
    (" 7", 7.0, 7),
    ("1e3", 1000.0, None),
    ("(826.80)", 826.8, None),
    ("826.80-", 826.8, 826),
    ("1,234", 1234.0, None),
    ("0000130842", 130842.0, 130842),
    ("5%", NAN, None),
    ("−45", 45.0, None),
    ("１２", 12.0, 12),
    ("1.234,50", 1234.5, 1),
    ("1,5", 1.5, None),
    ("826.80 CR", 826.8, 826),
    ("N/A", NAN, None),
    ("12k", NAN, None),
    ("£10 - £20", NAN, None),
    ("Trans Prem: £0.01", 0.01, None),
    ("1.2.3", NAN, 1),
    ("", NAN, None),
    ("   ", NAN, None),
    ("\xa0", NAN, None),
    ("\t", NAN, None),
    ("1.234", 1.234, 1),
    ("€-12,30", -12.3, None),
    ("1,234.50", 1234.5, None),
    ("12", 12.0, 12),
    ("-7", -7.0, -7),
]


@pytest.fixture(params=LOCALES)
def machine_locale(request):
    previous = locale.setlocale(locale.LC_ALL)
    try:
        locale.setlocale(locale.LC_ALL, request.param)
    except locale.Error:
        pytest.skip(f"{request.param} is not installed")
    yield request.param
    locale.setlocale(locale.LC_ALL, previous)


class TestLocale:
    def test_numbers_ignore_machine_locale(self, machine_locale):
        reader = DataSourceParser()
        for text, number, integer in CASES:
            parsed = reader.parse_float(text)
            if math.isnan(number):
                assert math.isnan(parsed), text
            else:
                assert parsed == number, text
            assert reader.parse_int(text) == integer, text

    @pytest.mark.parametrize("name", LOCALES)
    def test_import_leaves_locale_unchanged(self, name):
        try:
            previous = locale.setlocale(locale.LC_ALL)
            locale.setlocale(locale.LC_ALL, name)
            locale.setlocale(locale.LC_ALL, previous)
        except locale.Error:
            pytest.skip(f"{name} is not installed")
        script = (
            "import locale; before = locale.setlocale(locale.LC_ALL); import whyqd; "
            "after = locale.setlocale(locale.LC_ALL); assert before == after, (before, after)"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env={"LC_ALL": name, "PATH": ""},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
