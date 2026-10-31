# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path

import polars as pl

from whyqd.dtypes import MimeType
from whyqd.models import DialectModel
from whyqd.parsers.grid import GridParser


class PdfParser:
    """A PDF's table as the grid, at best effort: a PDF holds a printed page, not a table.

    What the file shows is read: whether it holds text, and whether its ruling gives a table, which sets how cells are
    found (`cells`). What it cannot show is declared: the pages, an unruled table's columns, and the names. A cell keeps
    its line breaks, since a wrap and a break look the same on a page. A row equal to a header row is that header
    repeated atop a later page, and is left out. Read through pdfplumber, the `pdf` extra.
    """

    PLACE = "row"
    # Points between the tops of two words on one line: pdfplumber's own `y_tolerance`
    LINE = 3

    def __init__(self) -> None:
        self.grids = GridParser()

    def grid(
        self, *, source: Path, mime: MimeType, dialect: DialectModel
    ) -> tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel]:
        """The table's grid and its types, every cell text, each grid row's number in the order read, and the dialect
        with `cells` recorded. It has no `fp0`, since the grid depends on how the PDF is read: its `cells`, `columns`,
        and `pages`.

        Raises
        ------
        ImportError
            Without the `pdf` extra.
        ValueError
            For a PDF with no text, such as a scan, or pages it does not have.
        """
        try:
            import pdfplumber
        except ImportError as e:
            raise ImportError("Reading a PDF needs the extra: pip install whyqd[pdf] [whyqd:pdf-extra]") from e
        with pdfplumber.open(source) as pdf:
            pages = self.pages(pages=pdf.pages, declared=dialect.pages, source=source)
            if not any(page.chars for page in pages):
                raise ValueError(
                    f"`{source.name}` holds no text on {'its pages' if dialect.pages is None else 'pages ' + dialect.pages}, "
                    "only images: it is a scan. Recognise its text first (OCR), or load the file it was printed from. "
                    "[whyqd:pdf-scan]"
                )
            if dialect.columns:
                cells = "text"
                rows = [row for page in pages for row in self.lines(page=page, columns=dialect.columns)]
            else:
                cells = dialect.cells or ("lines" if any(page.find_tables() for page in pages) else "text")
                rows = []
                for page in pages:
                    for table in page.extract_tables(self.settings(cells=cells)):
                        rows.extend(table)
        rows = self.unrepeated(rows=rows, dialect=dialect)
        width = max((len(r) for r in rows), default=0)
        grid = pl.DataFrame(
            {f"column_{i}": [r[i] if i < len(r) and r[i] else None for r in rows] for i in range(width)},
            schema={f"column_{i}": pl.String for i in range(width)},
        )
        grid, types = self.grids.trim(grid=grid)
        return grid, types, list(range(1, grid.height + 1)), dialect.model_copy(update={"cells": cells})

    def pages(self, *, pages: list, declared: str | None, source: Path) -> list:
        """The pages a dialect's `pages` names, counted from 1, or every page."""
        if declared is None:
            return pages
        chosen = []
        for part in declared.replace(" ", "").split(","):
            first, _, last = part.partition("-")
            try:
                numbers = range(int(first), int(last or first) + 1)
            except ValueError as e:
                raise ValueError(
                    f"`pages` `{declared}` names pages by number from 1: `5-7`, or `1,3,5-7`. [whyqd:pdf-pages]"
                ) from e
            if not numbers or numbers.start < 1 or numbers.stop - 1 > len(pages):
                raise ValueError(
                    f"`pages` `{declared}` names a page `{source.name}` does not have: it has {len(pages)}. "
                    "[whyqd:pdf-pages]"
                )
            chosen.extend(pages[n - 1] for n in numbers)
        return chosen

    def settings(self, *, cells: str) -> dict:
        """pdfplumber's table settings for how cells are found."""
        if cells == "lines":
            return {}
        return {"vertical_strategy": "text", "horizontal_strategy": "text"}

    def lines(self, *, page, columns: list[float]) -> list[list[str | None]]:
        """A page's rows under declared columns: each line of text a row, each word in the column it starts in.

        A word belongs to the last column whose left edge it starts at or after, one left of the first edge to the
        first; words whose tops are within `LINE` points of each other are one line, and a cell's words are joined by
        one space, so a run of spaces in the PDF reads as one. pdfplumber finds no cells where a mostly empty column
        meets the page's edge, so the words are placed here, by the declared edges alone.
        """
        rows, top = [], None
        for word in sorted(page.extract_words(), key=lambda w: (round(w["top"]), w["x0"])):
            if top is None or word["top"] - top > self.LINE:
                rows.append([[] for _ in columns])
                top = word["top"]
            column = max([0, *(i for i, edge in enumerate(columns) if word["x0"] >= edge)])
            rows[-1][column].append(word)
        return [[" ".join(w["text"] for w in sorted(cell, key=lambda w: w["x0"])) or None for cell in row] for row in rows]

    def unrepeated(self, *, rows: list[list[str | None]], dialect: DialectModel) -> list[list[str | None]]:
        """The rows without any equal to a header row after the header, each being that header atop a later page."""
        start, end = dialect.skipRows, dialect.skipRows + dialect.headerRowCount
        header = [self.row(r) for r in rows[start:end]]
        return rows[:end] + [r for r in rows[end:] if self.row(r) not in header]

    def row(self, row: list[str | None]) -> tuple[str, ...]:
        cells = [c or "" for c in row]
        while cells and not cells[-1]:
            cells.pop()
        return tuple(cells)
