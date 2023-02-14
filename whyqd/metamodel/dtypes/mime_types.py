from enum import Enum


class MimeType(str, Enum):
    # Note that neither `feather` nor `parquet` yet have official mime types.
    CSV = "text/csv"
    XLS = "application/vnd.ms-excel"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PRQ = "application/vnd.apache.parquet"
    FTR = "application/vnd.apache.feather"
