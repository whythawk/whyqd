# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from whyqd.dtypes import EncodingStep


class DialectModel(BaseModel):
    """How a file is written, so it can be read: the dialect of the W3C's CSV on the Web metadata vocabulary
    ([Metadata Vocabulary for Tabular Data, section 5.9](https://www.w3.org/TR/tabular-metadata/#dialect-descriptions)),
    with its names and defaults, and whyqd's own: `encodingStep`, `rowsPerRecord`, `sheet`, and, for a PDF, `cells`,
    `pages`, and `columns`.

    One default differs: CSV on the Web trims each cell, and whyqd keeps it as written (`trim` false). A blank line is
    a row (`skipBlankRows` false), in both.
    """

    encoding: str = Field("utf-8", description="The file's encoding, as the WHATWG Encoding Standard names it.")
    encodingStep: Optional[EncodingStep] = Field(None, description="What settled the encoding.")
    delimiter: str = Field(",", description="The character between cells.")
    quoteChar: Optional[str] = Field('"', description="The character quoting a cell; `null` for none.")
    doubleQuote: bool = Field(True, description="A quote inside a quoted cell is doubled; if false, escaped by `\\`.")
    skipRows: int = Field(0, ge=0, description="Rows before the header, or before the data where there is no header.")
    headerRowCount: int = Field(1, ge=0, description="Header rows; `0` where the file has none.")
    skipBlankRows: bool = Field(False, description="Leave out blank rows. By default a blank row is a row.")
    trim: Union[bool, Literal["start", "end"]] = Field(False, description="Strip whitespace around each cell.")
    rowsPerRecord: Optional[list[int]] = Field(
        None,
        description="The fields in each row of one record, header included, where a record spans several rows: "
        "`[47, 1]` is 47 fields on the first row and 1 on the next. Absent where a record is one row.",
    )
    sheet: Optional[str] = Field(None, description="The spreadsheet's sheet, where the file has several.")
    cells: Optional[Literal["lines", "text"]] = Field(
        None,
        description="How a PDF's cells are found: by its ruling (`lines`), or by where its text sits (`text`). Read "
        "from the file where undeclared: `lines` where its ruling gives a table, else `text`.",
    )
    pages: Optional[str] = Field(
        None, description="A PDF's pages holding the table, counted from 1: `5-7`, or `1,3,5-7`. Absent for every page."
    )
    columns: Optional[list[float]] = Field(
        None,
        description="The left edge of each of a PDF table's columns, in points from the page's left, where its cells "
        "are found by `text` and the words do not show the columns.",
    )
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)
