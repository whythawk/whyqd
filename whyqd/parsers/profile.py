# SPDX-License-Identifier: BSD-3-Clause
import polars as pl

from whyqd.config.patterns import PolarsPatterns
from whyqd.dtypes import CellType
from whyqd.models import ProfileModel


class ProfileParser:
    """What a column holds, as read, in counts. Profiling never changes a cell.

    Any cell may hold a hard space, a zero-width character, or a control character (`PolarsPatterns`); only a text
    cell is zero-padded (`0012`) or date-like. Format codes are counted for number and date cells alone.
    """

    FORMATTED = [CellType.NUMBER.value, CellType.DATE.value]

    def __init__(self) -> None:
        self.patterns = PolarsPatterns()

    def profile(self, *, text: pl.Series, types: pl.Series, formats: pl.Series | None = None) -> ProfileModel:
        """A column's profile from its cells' text, their stored types, and, for an `.xlsx`, their format codes.

        Parameters
        ----------
        text: pl.Series
            Each cell's text as stored, null where empty.
        types: pl.Series
            Each cell's `CellType` tag.
        formats: pl.Series | None, default None
            Each cell's number format code; none for a file that stores none.
        """
        p = self.patterns
        found = dict(types.drop_nulls().value_counts().iter_rows())
        is_text = types == CellType.STRING.value
        counts = {}
        if formats is not None:
            coded = dict(formats.filter(types.is_in(self.FORMATTED)).drop_nulls().value_counts().iter_rows())
            counts = dict(sorted(coded.items(), key=lambda c: (-c[1], c[0])))
        return ProfileModel(
            cellTypes={t.value: found[t.value] for t in CellType if t.value in found},
            blank=text.null_count(),
            whitespace=text.str.contains(p.WHITESPACE).sum(),
            hardSpace=text.str.contains(p.HARD_SPACE).sum(),
            zeroWidth=text.str.contains(p.ZERO_WIDTH).sum(),
            control=text.str.contains(p.CONTROL).sum(),
            dateLike=(
                is_text & (text.str.contains(p.DATE) | (text.str.contains(p.MONTH) & text.str.contains(p.DIGIT)))
            ).sum(),
            zeroPadded=(is_text & text.str.contains(p.ZERO_PADDED)).sum(),
            numberFormats=counts,
        )
