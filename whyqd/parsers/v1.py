# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pathlib import Path
import hashlib

import numpy as np
import pandas as pd

from whyqd.dtypes import MimeType
from whyqd.models import DataSourceModel
from whyqd.parsers.core import CoreParser


class V1ChecksumParser:
    """whyqd 1.x's data checksum: the table as 1.x reads it, printed by pandas, hashed with BLAKE2b-512.

    Its result depends on how pandas reads and prints a table, so this keeps 1.x's read unchanged, and with it both
    ways 1.x checked a table: a data source derived again from its file (`checksum`), and a file read with its stored
    settings (`read`), as a transform checks its source and destination. It verifies 1.x checksums and makes no new
    ones.

    Example:
      ```python
      from whyqd.parsers.v1 import V1ChecksumParser

      V1ChecksumParser().checksum(model=datasource.get) == datasource.get.get_checksum("table-1x")
      ```
    """

    def __init__(self) -> None:
        self.core = CoreParser()

    def checksum(self, *, model: DataSourceModel) -> str:
        """Derive a data source again from its file, with its 1.x settings (`header`, `sheet_name`, `attributes`),
        and return its checksum.

        Parameters:
          model: A data source as 1.x derived it.

        Returns:
          The checksum of the table, as 1.x wrote it.
        """
        attributes = model.attributes.terms if model.attributes else {}
        path, header, sheet_name = model.path, model.header, model.sheet_name
        if header is None:
            df = self.read(source=path, mimetype=model.mime, sheet_name=sheet_name, nrows=50, **attributes)
            names = []
            if not ((isinstance(df, dict) and not df) or df.empty):
                names = [f"column_{i}" for i in range(len(df.columns))]
        else:
            nrows = header + 1 if header > 1 else 1
            df = self.read(
                source=path, mimetype=model.mime, sheet_name=sheet_name, header=header, nrows=nrows, **attributes
            )
            names = df.columns.tolist()
        if header is None or header != 0:
            df = self.read(
                source=path,
                mimetype=model.mime,
                names=names,
                preserve=names,
                sheet_name=sheet_name,
                header=None,
                **attributes,
            )
        else:
            df = self.read(source=path, mimetype=model.mime, preserve=names, sheet_name=sheet_name, **attributes)
        return self.table(df=df)

    def table(self, *, df: pd.DataFrame) -> str:
        """Return the checksum of a table: pandas' printed table, as text, hashed.

        Parameters:
          df: The table. Array cells are changed to lists in place.

        Returns:
          The checksum.
        """
        for column in df.columns:
            if isinstance(df.iloc[0][column], np.ndarray):
                df[column] = df[column].apply(lambda x: x.tolist())
        df_string = df.astype("string").astype("string").to_string(index=False).encode("utf-8")
        return hashlib.blake2b(df_string).hexdigest()

    def read(
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
    ) -> dict[str, pd.DataFrame] | pd.DataFrame:
        """Read a file as 1.x did, with pandas' keywords as 1.x's `attributes`.

        Parameters:
          source: A path or URI, or a data source, whose settings then replace the others.
          mimetype: CSV, XLS, XLSX, Feather, or Parquet.
          header: The header row, counted from 0.
          preserve: Columns read as text, or `True` for every column. CSV and Excel only.
          names: Column names, for a file without a header row. CSV and Excel only.
          nrows: The number of rows to read.
          sheet_name: The sheet to read; by default every sheet that is not empty.
          directory: Where a remote source is saved.
          attributes: pandas' own keywords for the reader.

        Returns:
          A dataframe, or one for each sheet.
        """
        kwargs = {} | attributes
        if isinstance(source, DataSourceModel):
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
            source = self.core.download_uri_source(source=source, directory=directory)
        if not self.core.check_source(source=source):
            raise FileNotFoundError(f"Source at `{source}` not found.")
        if not isinstance(mimetype, MimeType):
            try:
                mimetype = MimeType.value_of(mimetype)
            except ValueError:
                mimetype = MimeType(mimetype)
        if mimetype in [MimeType.PRQ, MimeType.PARQUET]:
            return self._read_parquet(source=source, nrows=nrows, **kwargs)
        if mimetype in [MimeType.FTR, MimeType.FEATHER]:
            return pd.read_feather(source, **kwargs)
        if preserve:
            if isinstance(preserve, bool):
                kwargs["dtype"] = pd.StringDtype()
            else:
                if not isinstance(preserve, list):
                    preserve = [preserve]
                kwargs["dtype"] = {k: pd.StringDtype() for k in preserve}
        kwargs["header"] = header
        if names:
            kwargs["header"] = None
            kwargs["names"] = names
        if nrows:
            kwargs["nrows"] = nrows
        if mimetype in [MimeType.XLS, MimeType.XLSX]:
            kwargs["sheet_name"] = sheet_name
            # The engines 1.x read with, named so a change of pandas' default leaves the read, and its checksums, alone
            kwargs.setdefault("engine", "xlrd" if mimetype == MimeType.XLS else "openpyxl")
            return self._read_excel(source=source, **kwargs)
        if mimetype == MimeType.CSV:
            return self._read_csv(source=source, **kwargs)
        raise FileExistsError(f"Source at `{source}` does not have a recognised mimetype `{mimetype}`.")

    def _read_excel(self, *, source: str | Path, **kwargs) -> dict[str, pd.DataFrame] | pd.DataFrame:
        # Every sheet unless one is named; empty sheets dropped, and a single sheet left returned alone
        if kwargs.get("sheet_name"):
            return pd.read_excel(source, **kwargs)
        df = pd.read_excel(source, **kwargs)
        keys = list(df.keys())
        for k in keys:
            if df[k].empty:
                del df[k]
        if len(df.keys()) == 1:
            df = df[keys[0]]
        return df

    def _read_csv(self, *, source: str | Path, **kwargs) -> pd.DataFrame:
        # 1.x drops bytes that do not decode, and guesses the delimiter with the python engine
        kwargs["encoding_errors"] = "ignore"
        kwargs["engine"] = "python"
        if not kwargs.get("nrows"):
            return pd.read_csv(source, **kwargs)
        kwargs["iterator"] = True
        kwargs["chunksize"] = 10000
        return pd.concat(pd.read_csv(source, **kwargs), ignore_index=True)

    def _read_parquet(self, *, source: str | Path, nrows: int | None = None, **kwargs) -> pd.DataFrame:
        if nrows:
            import pyarrow as pa
            from pyarrow.parquet import ParquetFile

            batch = next(ParquetFile(str(source)).iter_batches(batch_size=nrows))
            return pa.Table.from_batches([batch]).to_pandas(**kwargs)
        if "engine" not in kwargs:
            kwargs["engine"] = "pyarrow"
        return pd.read_parquet(source, **kwargs)
