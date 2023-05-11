from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
from pydantic import Json
import json

from whyqd.dtypes import MimeType
from whyqd.models import DataSourceModel, CitationModel
from whyqd.parsers import DataSourceParser
from whyqd.core.base import BaseDefinition

if TYPE_CHECKING:
    import modin.pandas as pd


class DataSourceDefinition(BaseDefinition):
    """Create and manage a data source schema.

    !!! tip "Strategy"
        Guidance on how to use this definition is in the strategies section on
        [DataSource Strategies](/strategies/datasource).

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
        self.reader = DataSourceParser()
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
        header: int | list[int | None] | None = 0,
        **attributes,
    ) -> DataSourceModel | list[DataSourceModel]:
        """Derive a data model schema (or list) from a data source. All columns will be coerced to `string` type to
        preserve data quality even though this is far less efficient.

        Parameters:
          source:  Source filename.
          mimetype:  Pandas can read a diversity of mimetypes. **whyqd** supports `xls`, `xlsx`, `csv`, `parquet` and `feather`.
          header:  Row (0-indexed) to use for the column labels of the parsed DataFrame. If there are multiple sheets, then
                    a list of integers should be provided. If `header` is `None`, row 0 will be treated as values and a
                    set of field names will be generated indexed to the number of data columns.
          attributes: dict of specific `mimetype` related Pandas attributes. Use sparingly.

        Returns:
          List of DataSourceModel, or DataSourceModel
        """
        self.model = self.reader.derive_data_model(source=source, mimetype=mimetype, header=header, **attributes)

    #########################################################################################
    # VALIDATION UTILITIES
    #########################################################################################

    def validate(self) -> bool:
        """Validate that all required fields are returned from the crosswalk."""
        if not self.model:
            raise ValueError(f"{self.model_name.title()} model does not exist.")
        models = self.model
        if not isinstance(self.model, list):
            models = [models]
        for m in models:
            attributes = {}
            if m.attributes:
                attributes |= m.attributes.terms
            vmod = self.reader.derive_data_model(
                source=m.path, mimetype=m.mime, sheet_name=m.sheet_name, header=m.header, **attributes
            )
            try:
                assert vmod.checksum == m.checksum
            except AssertionError:
                raise AssertionError(f"{self.model_name.title()} model checksum does not match derived checksum.")
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
            m.citation.dict(by_alias=True, exclude_defaults=True, exclude_none=True) for m in self.model if m.citation
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

    def get_json(self, hide_uuid: bool = False) -> Json | None:
        """Get the json model.

        Parameters:
          hide_uuid: Hide all UUIDs in the nested JSON output. Mostly useful for validation assertions where the only
                     differences between sources are the UUIDs.

        Returns:
          Json-conforming output, or None.
        """
        if not isinstance(self.model, list):
            return super().get_json(hide_uuid=hide_uuid)
        response = []
        for model in self.model:
            if not hide_uuid:
                response.append(model.json(by_alias=True, exclude_defaults=True, exclude_none=True))
            else:
                json.dumps(self.exclude_uuid(model=model))
        return response

    def save(
        self,
        directory: str | None = None,
        filename: str | None = None,
        created_by: str | None = None,
        hide_uuid: bool = False,
    ) -> bool:
        """Save model as a json file.

        Parameters:
          directory:  Defaults to working directory
          filename:  Defaults to model name
          created_by:  Declare the model creator/updater
          hide_uuid:  Hide all UUIDs in the nested JSON output.

        Returns:
          Boolean True if saved.
        """
        if not isinstance(self.model, list):
            if not filename:
                filename = "".join(self.model.name.split(".")[:-1] + [f".{self.model_name}"])
            return super().save(directory=directory, filename=filename, created_by=created_by, hide_uuid=hide_uuid)
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
        models = self.get_json(hide_uuid=hide_uuid)
        for i, model in enumerate(models):
            filename = "".join(self.model[i].name.split(".")[:-1] + [f".{self.model_name}"])
            path = directory / filename
            self.core.save_file(data=model, source=path)
        return True
