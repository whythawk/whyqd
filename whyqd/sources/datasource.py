# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pandas as pd
import polars as pl

from whyqd.parsers.format import FormatParser
from whyqd.reading.conformance import ConformanceParser
from whyqd.sources.arrow import ArrowParser
from whyqd.sources.csv import CsvParser
from whyqd.sources.diagnosis import DiagnosisParser
from whyqd.sources.excel import ExcelParser
from whyqd.sources.fingerprint import FingerprintParser
from whyqd.sources.location import LocationParser
from whyqd.sources.pdf import PdfParser
from whyqd.sources.profile import ProfileParser
from whyqd.sources.reader import Reader
from whyqd.sources.row_key import RowKeyParser
from whyqd.sources.table import TableParser
from whyqd.models import (
    ChecksumModel,
    ColumnModel,
    DataSourceModel,
    DataSourceAttributeModel,
    DialectModel,
    FindingModel,
    ReportModel,
)
from whyqd.dtypes import ChecksumContent, MimeType, FieldType

if TYPE_CHECKING:
    from whyqd.core.schema import SchemaDefinition
    from whyqd.sources.v1 import V1ChecksumParser


class DataSourceParser:
    """A file as a data source: found, read through its format's reader as its dialect says, described, diagnosed,
    and verified; and a transform's saved output described as 1.x described it."""

    # pandas' names for the dtypes a frame's column is recorded as a `number` by
    PANDAS_NUMBERS: ClassVar[frozenset[str]] = frozenset({"float64", "int64", "Float64", "Int64"})

    def __init__(self):
        self.definition_formats = FormatParser()
        self.diagnoses = DiagnosisParser()
        self.fingerprints = FingerprintParser()
        self.location = LocationParser()
        self.profiles = ProfileParser()
        self._v1 = None
        self.tables = TableParser()
        self.row_key = RowKeyParser()
        arrow, excel = ArrowParser(), ExcelParser()
        self.readers: dict[MimeType, Reader] = {
            MimeType.CSV: CsvParser(),
            MimeType.PARQUET: arrow,
            MimeType.FEATHER: arrow,
            MimeType.XLS: excel,
            MimeType.XLSX: excel,
            MimeType.PDF: PdfParser(),
        }

    def get(
        self,
        *,
        source: str | Path | DataSourceModel,
        mimetype: str | MimeType | None = None,
        directory: str | Path | None = None,
        **settings,
    ) -> pd.DataFrame:
        """A data source's table, read by its `dialect`, every cell as its text, keyed by `__row__`.

        Parameters:
          source: The data source, or a file's path, read by the default dialect; a workbook's by path, its only sheet.
          mimetype: For a path: CSV, XLS, XLSX, Parquet, or Feather.
          directory: Where to download a source given by URI; `settings.WHYQD_DIRECTORY` where `None`.

        Raises:
          TypeError: For any other setting, since a file is read by its dialect: derive its data source, then get it by
            its model.
        """
        if settings:
            raise TypeError(
                f"`{'`, `'.join(settings)}` {'is not a setting' if len(settings) == 1 else 'are not settings'} of "
                "`get`. Derive the data source with a `dialect`, then get it by its model. [whyqd:get-settings]"
            )
        if isinstance(source, DataSourceModel):
            mime = self.get_mimetype(mimetype=source.mime)
            path = self.location.locate(source=source.path, directory=directory)
            table, _ = self.read(
                source=path, mime=mime, dialect=self.dialect(source=source), names=source.names or None
            )
            if (
                source.get_checksum(ChecksumContent.TABLE_1X) is not None
                and source.index is not None
                and table.height != source.index
            ):
                warnings.warn(
                    f"`{source.name}` reads as {table.height} rows where 1.x read {source.index}, so its rows are "
                    "numbered differently. Check any stored action that names rows. [whyqd:rows-renumbered]",
                    UserWarning,
                    stacklevel=2,
                )
            return table.to_pandas()
        path = self.location.locate(source=source, directory=directory)
        table, _ = self.read(source=path, mime=self.get_mimetype(mimetype=mimetype), dialect=DialectModel())
        return table.to_pandas()

    def set(self, *, df: pd.DataFrame, source: str | Path, mimetype: MimeType) -> None:
        """Save a frame as a file of a format, its suffix the format's.

        Parameters:
          df: The frame, saved without its index.
          source: The file's path; its suffix is replaced.
          mimetype: CSV, XLS, XLSX, Parquet, or Feather.

        Raises:
          FileExistsError: For a format with no suffix to give the file.
        """
        if not isinstance(source, Path):
            source = Path(source)
        try:
            source = source.with_suffix(f".{mimetype.name}")
        except Exception as e:
            raise FileExistsError(f"Save mimetype not supported, `{mimetype}`.") from e
        if mimetype in [MimeType.PRQ, MimeType.PARQUET]:
            df.to_parquet(path=source, engine="pyarrow", index=False)
        if mimetype in [MimeType.FTR, MimeType.FEATHER]:
            df.to_feather(path=source)
        if mimetype in [MimeType.XLS, MimeType.XLSX]:
            df.to_excel(source, index=False)
        if mimetype == MimeType.CSV:
            df.to_csv(source, index=False)

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
        return DialectModel(**self.definition_formats.dialect_1x(settings))

    def reader(self, *, mime: MimeType) -> Reader:
        """The reader of a format; every `MimeType` has one."""
        return self.readers[mime]

    def read(
        self,
        *,
        source: Path,
        mime: MimeType,
        dialect: DialectModel,
        names: list[str] | None = None,
        typed: bool = False,
    ) -> tuple[pl.DataFrame, pl.DataFrame | None]:
        """A file's table, keyed by `__row__`, and, where `typed`, each cell's stored type in the table's shape."""
        reader = self.reader(mime=mime)
        grid, types, lines, dialect = reader.grid(source=source, mime=mime, dialect=dialect)
        table, beside = self.tables.table(
            grid=grid,
            lines=lines,
            dialect=dialect,
            source=source.name,
            place=reader.PLACE,
            names=names,
            beside=[types] if typed else [],
        )
        return table, beside[0] if typed else None

    def typed_table(self, *, source: DataSourceModel) -> tuple[pl.DataFrame, pl.DataFrame]:
        """A data source's table, keyed by `__row__`, and each cell's stored type, for reading by its schema."""
        path = self.location.locate(source=source.path)
        return self.read(
            source=path,
            mime=self.get_mimetype(mimetype=source.mime),
            dialect=self.dialect(source=source),
            names=source.names or None,
            typed=True,
        )

    def schema_findings(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        dialect: DialectModel | dict | None,
        sheet: str | None,
        schema: SchemaDefinition,
    ) -> list[FindingModel]:
        """What a source schema's declared fields find in a file, every field counting as read. A file that cannot be
        read has already said so in its report, so it finds nothing here."""
        mime = self.get_mimetype(mimetype=mimetype)
        given = self.declare(dialect=dialect)
        given = given.model_copy(update={"sheet": sheet}) if sheet else given
        path = self.location.locate(source=source)
        try:
            table, types = self.read(source=path, mime=mime, dialect=given, typed=True)
        except ValueError:
            return []
        conformance = ConformanceParser()
        fields = schema.fields.get_all()
        df = conformance.source(table=table, types=types, fields=fields, missing=schema.get.missingValues, inputs={})
        conformance.settle_source(df=df, read_fields={field.name for field in fields})
        return [*conformance.faults, *conformance.warnings]

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
        path, reader = self.location.locate(source=source), self.reader(mime=mime)
        read = reader.grid(source=path, mime=mime, dialect=self.declare(dialect=dialect))
        fp0 = self.fingerprints.fp0(grid=read[0], types=read[1]) if reader.FINGERPRINTED else None
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
        coded = reader.formats(source=path, mime=mime, sheet=dialect.sheet, height=grid.height, width=grid.width)
        if coded is not None:
            beside.append(coded)
        table, (text, types, *formats) = self.tables.table(
            grid=grid, lines=lines, dialect=dialect, source=path.name, place=reader.PLACE, names=names, beside=beside
        )
        formats = formats[0] if formats else None
        checksum = self.definition_formats.checksum
        checksums = [checksum(value=self.fingerprints.byte_hash(source=path), content=ChecksumContent.BYTES)]
        if fp0 is not None:
            checksums.append(checksum(value=fp0, content=ChecksumContent.FP0))
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
        """The `fp0` of the sheet or file a data source's dialect reads, as it is now. `None` for a PDF, which has
        none."""
        mime = self.get_mimetype(mimetype=source.mime)
        reader = self.reader(mime=mime)
        if not reader.FINGERPRINTED:
            return None
        grid, types, _, _ = reader.grid(source=path, mime=mime, dialect=self.dialect(source=source))
        return self.fingerprints.fp0(grid=grid, types=types)

    @property
    def v1(self) -> V1ChecksumParser:
        """1.x's own read and hash, which the `verify-1x` extra holds, loaded when a 1.x checksum is first met.

        Raises:
          ImportError: Naming the extra, where it is not installed.
        """
        if self._v1 is None:
            try:
                from whyqd.sources.v1 import V1ChecksumParser
            except ImportError as e:
                raise ImportError("Verifying a 1.x checksum needs the extra: pip install whyqd[verify-1x]") from e
            self._v1 = V1ChecksumParser()
        return self._v1

    def verify(self, *, source: DataSourceModel, directory: str | Path | None = None) -> None:
        """Verify a data source's file: by the table 1.x read where it has that checksum, through 1.x's own read;
        otherwise by its byte hash, else by `fp0`, warning that the file was saved again with no cell changed.

        Raises:
          ImportError: Where a 1.x checksum needs the `verify-1x` extra and it is not installed.
          ValueError: Where the file is not the one its data source was derived from, or it has no checksum.
        """
        table = source.get_checksum(ChecksumContent.TABLE_1X)
        if table is not None:
            if self.v1.checksum(model=source) != table:
                raise ValueError(
                    f"`{source.name}` has changed: its table is not the one 1.x read when its data source was "
                    "derived. Find the file it was derived from, or derive it again. [whyqd:source-changed]"
                )
            return
        hashed, fp0 = source.get_checksum(ChecksumContent.BYTES), source.get_checksum(ChecksumContent.FP0)
        if hashed is None and fp0 is None:
            raise ValueError(
                f"`{source.path}` has no checksum whyqd can verify. Derive its data source again to give it one. "
                "[whyqd:checksum-none]"
            )
        path = self.location.locate(source=source.path, directory=directory)
        if hashed is not None and self.fingerprints.byte_hash(source=path) == hashed:
            return
        if fp0 is None or self.fingerprint(source=source, path=path) != fp0:
            raise ValueError(
                f"`{source.name}` has changed: its cells are not those its data source was derived from. Find the file "
                "it was derived from, or derive it again from this one. [whyqd:source-changed]"
            )
        warnings.warn(
            f"`{source.name}` was saved again: the file's bytes differ, but its cells (`fp0`) do not. "
            "[whyqd:source-saved-again]",
            UserWarning,
            stacklevel=2,
        )

    def checksums_beside_1x(self, *, source: DataSourceModel) -> list[ChecksumModel]:
        """The byte hash and `fp0` a data source verified through 1.x's read does not yet hold, so that once saved it
        verifies without the extra. No `fp0` for one read with pandas' `attributes`, which has no dialect to parse
        its grid by."""
        path = self.location.locate(source=source.path)
        found = {ChecksumContent.BYTES: self.fingerprints.byte_hash(source=path)}
        if not (source.attributes and source.attributes.terms):
            found[ChecksumContent.FP0] = self.fingerprint(source=source, path=path)
        return [
            ChecksumModel(**self.definition_formats.checksum(value=value, content=content))
            for content, value in found.items()
            if value is not None and source.get_checksum(content) is None
        ]

    def derive_sheets(
        self,
        *,
        source: Path | str,
        mime: MimeType,
        dialect: DialectModel | dict | list[DialectModel | dict] | None = None,
        names: list[str] | dict[str, list[str]] | None = None,
    ) -> tuple[DataSourceModel | list[DataSourceModel], pl.DataFrame | list[pl.DataFrame]]:
        """A workbook's data sources, one a sheet, every sheet read and a hidden one flagged, and their tables.

        Each sheet is its own table, with its own dialect, names, and `fp0`. A list of dialects names each one's
        `sheet`, a sheet named by none taking the defaults; or names none, giving one a sheet in workbook order. `names`
        maps a sheet to its names, or, for a workbook of one sheet, is that sheet's names.

        Raises:
          ValueError: For a dialect or names given for a sheet the workbook does not have, or dialects that cannot be
            matched to its sheets.
        """
        path = self.location.locate(source=source)
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
        models, tables = zip(
            *(
                self.model(
                    source=source,
                    path=path,
                    mime=mime,
                    read=reads[name],
                    names=names.get(name),
                    fp0=self.fingerprints.fp0(grid=reads[name][0], types=reads[name][1]),
                    hidden=hidden,
                )
                for name, hidden in sheets
            ),
            strict=True,
        )
        return (models[0], tables[0]) if len(models) == 1 else (list(models), list(tables))

    def sheet_dialects(
        self, *, dialect: DialectModel | dict | list[DialectModel | dict] | None, sheets: list[str], source: Path | str
    ) -> dict[str, DialectModel]:
        """Each sheet's dialect, by the rule `derive_sheets` gives: by the sheet each names, the defaults for a sheet
        named by none; or, where none names a sheet, one a sheet in workbook order.

        Raises:
          ValueError: For dialects some of which name a sheet, unnamed dialects other than one a sheet, or a sheet the
            workbook does not have.
        """
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
            raise ValueError(
                f"`{Path(source).name}` has dialects naming a `sheet` and dialects naming none. Name every dialect's "
                "`sheet`, or none. [whyqd:dialects-named]"
            )
        by_name = {d.sheet: d for d in named}
        self.check_sheets(given=by_name, sheets=sheets, setting="dialect", source=source)
        return {name: by_name.get(name, DialectModel()) for name in sheets}

    def check_sheets(self, *, given: dict, sheets: list[str], setting: str, source: Path | str) -> None:
        """Refuse a `setting` given by sheet for a sheet the workbook does not have, naming those it has."""
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

        Parameters:
          source: The file's path or URI.
          mimetype: CSV, XLS, XLSX, Parquet, Feather, or PDF.
          dialect: How the file is written, so it can be read; for a workbook, one a sheet (`derive_sheets`).
          names: One name per column; for a workbook, by sheet.

        Raises:
          TypeError: For `header` or any reader's keyword, naming the dialect's settings to declare instead.
        """
        if settings:
            raise TypeError(
                f"`{'`, `'.join(settings)}` {'is a pandas setting' if len(settings) == 1 else 'are pandas settings'}, "
                "which whyqd no longer reads. Declare the file in `dialect`, and its column names in `names`. "
                "[whyqd:derive-settings]"
            )
        mimetype = self.get_mimetype(mimetype=mimetype)
        if self.reader(mime=mimetype).WORKBOOK:
            return self.derive_sheets(source=source, mime=mimetype, dialect=dialect, names=names)
        return self.derive(source=source, mime=mimetype, dialect=dialect, names=names)

    def diagnose(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        dialect: DialectModel | dict | None = None,
        propose: bool = False,
    ) -> list[ReportModel]:
        """How a file reads under a dialect, and what was found there: one report, or one a sheet of a workbook, or only
        the sheet the dialect names. A file that cannot be read gives a report saying so, rather than raising.

        Raises:
          ValueError: For a declaration whyqd cannot read, or a format it does not: neither is a fault in the file.
          FileNotFoundError: For a file that is not there.
        """
        mime = self.get_mimetype(mimetype=mimetype)
        given, path, reader = self.declare(dialect=dialect), self.location.locate(source=source), self.reader(mime=mime)
        if not reader.WORKBOOK:
            return [self.diagnoses.report(source=path, mime=mime, reader=reader, given=given, propose=propose)]
        try:
            sheets = reader.sheets(source=path)
        except ValueError as e:
            return [self.diagnoses.refused(source=path, mime=mime, reader=reader, error=e)]
        if given.sheet is not None:
            sheets = [(given.sheet, dict(sheets).get(given.sheet, False))]
        return [
            self.diagnoses.report(
                source=path, mime=mime, reader=reader, given=given, sheet=sheet, hidden=hidden, propose=propose
            )
            for sheet, hidden in sheets
        ]

    def get_source_data_model(
        self, *, df: pd.DataFrame, source: Path | str, mimetype: str | MimeType
    ) -> DataSourceModel:
        """The data source of a transform's output, from the frame it was saved from, with its `table-1x` checksum.

        Parameters:
          df: The output, as saved.
          source: Where it was saved.
          mimetype: The format it was saved as.
        """
        columns = self.get_header_columns(df=df)
        return DataSourceModel(
            path=str(source),
            mime=self.get_mimetype(mimetype=mimetype),
            columns=columns,
            preserve=[c.name for c in columns if c.dtype == "string"],
            checksums=[self.definition_formats.checksum(value=self.v1.table(df=df), content=ChecksumContent.TABLE_1X)],
            index=df.shape[0],
            attributes=DataSourceAttributeModel({}),
        )

    def get_header_columns(self, *, df: pd.DataFrame) -> list[ColumnModel]:
        """A frame's columns, each typed `number` where pandas holds it as one of `PANDAS_NUMBERS`, else `string`, a date
        column included, as 1.x recorded them."""
        return [
            ColumnModel(name=k, dtype=FieldType.NUMBER if str(v) in self.PANDAS_NUMBERS else FieldType.STRING)
            for k, v in df.dtypes.items()
        ]

    def get_mimetype(self, mimetype: str | MimeType) -> MimeType:
        """A format by its name (`CSV`, `PRQ`) or its media type (`text/csv`).

        Raises:
          ValueError: For a format whyqd does not read, naming those it does.
        """
        if isinstance(mimetype, MimeType):
            return mimetype
        if isinstance(mimetype, str):
            try:
                return MimeType.value_of(mimetype)
            except ValueError:
                pass
            try:
                return MimeType(mimetype)
            except ValueError:
                pass
        raise ValueError(
            f"whyqd does not read `{mimetype}` files. It reads {', '.join(sorted({m.name for m in self.readers}))}. "
            "[whyqd:format-unknown]"
        )
