# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
import hashlib
import json

if TYPE_CHECKING:
    import polars as pl


class FingerprintParser:
    """Two proofs of a source file: its byte hash, which any byte changes, and `fp0`, which only a cell changes.

    `fp0` hashes the file's grid as its reader parses it, every sheet in workbook order, a hidden one included, before
    any row is skipped, joined, or taken as the header, and before any cell is trimmed: it proves the file, not what
    is read from it. Each cell is its stored type and whyqd's text (`CellType`, `CellParser`), so `fp0` is the same
    through any reader and in any encoding, and a file saved again with no cell changed, such as after a column is
    widened, keeps it. Both are BLAKE2b-512.

    The form hashed: `fp0`, then for each sheet a line holding `{"sheet": name}` (`""` for a file without sheets),
    then a line for each row of its grid, trailing empty rows and columns trimmed, a JSON array of each cell as
    `[type, text]`, or `null` where empty; UTF-8, lines joined by `\\n`.
    """

    VERSION = "fp0"

    def byte_hash(self, *, source: str | Path) -> str:
        """The file's bytes, hashed."""
        checksum = hashlib.blake2b()
        with open(source, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                checksum.update(chunk)
        return checksum.hexdigest()

    def fp0(self, *, sheets: list[tuple[str, pl.DataFrame, pl.DataFrame]]) -> str:
        """The file's `fp0`, from each sheet's name, grid, and types, in workbook order.

        Example
        -------
        ```python
        grid = pl.DataFrame({"column_0": ["Code", "12"]})
        types = pl.DataFrame({"column_0": ["s", "n"]})
        FingerprintParser().fp0(sheets=[("Data", grid, types)])
        ```
        """
        checksum = hashlib.blake2b()
        checksum.update(self.VERSION.encode())
        for name, grid, types in sheets:
            checksum.update(b"\n" + json.dumps({"sheet": name}, ensure_ascii=False).encode("utf-8"))
            for texts, tags in zip(grid.iter_rows(), types.iter_rows(), strict=True):
                row = [None if text is None else [tag, text] for text, tag in zip(texts, tags, strict=True)]
                checksum.update(b"\n" + json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        return checksum.hexdigest()
