# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pydantic import field_validator, StringConstraints, ConfigDict, BaseModel, Field, AnyUrl
from typing import Annotated, ClassVar, Optional
import math


class CitationModel(BaseModel):
    """BibTeX model for citations.

    https://www.bibtex.com/format/

    Includes some non-standard fields.
    """

    MONTHS: ClassVar[tuple[str, ...]] = tuple("jan feb mar apr may jun jul aug sep oct nov dec".split())

    author: str = Field(
        ..., description="The name(s) of the author(s) (in the case of more than one author, separated by `and`)."
    )
    title: str = Field(..., description="The title of the work.")
    url: Optional[AnyUrl] = Field(
        None,
        description="The URL field is used to store the URL of a web page or FTP download. It is a non-standard BibTeX field.",
    )
    publisher: Optional[str] = Field(None, description="The publisher's name.")
    institution: Optional[str] = Field(
        None, description="The institution that was involved in the publishing, but not necessarily the publisher."
    )
    doi: Optional[str] = Field(
        None,
        description="The doi field is used to store the digital object identifier (DOI) of a journal article, conference paper, book chapter or book. It is a non-standard BibTeX field. It's recommended to simply use the DOI, and not a DOI link.",
    )
    month: Optional[Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True)]] = Field(
        None,
        description="The month of publication (or, if unpublished, the month of creation). Use three-letter abbreviation.",
    )
    year: Optional[int] = Field(None, description="The year of publication (or, if unpublished, the year of creation).")
    licence: Optional[str] = Field(
        None, description="The terms under which the associated resource are licenced for reuse."
    )
    note: Optional[str] = Field(None, description="Miscellaneous extra information.")
    model_config = ConfigDict(validate_assignment=True)

    @field_validator("month")
    @classmethod
    def month_abbreviation(cls, v: Optional[str]):
        if v is None:
            return v
        if v.lower() not in cls.MONTHS:
            raise ValueError(
                f"The citation's month `{v}` is not one of BibTeX's three-letter months. Write it as one, `jan` to `dec`. "
                "[whyqd:citation-month]"
            )
        return v.lower()

    @field_validator("year")
    @classmethod
    def year_is_four(cls, v: Optional[int]):
        if v is None:
            return v
        if v < 1000 or int(math.log10(v)) + 1 != 4:
            raise ValueError(
                f"The citation's year `{v}` is not four digits. Write the year in full, such as `2024`. "
                "[whyqd:citation-year]"
            )
        return v
