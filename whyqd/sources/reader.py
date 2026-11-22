# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
from typing import ClassVar

import polars as pl

from whyqd.dtypes import MimeType, Place
from whyqd.models import DialectModel, FindingModel, ProposalModel


class Reader:
    """One format's reader: the file as the grid, and what else only that format can show.

    Each reader gives the grid (`grid`) and says how its rows are counted (`PLACE`) and which of the dialect's settings
    it reads (`DIALECT`). The rest has a default, so a caller never asks which reader it holds: a workbook's sheets, its
    number formats, and what its cells hold beyond their text, and the settings that would read past a file's faults.
    """

    PLACE: ClassVar[Place]
    DIALECT: ClassVar[tuple[str, ...]]
    # Whether the grid proves the file's data (`fp0`): not where the grid depends on how the file is read
    FINGERPRINTED: ClassVar[bool] = True
    WORKBOOK: ClassVar[bool] = False

    def grid(
        self, *, source: Path, mime: MimeType, dialect: DialectModel
    ) -> tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel]:
        """The file's grid and each cell's type, where in the file each grid row is, counted from 1, and the dialect
        with what the read settled recorded."""
        raise NotImplementedError

    def sheets(self, *, source: Path) -> list[tuple[str, bool]]:
        """Each sheet's name, in order, and whether its publisher hid it; a reader with `WORKBOOK` gives them."""
        raise NotImplementedError

    def formats(
        self, *, source: Path, mime: MimeType, sheet: str | None, height: int, width: int
    ) -> pl.DataFrame | None:
        """Each cell's number format code, in the grid's shape, or `None` for a file that stores none."""
        return None

    def facts(self, *, source: Path, sheet: str | None, types: pl.DataFrame) -> dict[str, list[str]]:
        """What the file holds that its grid's text does not show: `merged` ranges and `errors`, each cell named."""
        return {"merged": [], "errors": []}

    def proposals(
        self, *, source: Path, mime: MimeType, dialect: DialectModel, faults: list[FindingModel]
    ) -> list[ProposalModel]:
        """The settings that would read past the file's faults, each with its evidence."""
        return []

    def encoding_proposal(
        self, *, source: Path, dialect: DialectModel, faults: list[FindingModel]
    ) -> ProposalModel | None:
        """The encoding the file more likely is, where its read suggests another."""
        return None

    def unreadable(self, *, source: Path, kind: str) -> ValueError:
        """The refusal for a file that is not what its format says, for the reader to raise."""
        return ValueError(
            f"`{source.name}` cannot be opened as {kind}. Check its format, or ask its owner for a sound copy. "
            "[whyqd:file-unreadable]"
        )
