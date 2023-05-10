from enum import Enum


class MimeType(str, Enum):
    # Note that neither `feather` nor `parquet` yet have official mime types.
    CSV = "text/csv"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PARQUET = "application/vnd.apache.parquet"
    PRQ = "application/vnd.apache.parquet"
    FEATHER = "application/vnd.apache.feather"
    FTR = "application/vnd.apache.feather"

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
