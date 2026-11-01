# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
import hashlib
import json

if TYPE_CHECKING:
    import polars as pl


class FingerprintParser:
    """Two proofs of a source: its file's byte hash, which any byte changes, and `fp0`, which only its data changes.

    `fp0` proves a source's data, not its file, however the means of reading it changes, so it is defined here without
    reference to any library, and anyone can recompute it. Each sheet of a workbook has its own, a hidden one included,
    and each other file one. It is taken before any row is skipped, joined, or taken as the header, and before any cell
    is trimmed, so no setting changes it. A file saved again with its data unchanged keeps it, in any encoding; a save
    that changes a cell's type or text does not, even if the file looks the same. Both are BLAKE2b-512.

    The bytes hashed, in UTF-8: `fp0`, then, each after a `\\n`, a line for each row of the grid, its trailing empty
    rows and columns trimmed. A line is a JSON array in the canonical form of
    [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785), holding each cell as `[type, text]` (`CellType`, `CellParser`),
    or `null` where empty. The sheet's name is not in them: it finds the sheet, and renaming one changes no value.

    Example
    -------
    A grid of `Code` above the number 12 hashes the bytes `fp0\\n[["s","Code"]]\\n[["n","12"]]`.
    """

    VERSION = "fp0"

    def byte_hash(self, *, source: str | Path) -> str:
        """The file's bytes, hashed."""
        checksum = hashlib.blake2b()
        with open(source, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                checksum.update(chunk)
        return checksum.hexdigest()

    def fp0(self, *, grid: pl.DataFrame, types: pl.DataFrame) -> str:
        """The `fp0` of one sheet, or of a file without sheets, from its grid and types.

        Example
        -------
        ```python
        grid = pl.DataFrame({"column_0": ["Code", "12"]})
        types = pl.DataFrame({"column_0": ["s", "n"]})
        FingerprintParser().fp0(grid=grid, types=types)
        ```
        """
        checksum = hashlib.blake2b()
        checksum.update(self.VERSION.encode())
        for texts, tags in zip(grid.iter_rows(), types.iter_rows(), strict=True):
            row = [None if text is None else [tag, text] for text, tag in zip(texts, tags, strict=True)]
            # For arrays of strings and nulls alone, these settings write what RFC 8785 writes
            checksum.update(b"\n" + json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        return checksum.hexdigest()
