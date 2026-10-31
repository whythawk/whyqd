# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import List, Union, Type, TYPE_CHECKING
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import numpy as np
import re
import ast

import polars as pl

from whyqd.parsers.arrow_reader import ArrowParser
from whyqd.parsers.core import CoreParser
from whyqd.parsers.csv_reader import CsvParser
from whyqd.parsers.excel_reader import ExcelParser
from whyqd.parsers.fingerprint import FingerprintParser
from whyqd.parsers.pdf_reader import PdfParser
from whyqd.parsers.profile import ProfileParser
from whyqd.parsers.row_key import RowKeyParser
from whyqd.parsers.table import TableParser
from whyqd.parsers.v1 import V1ChecksumParser
from whyqd.models import ColumnModel, DataSourceModel, DataSourceAttributeModel, DialectModel
from whyqd.dtypes import ChecksumContent, MimeType, FieldType

if TYPE_CHECKING:
    from whyqd.core import SchemaDefinition


class DataSourceParser:
    """Get, review and restructure tabular source data."""

    # pandas' names for the dtypes a frame's column is recorded as a `number` by
    NUMBERS = {"float64", "int64", "Float64", "Int64"}

    def __init__(self):
        self.core = CoreParser()
        self.fingerprints = FingerprintParser()
        self.profiles = ProfileParser()
        self.v1 = V1ChecksumParser()
        self.tables = TableParser()
        self.row_key = RowKeyParser()
        arrow, excel = ArrowParser(), ExcelParser()
        self.readers = {
            MimeType.CSV: CsvParser(),
            MimeType.PARQUET: arrow,
            MimeType.PRQ: arrow,
            MimeType.FEATHER: arrow,
            MimeType.FTR: arrow,
            MimeType.XLS: excel,
            MimeType.XLSX: excel,
            MimeType.PDF: PdfParser(),
        }

    ###################################################################################################
    ### TABULAR DATA READERS AND WRITERS
    ###################################################################################################

    def get(
        self,
        *,
        source: str | Path | DataSourceModel,
        mimetype: str | MimeType | None = None,
        directory: str | Path | None = None,
        **settings,
    ) -> pd.DataFrame:
        """A data source's table, read by its `dialect`, every cell as its text, keyed by `__row__`.

        Parameters
        ----------
        source: str | Path | DataSourceModel
            The data source, or a file's path, read by the default dialect; a workbook's by path, its only sheet.
        mimetype: str | MimeType | None, default None
            For a path: CSV, XLS, XLSX, Parquet, or Feather.
        directory: str | Path | None, default None
            Where to download a source given by URI. Default will be from `settings`.

        Raises
        ------
        TypeError
            For any other setting, since a file is read by its dialect: derive its data source, then get it by its model.

        Returns
        -------
        DataFrame
        """
        if settings:
            raise TypeError(
                f"`{'`, `'.join(settings)}` {'is not a setting' if len(settings) == 1 else 'are not settings'} of "
                "`get`. Derive the data source with a `dialect`, then get it by its model. [whyqd:get-settings]"
            )
        if isinstance(source, DataSourceModel):
            mime = self.get_mimetype(mimetype=source.mime)
            path = self.locate(source=source.path, directory=directory)
            table, _ = self.read(
                source=path, mime=mime, dialect=self.dialect(source=source), names=source.names or None
            )
            if (
                source.get_checksum(ChecksumContent.TABLE_1X) is not None
                and source.index is not None
                and table.height != source.index
            ):
                self.core.show_warning(
                    f"`{source.name}` reads as {table.height} rows where 1.x read {source.index}, so its rows are "
                    "numbered differently. Check any stored action that names rows. [whyqd:rows-renumbered]"
                )
            return table.to_pandas()
        path = self.locate(source=source, directory=directory)
        table, _ = self.read(source=path, mime=self.get_mimetype(mimetype=mimetype), dialect=DialectModel())
        return table.to_pandas()

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
        validate = {"matched": [], "unmatched": [], "coerced": []}
        columns = [c for c in self.get_header_columns(df=df) if not self.row_key.is_part(c.name)]
        for c in columns:
            prospect = schema.fields.get(name=c.name)
            if prospect:
                try:
                    if c.dtype == prospect.dtype:
                        validate["matched"].append(c.name)
                    else:
                        # Try coerce the column to the type
                        df[c.name] = self.coerce_column_to_dtype(column=pd.Series(df[c.name].to_numpy(), index=df.index), coerce=prospect.dtype)
                        validate["coerced"].append(c.name)
                    df[c.name] = pd.Series(df[c.name].to_numpy(), index=df.index).astype(FieldType(prospect.dtype).astype)
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

    ###################################################################################################
    ### DATA MODEL SCHEMA DERIVATION AND WRITER UTILITIES
    ###################################################################################################

    def locate(self, *, source: str | Path, directory: str | Path | None = None) -> Path:
        """The local path of a source, downloading one given by URI."""
        if self.core.check_uri(source=source):
            source = self.core.download_uri_source(source=source, directory=directory)
        if not self.core.check_source(source=source):
            raise FileNotFoundError(f"No file at `{source}`. [whyqd:source-missing]")
        return Path(source)

    def declare(self, *, dialect: DialectModel | dict | None) -> DialectModel:
        """A dialect as the wrangler declares it, refusing a setting whyqd does not know, naming those it does."""
        if dialect is None:
            return DialectModel()
        if isinstance(dialect, DialectModel):
            return dialect
        known = [k for k in DialectModel.model_fields if k != "encodingStep"]
        unknown = [k for k in dialect if k not in known]
        if unknown:
            raise ValueError(
                f"`{'`, `'.join(unknown)}` {'is not a setting' if len(unknown) == 1 else 'are not settings'} whyqd "
                f"reads a file by. A `dialect`'s settings are {', '.join(known)}. [whyqd:dialect-unknown]"
            )
        return DialectModel(**dialect)

    def dialect(self, *, source: DataSourceModel) -> DialectModel:
        """The dialect a data source is read by: its own, or, for a 1.x data source built without one, the one that
        reads its rows as 1.x read them (`FormatParser.dialect_1x`). Its `attributes` were pandas' keywords, which no
        dialect holds, so a data source with any is refused.
        """
        if source.dialect is not None:
            return source.dialect
        settings = {"header": source.header, "sheet_name": source.sheet_name}
        if source.attributes and source.attributes.terms:
            raise ValueError(
                f"`{source.name}` was read in 1.x with pandas' `{'`, `'.join(source.attributes.terms)}`, which whyqd "
                "no longer reads. Derive it again with a `dialect`. [whyqd:attributes-1x]"
            )
        return DialectModel(**self.core.formats.dialect_1x(settings))

    def reader(self, *, mime: MimeType) -> CsvParser | ExcelParser | ArrowParser | PdfParser:
        if mime not in self.readers:
            raise ValueError(
                f"whyqd does not read `{mime.value}` files. It reads {', '.join(sorted({m.name for m in self.readers}))}. "
                "[whyqd:format-unknown]"
            )
        return self.readers[mime]

    def read(
        self, *, source: Path, mime: MimeType, dialect: DialectModel, names: list[str] | None = None
    ) -> tuple[pl.DataFrame, DialectModel]:
        """A file's table, keyed by `__row__`, and its dialect with what the read settled recorded."""
        reader = self.reader(mime=mime)
        grid, _, lines, dialect = reader.grid(source=source, mime=mime, dialect=dialect)
        table, _ = self.tables.table(grid=grid, lines=lines, dialect=dialect, names=names, place=reader.PLACE)
        return table, dialect

    def derive(
        self,
        *,
        source: Path | str,
        mime: MimeType,
        dialect: DialectModel | dict | None = None,
        names: list[str] | None = None,
    ) -> tuple[DataSourceModel, pl.DataFrame]:
        """A file's data source, its columns, row count, `fp0` and byte hash, and the dialect that reads it; and its
        table, as `get` would read it."""
        path = self.locate(source=source)
        read = self.reader(mime=mime).grid(source=path, mime=mime, dialect=self.declare(dialect=dialect))
        fp0 = None if mime == MimeType.PDF else self.fingerprints.fp0(sheets=[("", read[0], read[1])])
        return self.model(source=source, path=path, mime=mime, read=read, names=names, fp0=fp0)

    def model(
        self,
        *,
        source: Path | str,
        path: Path,
        mime: MimeType,
        read: tuple[pl.DataFrame, pl.DataFrame, list[int], DialectModel],
        names: list[str] | None,
        fp0: str | None,
        hidden: bool = False,
    ) -> tuple[DataSourceModel, pl.DataFrame]:
        """The data source of a grid as its reader gave it, each column profiled, and its table."""
        grid, types, lines, dialect = read
        reader = self.reader(mime=mime)
        beside = [grid, types]
        if mime == MimeType.XLSX:
            beside.append(reader.formats(source=path, sheet=dialect.sheet, height=grid.height, width=grid.width))
        table, (text, types, *formats) = self.tables.table(
            grid=grid, lines=lines, dialect=dialect, names=names, place=reader.PLACE, beside=beside
        )
        formats = formats[0] if formats else None
        checksums = [
            self.core.formats.checksum(value=self.fingerprints.byte_hash(source=path), content=ChecksumContent.BYTES)
        ]
        if fp0 is not None:
            checksums.append(self.core.formats.checksum(value=fp0, content=ChecksumContent.FP0))
        model = DataSourceModel(
            path=str(source),
            mime=mime,
            hidden=hidden or None,
            attributes=DataSourceAttributeModel({}),
            columns=[
                ColumnModel(
                    name=c,
                    profile=self.profiles.profile(
                        text=text[c], types=types[c], formats=None if formats is None else formats[c]
                    ),
                )
                for c in text.columns
            ],
            names=names or [],
            dialect=dialect,
            checksums=checksums,
            index=table.height,
        )
        return model, table

    def fingerprint(self, *, source: DataSourceModel, path: Path) -> str | None:
        """The `fp0` of a data source's file as it is now: every sheet of a workbook, or the grid its dialect parses.
        `None` for a PDF, which has none."""
        mime = self.get_mimetype(mimetype=source.mime)
        if mime == MimeType.PDF:
            return None
        reader = self.reader(mime=mime)
        if mime in (MimeType.XLS, MimeType.XLSX):
            sheets = [
                (name, *reader.grid(source=path, mime=mime, dialect=DialectModel(sheet=name))[:2])
                for name, _ in reader.sheets(source=path)
            ]
            return self.fingerprints.fp0(sheets=sheets)
        grid, types, _, _ = reader.grid(source=path, mime=mime, dialect=self.dialect(source=source))
        return self.fingerprints.fp0(sheets=[("", grid, types)])

    def verify(self, *, source: DataSourceModel, directory: str | Path | None = None) -> None:
        """Verify a data source's file by its byte hash, else by `fp0`, warning that the file was saved again with no
        cell changed.

        Raises
        ------
        ValueError
            For a data source with neither.
        AssertionError
            Where the file's cells are not those its data source was derived from.
        """
        hashed, fp0 = source.get_checksum(ChecksumContent.BYTES), source.get_checksum(ChecksumContent.FP0)
        if hashed is None and fp0 is None:
            raise ValueError(f"`{source.path}` has no checksum whyqd can verify. [whyqd:checksum-none]")
        path = self.locate(source=source.path, directory=directory)
        if hashed is not None and self.fingerprints.byte_hash(source=path) == hashed:
            return
        if fp0 is None or self.fingerprint(source=source, path=path) != fp0:
            raise AssertionError(
                f"`{source.path}` has changed: its cells are not those its data source was derived from. "
                "[whyqd:source-changed]"
            )
        self.core.show_warning(
            f"`{source.path}` was saved again: its bytes differ, but its cells (`fp0`) do not. "
            "[whyqd:source-saved-again]"
        )

    def derive_sheets(
        self,
        *,
        source: Path | str,
        mime: MimeType,
        dialect: DialectModel | dict | list[DialectModel | dict] | None = None,
        names: list[str] | dict[str, list[str]] | None = None,
    ) -> tuple[DataSourceModel | list[DataSourceModel], pl.DataFrame | list[pl.DataFrame]]:
        """A workbook's data sources, one a sheet, every sheet read and a hidden one flagged, and their tables.

        Each sheet is its own table, with its own dialect and names. A list of dialects names each one's `sheet`, a
        sheet named by none taking the defaults; or names none, giving one a sheet in workbook order. `names` maps a
        sheet to its names, or, for a workbook of one sheet, is that sheet's names.

        Raises
        ------
        ValueError
            For a dialect or names given for a sheet the workbook does not have, or dialects that cannot be matched to
            its sheets.
        """
        path = self.locate(source=source)
        reader = self.reader(mime=mime)
        sheets = reader.sheets(source=path)
        order = [name for name, _ in sheets]
        dialects = self.sheet_dialects(dialect=dialect, sheets=order, source=source)
        if isinstance(names, list):
            if len(order) != 1:
                raise ValueError(
                    f"`{Path(source).name}` has {len(order)} sheets, so give `names` by sheet: "
                    f"{{'{order[0]}': [...]}}. [whyqd:names-by-sheet]"
                )
            names = {order[0]: names}
        names = names or {}
        self.check_sheets(given=names, sheets=order, setting="names", source=source)
        reads = {
            name: reader.grid(source=path, mime=mime, dialect=dialects[name].model_copy(update={"sheet": name}))
            for name in order
        }
        fp0 = self.fingerprints.fp0(sheets=[(name, grid, types) for name, (grid, types, _, _) in reads.items()])
        models, tables = zip(
            *(
                self.model(
                    source=source, path=path, mime=mime, read=reads[name], names=names.get(name), fp0=fp0, hidden=hidden
                )
                for name, hidden in sheets
            ),
            strict=True,
        )
        return (models[0], tables[0]) if len(models) == 1 else (list(models), list(tables))

    def sheet_dialects(
        self, *, dialect: DialectModel | dict | list[DialectModel | dict] | None, sheets: list[str], source: Path | str
    ) -> dict[str, DialectModel]:
        given = [] if dialect is None else dialect if isinstance(dialect, list) else [dialect]
        given = [self.declare(dialect=d) for d in given]
        named = [d for d in given if d.sheet is not None]
        if not named:
            if given and len(given) != len(sheets):
                raise ValueError(
                    f"`{Path(source).name}` has {len(sheets)} sheets but {len(given)} dialects without a `sheet`. "
                    "Give one a sheet, in order, or name each one's `sheet`. [whyqd:dialects-count]"
                )
            return {name: given[i] if given else DialectModel() for i, name in enumerate(sheets)}
        if len(named) != len(given):
            raise ValueError("Name every dialect's `sheet`, or none. [whyqd:dialects-named]")
        by_name = {d.sheet: d for d in named}
        self.check_sheets(given=by_name, sheets=sheets, setting="dialect", source=source)
        return {name: by_name.get(name, DialectModel()) for name in sheets}

    def check_sheets(self, *, given: dict, sheets: list[str], setting: str, source: Path | str) -> None:
        if unknown := [s for s in given if s not in sheets]:
            raise ValueError(
                f"`{setting}` is given for `{'`, `'.join(unknown)}`, which `{Path(source).name}` does not have. Its "
                f"sheets are `{'`, `'.join(sheets)}`. [whyqd:sheet-given]"
            )

    def derive_data_model(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        dialect: DialectModel | dict | list[DialectModel | dict] | None = None,
        names: list[str] | dict[str, list[str]] | None = None,
        **settings,
    ) -> tuple[DataSourceModel | list[DataSourceModel], pl.DataFrame | list[pl.DataFrame]]:
        """A data source derived from a file, and its table: a workbook's one a sheet, as lists where it has several.

        Parameters
        ----------
        source: Path | str
        mimetype: str | MimeType
            CSV, XLS, XLSX, Parquet, or Feather.
        dialect: DialectModel | dict | list[DialectModel | dict] | None, default None
            How the file is written, so it can be read; for a workbook, one a sheet (`derive_sheets`).
        names: list[str] | dict[str, list[str]] | None, default None
            One name per column; for a workbook, by sheet.

        Raises
        ------
        TypeError
            For `header` or any reader's keyword, naming the dialect's settings to declare instead.
        """
        if settings:
            raise TypeError(
                f"`{'`, `'.join(settings)}` {'is a pandas setting' if len(settings) == 1 else 'are pandas settings'}, "
                "which whyqd no longer reads. Declare the file in `dialect`, and its column names in `names`. "
                "[whyqd:derive-settings]"
            )
        mimetype = self.get_mimetype(mimetype=mimetype)
        if mimetype in (MimeType.XLS, MimeType.XLSX):
            return self.derive_sheets(source=source, mime=mimetype, dialect=dialect, names=names)
        return self.derive(source=source, mime=mimetype, dialect=dialect, names=names)

    def get_source_data_model(self, *, df: pd.DataFrame, source: Path | str, mimetype: str | MimeType) -> DataSourceModel:
        """The data source of a transform's output, from the frame it was saved from, with its `table-1x` checksum.

        Parameters
        ----------
        df: pd.DataFrame
            The output, as saved.
        source: Path | str
            Where it was saved.
        mimetype: str | MimeType

        Returns
        -------
        DataSourceModel
        """
        columns = self.get_header_columns(df=df)
        return DataSourceModel(
            path=str(source),
            mime=self.get_mimetype(mimetype=mimetype),
            columns=columns,
            preserve=[c.name for c in columns if c.dtype == "string"],
            checksums=[self.core.formats.checksum(value=self.v1.table(df=df), content=ChecksumContent.TABLE_1X)],
            index=df.shape[0],
            attributes=DataSourceAttributeModel({}),
        )

    def get_header_columns(self, *, df: pd.DataFrame) -> List[ColumnModel]:
        """A frame's columns, each typed `number` where pandas holds it as one of `NUMBERS`, else `string`, a date
        column included, as 1.x recorded them.

        Parameters
        ----------
        df: pd.DataFrame

        Returns
        -------
        List of ColumnModel
        """
        return [
            ColumnModel(name=k, dtype=FieldType.NUMBER if str(v) in self.NUMBERS else FieldType.STRING)
            for k, v in df.dtypes.items()
        ]

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

    ###################################################################################################
    ### PANDAS TYPE PARSERS
    ###################################################################################################

    def _date_is_isoformat(self, x: str) -> bool:
        """
        Checks a string to see whether it can be coerced as an ISO-formatted date `YYYY-MM-DD`
        https://stackoverflow.com/a/61569783
        """
        try:
            # `int` formatted dates will fail with `AttributeError`
            datetime.fromisoformat(x.replace('Z', '+00:00'))
        except (ValueError, TypeError, AttributeError):
            return False
        return True

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
        # Check if already in ISO Format
        if self._date_is_isoformat(x):
            return str(x).strip()[:10]
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
                return float(re_float.match(x).group(1))
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

    def parse_string(self, x: str | None) -> str | None:
        if pd.isna(x):
            return None
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
