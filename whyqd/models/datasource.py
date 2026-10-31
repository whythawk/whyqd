# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import Annotated, Optional, List, Dict, Any
from pydantic import StringConstraints, field_validator, ConfigDict, BaseModel, Field, ValidationInfo, RootModel
import string

from whyqd.dtypes import MimeType
from whyqd.models import ChecksumModel, CitationModel, ColumnModel
from whyqd.models.dialect import DialectModel
from whyqd.models.identifier import Identifier


class DataSourceAttributeModel(RootModel):
    # https://docs.pydantic.dev/latest/concepts/models/#rootmodel-and-custom-root-types
    root: Dict[str, Any]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __setitem__(self, item, term):
        self.root[item] = term

    @property
    def terms(self):
        return self.root


class DataSourceModel(BaseModel):
    uuid: Identifier = Field(description="Automatically generated unique identity for the data source.")
    title: Optional[str] = Field(None, description="A descriptive name for the data source.")
    description: Optional[str] = Field(
        None,
        description="A complete description of the data source. Depending on how complex your work becomes, try and be as helpful as possible to 'future-you'. You'll thank yourself later.",
    )
    path: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(..., description="Full path to valid source data file.")
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
    dialect: Optional[DialectModel] = Field(None, description="How the file is written, so it can be read.")
    hidden: Optional[bool] = Field(
        None, description="The publisher hid this sheet of the workbook; it is read like any other. Absent where visible."
    )
    attributes: Optional[DataSourceAttributeModel] = Field(
        {},
        description="Optional open dictionary for reader-specific attributes for Pandas' API. E.g. 'quoting' for the CSV library.",
    )
    checksums: List[ChecksumModel] = Field(
        ...,
        description="Checksums proving the source data, each naming what it hashed: the table as 1.x read it, or the file's bytes.",
    )
    index: Optional[int] = Field(None, description="Count of rows in source data table.")
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")
    model_config = ConfigDict(use_enum_values=True, validate_assignment=True)

    @field_validator("preserve")
    @classmethod
    def preserve_check(cls, v: Optional[List[str]], info: ValidationInfo):
        if not info.data["columns"] or set(v).difference([c.name for c in info.data["columns"]]):
            raise ValueError(
                f"Columns ({set(v).difference([c.name for c in info.data['columns']])}) not in source data columns."
            )
        return v

    @field_validator("key")
    @classmethod
    def key_check(cls, v: Optional[List[str]], info: ValidationInfo):
        if not info.data["columns"] or set(v).difference([c.name for c in info.data["columns"]]):
            raise ValueError(
                f"Key columns ({set(v).difference([c.name for c in info.data['columns']])}) not in source data columns."
            )
        return v

    def get_checksum(self, content: str) -> str | None:
        """The checksum value that hashed `content`, or None."""
        return next((c.checksumValue for c in self.checksums if c.content == content), None)

    @property
    def name(self) -> str:
        root = "".join(c for c in self.path.split("/")[-1] if c in f"-_. {string.ascii_letters}{string.digits}")
        sheet = self.sheet_name or (self.dialect.sheet if self.dialect else None)
        if sheet:
            return f"{root}::{sheet}"
        return root
