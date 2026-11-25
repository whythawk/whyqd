# SPDX-License-Identifier: BSD-3-Clause
from enum import Enum


class MimeType(str, Enum):
    """A source's format, by its media type. Neither Feather nor Parquet has an official one, so each takes the type its
    project uses; `PRQ` and `FTR` are names for the same two, so `MimeType.value_of("prq")` finds Parquet."""

    CSV = "text/csv"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PARQUET = "application/vnd.apache.parquet"
    PRQ = "application/vnd.apache.parquet"
    FEATHER = "application/vnd.apache.feather"
    FTR = "application/vnd.apache.feather"
    PDF = "application/pdf"

    @classmethod
    def value_of(cls, value):
        # https://stackoverflow.com/a/56567247/295606
        # Allows:
        #   `MimeType.value_of("prq")`
        #   <MimeType.PARQUET: 'application/vnd.apache.parquet'>
        for k, v in cls.__members__.items():
            if k.upper() == value.upper():
                return v
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{value}'")
