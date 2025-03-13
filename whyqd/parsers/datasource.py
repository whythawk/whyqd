from __future__ import annotations
from typing import List, Union, Type, TYPE_CHECKING
from pathlib import Path
from datetime import date, datetime
import pandas as _pd
import modin.pandas as pd
import numpy as np
from pyarrow.parquet import ParquetFile
import pyarrow as pa
import re
import locale
import ast

from whyqd.parsers.core import CoreParser
from whyqd.models import ColumnModel, DataSourceModel, DataSourceAttributeModel
from whyqd.dtypes import MimeType, FieldType
from whyqd.config.ray_init import ray_start

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except locale.Error:
    # Readthedocs has a problem, but difficult to replicate
    locale.setlocale(locale.LC_ALL, "")

if TYPE_CHECKING:
    from whyqd.core import SchemaDefinition


class DataSourceParser:
    """Get, review and restructure tabular source data."""

    def __init__(self):
        self.core = CoreParser()
        self.DATE_FORMATS = {
            "date": {"fmt": ["%Y-%m-%d"], "txt": ["YYYY-MM-DD"]},
            "datetime": {
                "fmt": ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S %Z%z"],
                "txt": ["YYYY-MM-DD hh:mm:ss", "YYYY-MM-DD hh:mm:ss UTC+0000"],
            },
            "year": {"fmt": ["%Y"], "txt": ["YYYY"]},
        }

    ###################################################################################################
    ### TABULAR DATA READERS AND WRITERS
    ###################################################################################################

    def read_excel(self, *, source: str | Path, **kwargs) -> dict[str, pd.DataFrame] | pd.DataFrame:
        # This will default to returning a dictionary of dataframes for each sheet
        # https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html
        ray_start()
        if kwargs.get("sheet_name"):
            # Only going to return a single dataframe
            # Modin can't seem to read sheets correctly
            return pd.DataFrame(_pd.read_excel(source, **kwargs))
        df = pd.read_excel(source, **kwargs)
        keys = list(df.keys())
        for k in keys:
            if df[k].empty:
                del df[k]
        if len(df.keys()) == 1:
            df = df[keys[0]]
        return df

    def read_csv(self, *, source: str | Path, **kwargs) -> pd.DataFrame:
        # New in pandas 1.3: will ignore encoding errors - perfect for this initial wrangling process
        # https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
        ray_start()
        kwargs["encoding_errors"] = "ignore"
        # Supposed to help with fruity separater guessing
        kwargs["engine"] = "python"
        if not kwargs.get("nrows"):
            df = pd.read_csv(source, **kwargs)
        else:
            kwargs["iterator"] = True
            kwargs["chunksize"] = 10000
            df_iterator = pd.read_csv(source, **kwargs)
            df = pd.concat(df_iterator, ignore_index=True)
        return df

    def read_parquet(self, *, source: str | Path, nrows: int | None = None, **kwargs) -> pd.DataFrame:
        # https://pandas.pydata.org/docs/reference/api/pandas.read_parquet.html
        if nrows:
            # https://stackoverflow.com/a/69888274/295606
            pf = ParquetFile(str(source))
            pf = next(pf.iter_batches(batch_size=nrows))
            # https://arrow.apache.org/docs/python/generated/pyarrow.Table.html#pyarrow.Table.to_pandas
            return pa.Table.from_batches([pf]).to_pandas(**kwargs)
        ray_start()
        if "engine" not in kwargs:
            kwargs["engine"] = "pyarrow"
        return pd.read_parquet(source, **kwargs)

    def read_feather(self, *, source: str | Path, **kwargs) -> pd.DataFrame:
        # https://pandas.pydata.org/docs/reference/api/pandas.read_feather.html
        ray_start()
        return pd.read_feather(source, **kwargs)

    def get(
        self,
        *,
        source: str | Path | DataSourceModel,
        mimetype: str | MimeType | None = None,
        header: int | None = 0,
        preserve: str | list[str] | bool = False,
        names: list[str] | None = None,
        nrows: int | None = None,
        sheet_name: str | None = None,
        directory: str | Path | None = None,
        **attributes,
    ) -> dict[str, pd.DataFrame] | pd.DataFrame | None:
        """Return a Pandas dataframe from a given source.

        Accepts default pandas parameters for Excel and CSV, but the objective is to preserve the source data with
        little data conversion outside of the data wrangling process.

        Parameters
        ----------
        source: str | Path | DataSourceModel
            Path to source data file.
        mimetype: str | MimeType
            **whyqd** supports reading from CSV, XLS, XLSX, Feather and Parquet files.
        header: int, default 0
            Row to use as the column headings. Default is 0.
        preserve: str or list of str, default None
            Column names where variable type guessing must be prevented and the original data preserved.
            Critical for foreign key references with weird formats, like integers with leading `0`.
            Only works for CSV and Excel.
        names: list of str, default None
            If the source data has no header row, explicitly pass a list of names - in the correct order - to address
            the data. Only works for CSV and Excel.
        nrows: int, default None
            A specified number of rows to return. For review, it is faster to load only a small number.
            Only works for CSV and Excel.
        sheet_name: str, default None
            If the source is a multi-sheet Excel file, and you know the sheet, you can load that specifically. If you
            need to apply parameters specific to each sheet, it's best to load individually. Default, load all.
        directory: str | Path, default None
            An optional working directory for use for remote source data. Default will be from `settings`.
        attributes: dict of specific `mimetype` related Pandas attributes. Use sparingly.

        Returns
        -------
        DataFrame or dict of DataFrame
        """
        ray_start()
        kwargs = {}
        kwargs |= attributes
        if isinstance(source, DataSourceModel):
            # Additional attributes stored in the model, e.g. End-of-line errors require `quoting=csv.QUOTE_NONE`
            #   quoting: int, default None
            #     CSV errors in opening a source file can be fixed by referencing quotation and end-of-line errors using
            #     `quoting=csv.QUOTE_NONE` and `import csv`.
            if source.attributes:
                kwargs |= source.attributes.terms
            mimetype = source.mime
            preserve = source.preserve
            sheet_name = source.sheet_name
            header = source.header
            if source.names:
                names = source.names
            source = source.path
        if self.core.check_uri(source=source):
            # Modin currently does not work with remote files. It needs a downloaded file.
            # Might have something to do with the way it imports data?
            source = self.core.download_uri_source(source=source, directory=directory)
        if not self.core.check_source(source=source):
            e = f"Source at `{source}` not found."
            raise FileNotFoundError(e)
        # These, currently, don't accept any additional parameters.
        mimetype = self.get_mimetype(mimetype=mimetype)
        if mimetype in [MimeType.PRQ, MimeType.PARQUET]:
            return self.read_parquet(source=source, nrows=nrows, **kwargs)
        if mimetype in [MimeType.FTR, MimeType.FEATHER]:
            return self.read_feather(source=source, **kwargs)
        # If the dtypes have not been set, then ensure that any provided preserved columns remain untouched
        # i.e. no forcing of text to numbers
        # defaulting to `dtype = object` ...
        if preserve:
            if isinstance(preserve, bool):
                kwargs["dtype"] = pd.StringDtype()
                # kwargs["keep_default_na"] = False
                # kwargs["na_values"] = ""
            else:
                if not isinstance(preserve, list):
                    preserve = [preserve]
                # kwargs["dtype"] = {k: object for k in preserve}
                kwargs["dtype"] = {k: pd.StringDtype() for k in preserve}
        kwargs["header"] = header
        if names:
            # Preserve all rows
            kwargs["header"] = None
            kwargs["names"] = names
        if nrows:
            kwargs["nrows"] = nrows
        # Check mimetype
        if mimetype in [MimeType.XLS, MimeType.XLSX]:
            kwargs["sheet_name"] = sheet_name
            return self.read_excel(source=source, **kwargs)
        if mimetype == MimeType.CSV:
            return self.read_csv(source=source, **kwargs)
        # Unknown mimetype
        raise FileExistsError(f"Source at `{source}` does not have a recognised mimetype `{mimetype}`.")

    def set(self, *, df: pd.DataFrame, source: str | Path, mimetype: MimeType) -> None:
        """Save a Pandas dataframe from a given source.

        Parameters
        ----------
        source: str
            Source filename.
        mimetype: MimeType
            **whyqd** supports saving to CSV, XLS, XLSX, Feather and Parquet files.
        df: pd.DataFrame
        """
        if not isinstance(source, Path):
            source = Path(source)
        try:
            source = source.with_suffix(f".{mimetype.name}")
        except Exception:
            raise FileExistsError(f"Save mimetype not supported, `{mimetype}`.")
        if mimetype in [MimeType.PRQ, MimeType.PARQUET]:
            df.to_parquet(path=source, engine="pyarrow", index=False)
        if mimetype in [MimeType.FTR, MimeType.FEATHER]:
            df.to_feather(path=source)
        if mimetype in [MimeType.XLS, MimeType.XLSX]:
            df.to_excel(source, index=False)
        if mimetype == MimeType.CSV:
            df.to_csv(source, index=False)

    ###################################################################################################
    ### TABULAR DATA SCHEMA COERSION UTILITIES
    ###################################################################################################

    def coerce_to_schema(self, *, df: pd.DataFrame, schema: Type[SchemaDefinition]) -> pd.DataFrame:
        # https://modin.readthedocs.io/en/stable/flow/modin/core/dataframe/pandas/partitioning/partition.html#modin.core.dataframe.pandas.partitioning.partition.PandasDataframePartition.to_numpy
        # CHECK: https://github.com/modin-project/modin/issues/3966
        validate = {"matched": [], "unmatched": [], "coerced": []}
        columns = self.get_header_columns(df=df)
        for c in columns:
            prospect = schema.fields.get(name=c.name)
            if prospect:
                try:
                    if c.dtype == prospect.dtype:
                        validate["matched"].append(c.name)
                    else:
                        # Try coerce the column to the type
                        df[c.name] = self.coerce_column_to_dtype(column=_pd.Series(df[c.name].to_numpy()), coerce=prospect.dtype)
                        validate["coerced"].append(c.name)
                    df[c.name] = _pd.Series(df[c.name].to_numpy()).astype(FieldType(prospect.dtype).astype)
                except (TypeError, SyntaxError, ValueError):
                    from_type = c.dtype
                    if isinstance(df[c.name][0], list):
                        from_type = "array"
                    e = f"Column '{c.name}' in Data cannot be converted from type '{from_type}' to '{prospect.dtype}'."
                    raise TypeError(e)
            else:
                validate["unmatched"].append(c.name)
        if validate["unmatched"]:
            self.core.show_warning(
                f"{len(validate['unmatched'])} columns in Data not found in Schema. {validate['unmatched']}"
            )
        if validate["coerced"]:
            self.core.show_warning(
                f"{len(validate['coerced'])} columns in Data were coerced to appropriate dtypes in Schema. {validate['coerced']}"
            )
        return df

    def coerce_column_to_dtype(self, *, column: pd.Series, coerce: str) -> pd.Series:
        parser = {
            "date": self.parse_dates,
            "usdate": self.parse_usdates,
            "datetime": self.parse_dates,
            "year": self.parse_dates,
            "number": self.parse_float,
            "integer": self.parse_int,
            "boolean": self.parse_bool,
            "array": self.parse_string_list,
            "string": self.parse_string,
        }
        return column.apply(lambda x: parser[coerce](x))

    def validate_schema_coersion(self, *, df: pd.DataFrame, schema: Type[SchemaDefinition]) -> bool:
        """Returns the MimeType representation of of a submitted source datatype."""
        for field in schema.fields.get_all():
            # Tests conversion to type
            series = df[field.name].astype(FieldType(field.dtype).astype)
            # Tests each constraint
            if field.constraints:
                if field.constraints.category:
                    # https://python-reference.readthedocs.io/en/latest/docs/comprehensions/set_comprehension.html
                    constraints = {c.name for c in field.constraints.category}
                    difference = {
                        term for term in series.unique() if not (term is pd.NA or pd.isnull(term) or term is None)
                    } - constraints
                    if difference:
                        raise ValueError(
                            f"Terms in `{field.name}` not defined as a category constraint: `{list(difference)}`"
                        )
                if field.constraints.required and len(series) != series.count():
                    raise ValueError(
                        f"Required constraint in `{field.name}` has `{len(series) - series.count()}` null values in `{len(series)}` rows."
                    )
                if field.constraints.unique and series.count() != len(series.unique()):
                    raise ValueError(
                        f"Unique constraint in `{field.name}` has `{series.count() - len(series.unique())}` non-unique values in `{series.count()}` rows."
                    )
                if field.constraints.minimum and series.min() < field.constraints.minimum:
                    raise ValueError(
                        f"Minimum constraint in `{field.name}` has value `{series.min()}` < `{field.constraints.minimum}`"
                    )
                if field.constraints.maximum and series.max() > field.constraints.maximum:
                    raise ValueError(
                        f"Minimum constraint in `{field.name}` has value `{series.max()}` > `{field.constraints.maximum}`"
                    )
        return True

    ###################################################################################################
    ### DATA MODEL SCHEMA DERIVATION AND WRITER UTILITIES
    ###################################################################################################

    def derive_data_model(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        sheet_name: str | None = None,
        header: int | list[int] | None = 0,
        **attributes,
    ) -> DataSourceModel | list[DataSourceModel]:
        """Derive a data model schema (or list) from a data source. All columns will be coerced to `string` type to
        preserve data quality even though this is far less efficient.

        Parameters
        ----------
        source: str
            Source filename.
        mimetype: str or MimeType
            Pandas can read a diversity of mimetypes. **whyqd** supports `xls`, `xlsx`, `csv`, `parquet` and `feather`.
        sheet_name: str, default None.
            If `mimetype` is a multi-sheeted Excel file, specify which one to use.
        header: int | list[int | None] | None = 0,
            Row (0-indexed) to use for the column labels of the parsed DataFrame. If there are multiple sheets, then
            a list of integers should be provided.
            If `header` is `None`, row 0 will be treated as values and a set of field names will be generated indexed
            to the number of data columns.
        attributes: dict of specific `mimetype` related Pandas attributes. Use sparingly.

        Returns
        -------
        List of DataSourceModel, or DataSourceModel
        """
        response = []
        mimetype = self.get_mimetype(mimetype=mimetype)
        sheet_names = [sheet_name]
        if sheet_name is None and mimetype in [MimeType.XLS, MimeType.XLSX]:
            # Check for multiple sheets
            df = self.read_excel(source=source, sheet_name=sheet_name, nrows=1, **attributes)
            if isinstance(df, dict):
                # Multiple sheets
                sheet_names = list(df.keys())
        for i, sheet_name in enumerate(sheet_names):
            header_i = header
            if isinstance(header, list):
                header_i = header[i]
            if header_i is None:
                header_names = self.create_header_names(
                    source=source, mimetype=mimetype, sheet_name=sheet_name, **attributes
                )
            else:
                header_names = self.get_header_names(
                    source=source, mimetype=mimetype, sheet_name=sheet_name, header=header_i, **attributes
                )
            response.append(
                self.get_source_data_model(
                    source=source,
                    mimetype=mimetype,
                    names=header_names,
                    sheet_name=sheet_name,
                    header=header_i,
                    **attributes,
                )
            )
        if len(response) > 1:
            return response
        return response[0]

    def get_source_data_model(
        self,
        *,
        df: pd.DataFrame | None = None,
        source: Path | str,
        mimetype: str | MimeType,
        names: list[str] | None = None,
        sheet_name: str | None = None,
        header: int | None = 0,
        **attributes,
    ) -> DataSourceModel:
        """Derive a data model schema from a SINGLE tabular data source. All columns will be coerced to `string` type to
        preserve data quality even though this is far less efficient.

        Parameters
        ----------
        source: str | Path
            Source filename.
        mimetype: str or MimeType
            Pandas can read a diversity of mimetypes. **whyqd** supports `xls`, `xlsx`, `csv`, `parquet` and `feather`.
        names: list of str
            A de-conflicted list of header-row names.
        sheet_name: str, default None.
            If `mimetype` is a multi-sheeted Excel file, specify which one to use.
        header: int, default 0
            Row (0-indexed) to use for the column labels of the parsed DataFrame.
        attributes: dict of specific `mimetype` related Pandas attributes. Use sparingly.

        Returns
        -------
        DataSourceModel
        """
        del_df = False
        if df is None:
            del_df = True
            if header is None or header != 0:
                # If names are specified, then header is None
                df = self.get(
                    source=source,
                    mimetype=mimetype,
                    names=names,
                    preserve=names,
                    sheet_name=sheet_name,
                    header=None,
                    **attributes,
                )
            else:
                df = self.get(source=source, mimetype=mimetype, preserve=names, sheet_name=sheet_name, **attributes)
        columns = self.get_header_columns(df=df)
        preserve = [c.name for c in columns if c.dtype == "string"]
        source_data_model = {
            "path": str(source),
            "mime": self.get_mimetype(mimetype=mimetype),
            "sheet_name": sheet_name,
            "columns": columns,
            "preserve": preserve,
            "checksum": self.get_checksum(df=df),
            "header": header,
            "index": df.shape[0],
            "attributes": DataSourceAttributeModel.model_validate(attributes),
        }
        if header is None or header != 0:
            source_data_model["names"] = names
        if del_df:
            del df
        return DataSourceModel(**source_data_model)

    def create_header_names(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        sheet_name: str | None = None,
        nrows: int = 50,
        **attributes,
    ) -> list[str]:
        """
        Return a list of default column names - starting with `column-0` - to apply to a given SINGULAR tabular data
        source.

        Parameters
        ----------
        source: str
            Source filename.
        mimetype: MimeType, default MimeType.CSV
            Pandas can read a diversity of mimetypes, but whyqd has only been tested on `xls`, `xlsx` and `csv`.
        sheet_name: str, default None.
            If `mimetype` is a multi-sheeted Excel file, specify which one to use.
        nrows: int, default 50
            A specified number of rows to return. For review, it is faster to load only a small number.
        attributes: dict of specific `mimetype` related Pandas attributes. Use sparingly.

        Returns
        -------
        List of str
        """
        df = self.get(source=source, mimetype=mimetype, sheet_name=sheet_name, nrows=nrows, **attributes)
        if (isinstance(df, dict) and not df) or df.empty:
            return []
        return [f"column_{i}" for i in range(len(df.columns))]

    def get_header_names(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        sheet_name: str | None = None,
        header: int | None = 0,
        nrows: int = 1,
        **attributes,
    ) -> list[str]:
        """Return a list of column names to apply to a given SINGULAR tabular data source.

        Parameters
        ----------
        source: str
            Source filename.
        mimetype: MimeType, default MimeType.CSV
            Pandas can read a diversity of mimetypes, but whyqd has only been tested on `xls`, `xlsx` and `csv`.
        sheet_name: str, default None.
            If `mimetype` is a multi-sheeted Excel file, specify which one to use.
        header: int, default 0
            Row (0-indexed) to use for the column labels of the parsed DataFrame.
        nrows: int, default 1
            A specified number of rows to return. For review, it is faster to load only a small number.
        attributes: dict of specific `mimetype` related Pandas attributes. Use sparingly.

        Returns
        -------
        List of str
        """
        if header is not None and header > nrows:
            nrows = header + 1
        df = self.get(source=source, mimetype=mimetype, sheet_name=sheet_name, header=header, nrows=nrows, **attributes)
        return df.columns.tolist()

    def get_header_columns(self, *, df: pd.DataFrame) -> List[ColumnModel]:
        """Returns a list of ColumnModels from a source DataFrame.

        Parameters
        ----------
        df: pd.DataFrame
            Should be derived from `get` with a sensible default for `nrows` being 50.

        Returns
        -------
        List of ColumnModel
        """
        # Prepare summary
        try:
            columns = [
                {"name": k, "type": "number"}
                if v in ["float64", "int64", "Float64", "Int64"]
                else {"name": k, "type": "date"}
                if v in ["datetime64[ns]"]
                else {"name": k, "type": "string"}
                for k, v in df.dtypes.apply(lambda x: x.name).to_dict().items()
            ]
        except AttributeError:
            # No idea ... some seem to give shit
            columns = [
                {"name": k, "type": "number"}
                if v in ["float64", "int64", "Float64", "Int64"]
                else {"name": k, "type": "date"}
                if v in ["datetime64[ns]"]
                else {"name": k, "type": "string"}
                for k, v in df.dtypes.apply(lambda x: str(x)).to_dict().items()
            ]
        return [ColumnModel(**c) for c in columns]

    ###################################################################################################
    ### GENERAL UTILITIES
    ###################################################################################################

    def get_mimetype(self, mimetype: str | MimeType) -> MimeType:
        """Returns the MimeType representation of a submitted source datatype.

        Parameters
        ----------
        mimetype: str or MimeType

        Returns
        -------
        MimeType
        """
        if isinstance(mimetype, MimeType):
            return mimetype
        elif isinstance(mimetype, str):
            try:
                return MimeType.value_of(mimetype)
            except ValueError:
                return MimeType(mimetype)
        raise ValueError(f"MimeType not found for '{mimetype}'")

    def deduplicate_columns(self, *, df: pd.DataFrame) -> pd.Index:
        """
        Source: https://stackoverflow.com/a/65254771/295606
        Source: https://stackoverflow.com/a/55405151
        Returns a new column list permitting deduplication of dataframes which may result from merge.

        Parameters
        ----------
        df: pd.DataFrame

        Returns
        -------
        pd.Index
            Updated column names
        """
        column_index = pd.Series(df.columns.tolist())
        if df.columns.has_duplicates:
            duplicates = column_index[column_index.duplicated()].unique()
            for name in duplicates:
                dups = column_index == name
                replacements = [f"{name}{i}" if i != 0 else name for i in range(dups.sum())]
                column_index.loc[dups] = replacements
        return pd.Index(column_index)

    def get_checksum(self, *, df: pd.DataFrame, crosscheck: str = None) -> str:
        checksum = self.core.get_data_checksum(df=df)
        if crosscheck and checksum != crosscheck:
            raise ValueError(
                f"Checksum provided ({crosscheck}) is not equal to the generated checksum ({checksum}). Check your data source."
            )
        return checksum

    def check_date_format(self, *, date_type: str, date_value: str) -> bool:
        # https://stackoverflow.com/a/37045601
        # https://www.saltycrane.com/blog/2009/05/converting-time-zones-datetime-objects-python/
        for fmt in self.DATE_FORMATS[date_type]["fmt"]:
            try:
                if date_value == datetime.strptime(date_value, fmt).strftime(fmt):
                    return True
            except ValueError:
                continue
        raise ValueError(f"Incorrect date format, should be: `{self.DATE_FORMATS[date_type]['txt']}`")

    ###################################################################################################
    ### PANDAS TYPE PARSERS
    ###################################################################################################

    def _parse_dates(self, x: Union[None, str], dayfirst: bool = True) -> Union[pd.NaT, date.isoformat]:
        """
        This is the hard-won 'trust nobody', certainly not Americans, date parser. This requires that the user
        specify whether the day is first (ISO-style) or not (USA-style).

        NOTE: This is for dates, not datetimes, or times. If it is a properly formatted datetime, it might work
        but don't count on it.

        TODO: Replace with https://github.com/scrapinghub/dateparser
            The only concern is that dateparser.parse(x).date().isoformat() will coerce *any* string to a date,
            no matter *what* it is.

        Parameters
        ----------
        x: str | None
        dayfirst: bool
            Indicates whether this should be considered as an American-format date. Default is `True`, not American.

        Returns
        -------
        pd.NaT | date.isoformat
        """
        if pd.isnull(x):
            return pd.NaT
        if isinstance(x, str) and len(x) <= 10 and ":" in x:
            # This specific variation of a date is interpreted as a time, so ...
            x = re.sub(r"[\\/,\.:;]", "-", x)
        # Check if to_datetime can handle things
        if not pd.isnull(pd.to_datetime(x, errors="coerce", dayfirst=dayfirst)):
            return date.isoformat(pd.to_datetime(x, errors="coerce", dayfirst=dayfirst))
        # Manually see if coersion will work
        x = str(x).strip()[:10]
        # Handles separators in ["\\", "/", ".", "-", ":", ";", ","]
        x = re.sub(r"[\\/,\.:;]", "-", x)
        try:
            if dayfirst:
                # Some attempt at ISO
                y, m, d = x.split("-")
            else:
                # American
                m, d, y = x.split("-")
        except ValueError:
            return pd.NaT
        if dayfirst:
            # Order checks, ignoring US dates ... need to figure whether day or year is first
            if len(d) == 4 or (len(y) <= 2 and len(d) <= 2):
                # Swap the day and year positions
                d, m, y = x.split("-")
        # Fat finger on 1999 ... not going to check for other date errors as no way to figure out
        if len(y) == 4 and y[0] == "9":
            y = "1" + y[1:]
        x = f"{'0' + d if len(d) == 1 else d}-{'0' + m if len(m) == 1 else m}-{'0' + y if len(y) == 1 else y}"
        # Check if to_datetime can handle things
        try:
            if len(y) <= 2:
                # NOTE: if `len(y)` is two digits, then the "earliest" date is 1969 from `69`.
                # Other years will be the future ¯\_(ツ)_/¯
                x = datetime.strptime(x, "%d-%m-%y")
            else:
                x = datetime.strptime(x, "%d-%m-%Y")
        except ValueError:
            return pd.NaT
        x = date.isoformat(x)
        try:
            pd.Timestamp(x)
            return x
        except pd.errors.OutOfBoundsDatetime:
            return pd.NaT

    def parse_dates(self, x: Union[None, str]) -> Union[pd.NaT, date.isoformat]:
        return self._parse_dates(x, dayfirst=True)

    def parse_usdates(self, x: Union[None, str]) -> Union[pd.NaT, date.isoformat]:
        return self._parse_dates(x, dayfirst=False)

    def parse_dates_coerced(self, x: Union[None, str]) -> Union[pd.NaT, pd.Timestamp]:
        return pd.to_datetime(self._parse_dates(x, dayfirst=True), errors="coerce")

    def parse_usdates_coerced(self, x: Union[None, str]) -> Union[pd.NaT, pd.Timestamp]:
        return pd.to_datetime(self._parse_dates(x, dayfirst=False), errors="coerce")

    def _postprocess_parse_float(self, x: str) -> np.nan | float:
        """
        Regex to extract wrecked floats: https://stackoverflow.com/a/71206446
        Checked against: https://regex101.com/
        """
        # https://stackoverflow.com/a/71206446
        if x.group(3):
            return f"{x.group(1).replace(',','').replace('.','')}.{x.group(3)}"
        elif x.group(2):
            return f"{x.group(1).replace(',','').replace('.','')}"
        else:
            return np.nan

    def _preprocess_parse_float(self, x: str | int | float) -> np.nan | float:
        """
        Regex to extract wrecked floats: https://stackoverflow.com/a/385597
        Checked against: https://regex101.com/
        """
        try:
            return float(x)
        except ValueError:
            re_float = re.compile(
                r"""(?x)
            ^
                \D*     		# first, match an optional sign *and space*
                (             # then match integers or f.p. mantissas:
                    \d+       # start out with a ...
                    (
                        \.\d* # mantissa of the form a.b or a.
                    )?        # ? takes care of integers of the form a
                    |\.\d+     # mantissa of the form .b
                )
                ([eE][+-]?\d+)?  # finally, optionally match an exponent
            $"""
            )
            try:
                x = re_float.match(x).group(1)
                x = re.sub(r"[^e0-9,-\.]", "", str(x))
                return locale.atof(x)
            except (ValueError, AttributeError):
                return np.nan
        except TypeError:
            return np.nan

    def parse_float(self, x: str | int | float) -> np.nan | float:
        """
        Regex to extract wrecked floats
        Checked against: https://regex101.com/
        References:
            https://stackoverflow.com/a/73083844
            https://stackoverflow.com/a/385597
            https://stackoverflow.com/a/71206446
        """
        # 1. Try preprocess
        parsed = self._preprocess_parse_float(x)
        if np.isnan(parsed):
            # 2. Try postprocess and re-preprocess
            sign = ""
            try:
                # 2.1 Check for a leading negative sign
                re_float = r"[^\d+-/÷%\*]*"
                parsed = re.sub(re_float, "", x)
                if len(parsed) > 1 and parsed[0] in ["-"]:
                    sign = parsed[0]
            except (ValueError, AttributeError, TypeError):
                return np.nan
            # 2.2 Postprocess as comma/point-separated groups
            re_float = r"\b\d{1,2}\.\d{1,2}\.\d{2}(?:\d{2})?\b|\b(?<!\d[.,])(\d{1,3}(?=([.,])?)(?:\2\d{3})*|\d+)(?:(?(2)(?!\2))[.,](\d+))?\b(?![,.]\d)"
            parsed = list(filter(None, [self._postprocess_parse_float(x) for x in re.finditer(re_float, x)]))
            if len(parsed) == 1 and isinstance(parsed[0], str):
                parsed = sign + parsed[0]
                parsed = self._preprocess_parse_float(parsed)
            else:
                return np.nan
        return parsed

    def parse_int(self, x: str | int | float) -> np.nan | int:
        try:
            return int(str(x).split(".")[0])
        except ValueError:
            return None

    def parse_string(self, x: str) -> None | str:
        x = str(x).replace("\n", " ").replace("\r", "").replace("\t", "").replace("\\", "").strip()
        x = " ".join(str(x).split())
        if x and x[0] == "'":
            x = x[1:]
        if not x:
            return None
        return x

    def parse_bool(self, x: str) -> bool:
        if str(x).strip().lower() == "true":
            return True
        if str(x).strip().lower() == "false":
            return False
        return np.nan

    def parse_string_list(self, x: str) -> List[str]:
        """Coerce a column, which should contain a list of strings, from literal to actual."""
        if not isinstance(x, (str, list)):
            # If it's not already a list, then it needs to be a list stored as a string
            raise TypeError
        if isinstance(x, str):
            x = ast.literal_eval(x)
        x = [str(t).strip() if not pd.isna(t) else None for t in x]
        if not x:
            return None
        return x
