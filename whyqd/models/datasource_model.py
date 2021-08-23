from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, validator, constr
import mimetypes
from uuid import UUID, uuid4
import string


from ..parsers import CoreScript, WranglingScript
from ..types import MimeType
from ..models import CitationModel, ColumnModel, ActionScriptModel


class DataSourceModel(BaseModel):
    uuid: UUID = Field(
        default_factory=uuid4, description="Automatically generated unique identity for the data source."
    )
    path: constr(strip_whitespace=True) = Field(..., description="Full path to valid source data file.")
    mime: MimeType = Field(default=None, description="Mime type for source data. Automatically generated.")
    sheet_name: Optional[str] = Field(
        None,
        description="Needed if MimeType is either of XLS or XLSX, and the data consists of multiple sheets.",
    )
    names: Optional[List[ColumnModel]] = Field(
        [],
        description="If the source data has no header row, explicitly pass a list of column names - in the correct order - to address the data. May not be known until after initial wrangling.",
    )
    columns: List[ColumnModel] = Field(
        [], description="List of ColumnModel with names & type derived from the source data."
    )
    preserve: Optional[List[ColumnModel]] = Field(
        [],
        description="List of columns where variable type guessing must be prevented and the original data preserved. Critical for foreign key references with weird formats, like integers with leading `0`.",
    )
    key: Optional[ColumnModel] = Field(
        None, description="A key column required before merging of multiple data sources into an interim data source."
    )
    actions: List[ActionScriptModel] = Field(
        [],
        description="List of Actions in script format to be performed on these data, in this order. Will be parsed and validated seperately.",
    )
    checksum: str = Field(
        default=None, description="Checksum for source data file. Automatically generated. Based on Blake2b."
    )
    citation: Optional[CitationModel] = Field(None, description="Optional full citation for the source data.")

    class Config:
        use_enum_values = True
        anystr_strip_whitespace = True
        validate_assignment = True

    @validator("mime", pre=True, always=True)
    def generate_mime_type(cls, v, values, **kwargs):
        mimetypes.init()
        mmtp = MimeType(mimetypes.guess_type(values["path"])[0])
        if v and v != mmtp:
            raise ValueError(
                f"Mimetype provided ({v}) is not equal to the generated mimetype ({mmtp}). Either provide 'None', or check your source."
            )
        return mmtp

    @validator("preserve")
    def preserve_check(cls, v, values, **kwargs):
        if not values["columns"] or set([p.name for p in v]).difference([c.name for c in values["columns"]]):
            raise ValueError(
                f"Columns ({set([p.name for p in v]).difference([c.name for c in values['columns']])}) not in source data columns."
            )
        return v

    @validator("key")
    def key_check(cls, v, values, **kwargs):
        if not values["columns"] or v.name not in [c.name for c in values["columns"]]:
            raise ValueError(f"Key column ({v.name}) not in list of columns.")
        return v

    @validator("checksum", pre=True, always=True)
    def generate_checksum(cls, v, values, **kwargs):
        check = CoreScript().get_checksum(values["path"])
        if v and v != check:
            # Check the data checksum instead
            df_columns = [d.name for d in values["columns"]]
            names = [d.name for d in values["names"]] if values.get("names") else None
            df = WranglingScript().get_dataframe(
                values["path"],
                filetype=values["mime"],
                names=names,
                preserve=[d.name for d in values.get("preserve", []) if d.name in df_columns],
            )
            check = CoreScript().get_data_checksum(df)
            if v and v != check:
                raise ValueError(
                    f"Checksum provided ({v}) is not equal to the generated checksum ({check}). Either provide 'None', or check your source."
                )
        return check

    @property
    def source(self) -> str:
        return f"{str(self.uuid)}.{MimeType(self.mime).name.lower()}"

    @property
    def title(self) -> str:
        root = "".join(c for c in self.path.split("/")[-1] if c in f"-_. {string.ascii_letters}{string.digits}")
        if self.sheet_name:
            return f"{root}::{self.sheet_name}"
        return root
