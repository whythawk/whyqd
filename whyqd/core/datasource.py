# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
from pydantic import Json

from whyqd.dtypes import ChecksumContent, MimeType
from whyqd.models import ChecksumModel, DataSourceModel, CitationModel, DialectModel
from whyqd.core.base import BaseDefinition
from whyqd.config.settings import settings

if TYPE_CHECKING:
    import pandas as pd


class DataSourceDefinition(BaseDefinition):
    """Create and manage a data source schema.

    !!! tip "Strategy"
        Guidance on how to use this definition is in the strategies section on
        [DataSource Strategies](../strategies/datasource.md).

    !!! info
        **whyqd** supports any of the following file mime types:

        - `CSV`: "text/csv"
        - `XLS`: "application/vnd.ms-excel"
        - `XLSX`: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        - `PARQUET` (or `PRQ`): "application/vnd.apache.parquet"
        - `FEATHER` (or `FTR`): "application/vnd.apache.feather"

        Declare it like so:

        ```python
        MIMETYPE = "xlsx" # upper- or lower-case is fine
        ```

        Specify the mime type as a text string, uppper- or lower-case. Neither of
        [Parquet](https://parquet.apache.org/docs/overview/) or [Feather](https://arrow.apache.org/docs/python/feather.html)
        yet have official mimetypes, so this is what we're using for now.

    Parameters:
      source: A path to a json file containing a saved schema, or a dictionary conforming to the DataSourceModel.

    Example:
      Create and validate a new `DataSourceDefinition` as follows:

      ```python
      import whyqd as qd

      datasource = qd.DataSourceDefinition()
      datasource.derive_model(source=DATASOURCE_PATH, mimetype=MIMETYPE)
      datasource.save(directory=DIRECTORY)
      datasource.validate()
      ```
    """

    def __init__(self, *, source: Path | str | DataSourceModel | None = None) -> None:
        super().__init__(model_name="data")
        self.data = None
        self.set(schema=source)

    @property
    def get(self) -> DataSourceModel | list[DataSourceModel] | None:
        """Get the data source model.

        !!! warning
            If your source data are `Excel`, and that spreadsheet consists of multiple `sheets`, then **whyqd** will
            produce multiple data models which will be returned as a list. Each model will reflect the metadata for
            each sheet.

            As always *look* at your data and test before implementing in code. You should see an additional `sheet_name`
            field.

        Returns:
          Pydantic DataSourceModel as a list, a single, or None
        """
        return self.model

    def set(self, *, schema: Path | str | DataSourceModel | None = None) -> None:
        """Update or create the schema.

        Parameters:
          schema: A dictionary conforming to the DataSourceModel.
        """
        if schema:
            self.model = self.core.create_or_update_model(modelType=DataSourceModel, source=schema, model=self.model)

    def get_data(self, *, refresh: bool = False) -> pd.DataFrame | None:
        """Get a Pandas (Modin) dataframe.

        Parameters:
          refresh: Force an update of the dataframe if there have been attribute changes.

        Returns:
          A dataframe, or none.
        """
        if self.model and (refresh or self.data is None or self.data.empty):
            self.data = self.reader.get(source=self.model)
        return self.data

    #########################################################################################
    # DERIVE SCHEMA FROM TABULAR DATA
    #########################################################################################

    def derive_model(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        dialect: DialectModel | dict | list[DialectModel | dict] | None = None,
        names: list[str] | dict[str, list[str]] | None = None,
        **settings,
    ) -> DataSourceModel | list[DataSourceModel]:
        """Derive a data source from a file, or one a sheet from a workbook. Every cell is read as its text.

        Parameters:
          source:  Source filename.
          mimetype:  **whyqd** supports `xls`, `xlsx`, `csv`, `parquet` and `feather`.
          dialect: How the file is written, so it can be read: the dialect of CSV on the Web, as `DialectModel`
                   describes it. Undeclared, each setting takes its default; a CSV's encoding, undeclared, is settled by
                   whyqd's ladder and recorded. For a workbook, a list, each naming its `sheet`, or one a sheet in order.
          names: One name per column, for a file with no header row or a header over several rows; for a workbook, a
                 mapping of sheet to names.
          settings: Refused, naming the dialect: `header` and pandas' keywords are no longer read.

        Returns:
          List of DataSourceModel, or DataSourceModel
        """
        self.model = self.reader.derive_data_model(
            source=source, mimetype=mimetype, dialect=dialect, names=names, **settings
        )

    #########################################################################################
    # VALIDATION UTILITIES
    #########################################################################################

    def validate(self) -> bool:
        """Verify the source data against the data source's checksum.

        A checksum of the table as 1.x read it (`table-1x`) verifies through 1.x's own read, which needs the
        `verify-1x` extra. Once it verifies, the file's `fp0` and byte hash are added beside it. A data source without
        one verifies by its byte hash, else by `fp0`, warning that the file was saved again with no cell changed.

        Raises:
          ImportError: If a 1.x checksum needs verifying and the `verify-1x` extra is not installed.
          AssertionError: If the source data does not match its checksum.

        Returns:
          True if every data source verifies.
        """
        if not self.model:
            raise ValueError(f"{self.model_name.title()} model does not exist.")
        models = self.model
        if not isinstance(self.model, list):
            models = [models]
        for m in models:
            table = m.get_checksum(ChecksumContent.TABLE_1X)
            if table is None:
                self.reader.verify(source=m)
                continue
            try:
                from whyqd.parsers.v1 import V1ChecksumParser
            except ImportError as e:
                raise ImportError("Verifying a 1.x checksum needs the extra: pip install whyqd[verify-1x]") from e
            if V1ChecksumParser().checksum(model=m) != table:
                raise AssertionError(f"{self.model_name.title()} model checksum does not match derived checksum.")
            path = self.reader.locate(source=m.path)
            found = {ChecksumContent.BYTES: self.reader.fingerprints.byte_hash(source=path)}
            # One read with pandas' settings has no dialect to parse its grid by
            if not (m.attributes and m.attributes.terms):
                found[ChecksumContent.FP0] = self.reader.fingerprint(source=m, path=path)
            for content, value in found.items():
                if m.get_checksum(content) is None and value is not None:
                    m.checksums.append(
                        ChecksumModel(algorithm=settings.CHECKSUM_ALGORITHM, checksumValue=value, content=content)
                    )
        return True

    #########################################################################################
    # MANAGE CITATION
    #########################################################################################

    def get_citation(self) -> dict[str, str | dict[str, str]]:
        """Get the citation as a dictionary.

        Raises:
          ValueError: If no citation has been declared or the build is incomplete.

        Returns:
          A dictionary conforming to the CitationModel.
        """
        if not isinstance(self.model, list):
            return super().get_citation()
        return [
            m.citation.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True) for m in self.model if m.citation
        ]

    def set_citation(self, *, citation: CitationModel, index: int = None) -> None:
        """Update or create the citation.

        Parameters:
          citation: A dictionary conforming to the CitationModel.
          index: If there are multiple sources from the source data, provide the index (base 0) for the resource citation.
        """
        # Create a temporary CitationModel
        if not isinstance(self.model, list):
            super().set_citation(citation=citation)
        elif index:
            self.model[index].citation = self.core.create_or_update_model(
                modelType=CitationModel, source=citation, model=self.model[index].citation
            )
        else:
            for index in range(len(self.model)):
                self.model[index].citation = self.core.create_or_update_model(
                    modelType=CitationModel, source=citation, model=self.model[index].citation
                )

    #########################################################################################
    # SAVE UTILITIES FOR LISTS
    #########################################################################################

    def get_json(self, hide_uuid: bool = False, format: str | None = None) -> Json | list[Json] | None:
        """Get the json model, or one per sheet.

        Parameters:
          hide_uuid: Hide all UUIDs in the nested JSON output. Mostly useful for validation assertions where the only
                     differences between sources are the UUIDs.
          format: The definition format to write, one of `settings.FORMAT_VERSIONS` (`whyqd.config.settings`). Defaults to the current one.

        Returns:
          Json-conforming output, a list of them, or None.
        """
        if not isinstance(self.model, list):
            return super().get_json(hide_uuid=hide_uuid, format=format)
        formats = self.core.formats
        return [formats.dumps(formats.write(model=m, format=format, hide_uuid=hide_uuid)) for m in self.model]

    def save(
        self,
        directory: str | None = None,
        filename: str | None = None,
        created_by: str | None = None,
        hide_uuid: bool = False,
        format: str | None = None,
    ) -> bool:
        """Save model as a json file.

        Parameters:
          directory:  Defaults to working directory
          filename:  Defaults to model name
          created_by:  Declare the model creator/updater
          hide_uuid:  Hide all UUIDs in the nested JSON output.
          format: The definition format to write, one of `settings.FORMAT_VERSIONS` (`whyqd.config.settings`). Defaults to the current one.

        Returns:
          Boolean True if saved.
        """
        if not isinstance(self.model, list):
            if not filename:
                filename = "".join(self.model.name.split(".")[:-1] + [f".{self.model_name}"])
            return super().save(
                directory=directory, filename=filename, created_by=created_by, hide_uuid=hide_uuid, format=format
            )
        if not directory:
            directory = self.core.default_directory
        else:
            directory = self.core.check_path(directory=directory)
        if not filename:
            filename = f"{self.model.name}.{self.model_name}"
        if filename.split(".")[-1] != self.model_name:
            filename += f".{self.model_name}"
        if isinstance(directory, str):
            directory = Path(directory)
        models = self.get_json(hide_uuid=hide_uuid, format=format)
        for i, model in enumerate(models):
            filename = "".join(self.model[i].name.split(".")[:-1] + [f".{self.model_name}"])
            path = directory / filename
            self.core.save_file(data=model, source=path)
        return True
