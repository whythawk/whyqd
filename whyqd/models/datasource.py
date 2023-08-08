from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, constr
from uuid import UUID, uuid4
import string

from whyqd.dtypes import MimeType
from whyqd.models import CitationModel, ColumnModel


class DataSourceAttributeModel(BaseModel):
    # https://docs.pydantic.dev/latest/usage/models/#custom-root-types
    __root__: Dict[str, Any]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]

    def __setitem__(self, item, term):
        self.__root__[item] = term

    @property
    def terms(self):
        return self.__root__


class DataSourceModel(BaseModel):
    uuid: UUID = Field(
        default_factory=uuid4, description="Automatically generated unique identity for the data source."
    )
    title: Optional[str] = Field(None, description="A descriptive name for the data source.")
    description: Optional[str] = Field(
        None,
        description="A complete description of the data source. Depending on how complex your work becomes, try and be as helpful as possible to 'future-you'. You'll thank yourself later.",
    )
    path: constr(strip_whitespace=True) = Field(..., description="Full path to valid source data file.")
    mime: MimeType = Field(..., description="Mime type for source data. Automatically generated.")
    header: Optional[int] = Field(
        0, description="Row (0-indexed) to use for the column labels of the parsed DataFrame. "
    )
    sheet_name: Optional[str] = Field(
        None,
        description="Needed if MimeType is either of XLS or XLSX, and the data consists of multiple sheets.",
    )
    names: Optional[List[str]] = Field(
        [],
        description="If the source data has no header row, explicitly pass a list of column names - in the correct order - to address the data. May not be known until after initial wrangling.",
    )
    columns: List[ColumnModel] = Field(
        ..., description="List of ColumnModel with names & type derived from the source data. In table order."
    )
    preserve: Optional[List[str]] = Field(
        [],
        description="List of columns where variable type guessing must be prevented and the original data preserved. Critical for foreign key references with weird formats, like integers with leading `0`.",
    )
    key: Optional[List[str]] = Field(
        [],
        description="A list of key columns required before merging of multiple data sources into an interim data source.",
    )
    attributes: Optional[DataSourceAttributeModel] = Field(
        {},
        description="Optional open dictionary for reader-specific attributes for Pandas' API. E.g. 'quoting' for the CSV library.",
    )
    checksum: str = Field(default=..., description="Checksum for source data file. Based on Blake2b.")
    index: Optional[int] = Field(None, description="Count of rows in source data table.")
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")

    class Config:
        use_enum_values = True
        # anystr_strip_whitespace = True
        validate_assignment = True

    @validator("preserve")
    def preserve_check(cls, v, values, **kwargs):
        if not values["columns"] or set(v).difference([c.name for c in values["columns"]]):
            raise ValueError(
                f"Columns ({set(v).difference([c.name for c in values['columns']])}) not in source data columns."
            )
        return v

    @validator("key")
    def key_check(cls, v, values, **kwargs):
        if not values["columns"] or set(v).difference([c.name for c in values["columns"]]):
            raise ValueError(
                f"Key columns ({set(v).difference([c.name for c in values['columns']])}) not in source data columns."
            )
        return v

    @property
    def hexed_filename(self) -> str:
        return f"{str(self.uuid)}.{MimeType(self.mime).name.lower()}"

    @property
    def name(self) -> str:
        root = "".join(c for c in self.path.split("/")[-1] if c in f"-_. {string.ascii_letters}{string.digits}")
        if self.sheet_name:
            return f"{root}::{self.sheet_name}"
        return root
