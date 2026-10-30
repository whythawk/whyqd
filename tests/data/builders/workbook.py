# SPDX-License-Identifier: BSD-3-Clause
"""Save a workbook as Excel and LibreOffice save one: text with leading or trailing whitespace marked to keep it.

openpyxl writes `<t> </t>` where Excel writes `<t xml:space="preserve"> </t>`, and a reader may drop whitespace that
is not marked, as python-calamine does, so a fixture saved by openpyxl alone would test a file no spreadsheet writes.

    python tests/data/builders/workbook.py <workbook.xlsx> ...

marks workbooks already saved, in place.
"""

import re
import sys
import zipfile
from pathlib import Path

UNMARKED = re.compile(rb"<t>(\s[^<]*|[^<]*\s)</t>")


def mark(path: Path) -> None:
    """Mark the whitespace in a saved workbook's text, writing it anew beside it and then moving it into place."""
    staged = path.with_suffix(".marking")
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(staged, "w", zipfile.ZIP_DEFLATED) as marked:
        for item in source.infolist():
            data = source.read(item)
            if item.filename.startswith("xl/worksheets/") or item.filename == "xl/sharedStrings.xml":
                data = UNMARKED.sub(rb'<t xml:space="preserve">\1</t>', data)
            marked.writestr(item, data)
    staged.replace(path)


def save(workbook, path: Path) -> None:
    workbook.save(path)
    mark(path)


if __name__ == "__main__":
    for name in sys.argv[1:]:
        mark(Path(name))
