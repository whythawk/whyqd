# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import locale
import subprocess
import sys
import pytest

from whyqd.parsers import ReadingParser

LOCALES = ["C.UTF-8", "en_US.UTF-8", "de_DE.UTF-8"]


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
        read = ReadingParser().read(cells=["1234.50", "1,234", "-7"], dtype="number")
        assert [r.value for r in read] == [1234.5, None, -7.0]
        assert read[1].reason == "undeclared-character"

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
