from __future__ import annotations
from pydantic import field_validator, StringConstraints, ConfigDict, BaseModel, Field, AnyUrl
from typing import Optional
import math
from typing_extensions import Annotated


class CitationModel(BaseModel):
    """BibTeX model for citations.

    https://www.bibtex.com/format/

    Includes some non-standard fields.
    """

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
        if v.lower() not in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]:
            raise ValueError("Month must conform to the BibTeX three-letter code definition.")
        return v.lower()

    @field_validator("year")
    @classmethod
    def year_is_four(cls, v: Optional[int]):
        if v < 1000 or int(math.log10(v)) + 1 != 4:
            raise ValueError(
                "Year must be in the period 1000 to 9999. There may be a year 9999 problem, but if you're still using this software by then, I'll be impressed."
            )
        return v
