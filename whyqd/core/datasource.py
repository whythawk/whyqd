# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
from pydantic import Json

from whyqd.dtypes import ChecksumContent, MimeType
from whyqd.models import DataSourceModel, CitationModel, DialectModel, ReportModel
from whyqd.core.base import BaseDefinition

if TYPE_CHECKING:
    import pandas as pd

    from whyqd.core.schema import SchemaDefinition


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

    Examples:
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

            As always *look* at your data and test before implementing in code. Each sheet's data source names its
            sheet in `dialect.sheet`.

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
            self.model = self.definitions.build(kind=DataSourceModel, source=schema, model=self.model)

    def get_data(self, *, refresh: bool = False) -> pd.DataFrame | None:
        """Get the data source's table as a pandas dataframe.

        Parameters:
          refresh: Force an update of the dataframe if there have been attribute changes.

        Returns:
          A dataframe, or none.
        """
        if self.model and (refresh or self.data is None or self.data.empty):
            self.data = self.reader.get(source=self.model)
        return self.data

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
                   whyqd's ladder and recorded. For a workbook, a list, each naming its `sheet`, or one a sheet in
                   order.
          names: One name per column, for a file with no header row or a header over several rows; for a workbook, a
                 mapping of sheet to names. Names past the file's last filled column are added as empty columns;
                 columns past the last name are named by position, with a warning.
          settings: Refused, naming the dialect: `header` and pandas' keywords are no longer read.

        Returns:
          The data source, or one a sheet of a workbook.
        """
        self.model, table = self.reader.derive_data_model(
            source=source, mimetype=mimetype, dialect=dialect, names=names, **settings
        )
        # Held so the first `get_data` need not read the file again
        self.data = None if isinstance(self.model, list) else table.to_pandas()
        return self.model

    def diagnose(
        self,
        *,
        source: Path | str,
        mimetype: str | MimeType,
        dialect: DialectModel | dict | None = None,
        propose: bool = False,
        schema: SchemaDefinition | None = None,
    ) -> list[ReportModel]:
        """How whyqd read a file and what it found there, to review before going on. Nothing is applied, and this
        definition does not change: declare what you decide in `derive_model`'s `dialect`.

        With a `schema`, the report also reads each field it declares, so a declaration can be checked before any
        crosswalk exists. A cell that does not fit is a fault here, and stops nothing.

        A report says which setting took which value, and whether you declared it. A fault is a file that cannot be read
        as written, or was read with a loss; a fact is something the file holds, with no claim of what it means, for the
        crosswalk to act on. A file that cannot be read gives a report saying why, rather than raising.

        Parameters:
          source:  Source filename.
          mimetype:  **whyqd** supports `xls`, `xlsx`, `csv`, `parquet`, `feather`, and, with its extra, `pdf`.
          dialect: How the file is written, as in `derive_model`. For a workbook, one naming its `sheet` reports on that
                   sheet alone; otherwise each sheet reads by it, and has its own report.
          propose: Also propose settings that would read past a fault, each with its evidence.
          schema: A source schema whose declared fields to read against the file.

        Returns:
          One ReportModel, or one a sheet of a workbook.

        Examples:
          ```python
          import whyqd as qd

          report = qd.DataSourceDefinition().diagnose(source=DATASOURCE_PATH, mimetype=MIMETYPE)[0]
          print(report.preview)
          for finding in report.findings:
              print(finding)
          ```
        """
        reports = self.reader.diagnose(source=source, mimetype=mimetype, dialect=dialect, propose=propose)
        if schema is not None:
            for report in reports:
                report.findings += self.reader.schema_findings(
                    source=source, mimetype=mimetype, dialect=dialect, sheet=report.sheet, schema=schema
                )
        return reports

    def validate(self) -> bool:
        """Verify the source data against the data source's checksum.

        A checksum of the table as 1.x read it (`table-1x`) verifies through 1.x's own read, which needs the
        `verify-1x` extra. Once it verifies, the `fp0` of what its dialect reads and the file's byte hash are added
        beside it. A data source without one verifies by its byte hash, else by `fp0`, warning that the file was saved
        again with no cell changed.

        Raises:
          ImportError: If a 1.x checksum needs verifying and the `verify-1x` extra is not installed.
          ValueError: If the file is not the one the data source was derived from, or there is no model.

        Returns:
          True if every data source verifies.
        """
        if not self.model:
            raise ValueError(
                "This data source is empty, so there is nothing to verify. Derive it first. [whyqd:definition-empty]"
            )
        models = self.model if isinstance(self.model, list) else [self.model]
        for m in models:
            self.reader.verify(source=m)
            if m.get_checksum(ChecksumContent.TABLE_1X) is not None:
                m.checksums += self.reader.checksums_beside_1x(source=m)
        return True

    def get_citation(self) -> dict[str, str | dict[str, str]] | list[dict[str, str | dict[str, str]]]:
        """Get the citation as a dictionary, or one a cited sheet of a workbook.

        Raises:
          ValueError: If no citation has been declared or the build is incomplete.

        Returns:
          A dictionary conforming to the CitationModel, or a list of them.
        """
        if not isinstance(self.model, list):
            return super().get_citation()
        return [
            m.citation.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)
            for m in self.model
            if m.citation
        ]

    def set_citation(self, *, citation: CitationModel, index: int | None = None) -> None:
        """Update or create the citation.

        Parameters:
          citation: A dictionary conforming to the CitationModel.
          index: For a workbook, the sheet to cite, counted from 0; by default, every sheet.
        """
        # Create a temporary CitationModel
        if not isinstance(self.model, list):
            super().set_citation(citation=citation)
        elif index is not None:
            self.model[index].citation = self.definitions.build(
                kind=CitationModel, source=citation, model=self.model[index].citation
            )
        else:
            for index in range(len(self.model)):
                self.model[index].citation = self.definitions.build(
                    kind=CitationModel, source=citation, model=self.model[index].citation
                )

    def get_json(self, hide_uuid: bool = False, format: str | None = None) -> Json | list[Json] | None:
        """Get the json model, or one per sheet.

        Parameters:
          hide_uuid: Hide all UUIDs in the nested JSON output. Mostly useful for validation assertions where the only
                     differences between sources are the UUIDs.
          format: The definition format to write, one of `settings.FORMAT_VERSIONS` (`whyqd.config.settings`).
                  Defaults to the current one.

        Returns:
          Json-conforming output, a list of them, or None.
        """
        if not isinstance(self.model, list):
            return super().get_json(hide_uuid=hide_uuid, format=format)
        formats = self.definitions.formats
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
          format: The definition format to write, one of `settings.FORMAT_VERSIONS` (`whyqd.config.settings`).
                  Defaults to the current one.

        Returns:
          Boolean True if saved.
        """
        if not isinstance(self.model, list):
            if not filename:
                filename = "".join(self.model.name.split(".")[:-1] + [f".{self.model_name}"])
            return super().save(
                directory=directory, filename=filename, created_by=created_by, hide_uuid=hide_uuid, format=format
            )
        directory = self.definitions.directory(directory)
        if not filename:
            filename = f"{self.model.name}.{self.model_name}"
        if filename.split(".")[-1] != self.model_name:
            filename += f".{self.model_name}"
        models = self.get_json(hide_uuid=hide_uuid, format=format)
        for i, model in enumerate(models):
            filename = "".join(self.model[i].name.split(".")[:-1] + [f".{self.model_name}"])
            self.definitions.save(text=model, path=directory / filename)
        return True
