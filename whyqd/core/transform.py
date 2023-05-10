from __future__ import annotations
from pathlib import Path

from whyqd.dtypes import MimeType
from whyqd.models import DataSourceModel, CrosswalkModel, TransformModel
from whyqd.core import CrosswalkDefinition
from whyqd.core.base import BaseDefinition
from whyqd.parsers import DataSourceParser
from whyqd.config.settings import settings


class TransformDefinition(BaseDefinition):
    """Create and manage a transform to perform a schema to schema crosswalk on a tabular data source.

    Parameters:
      transform: Path to a transform definition, or a dictionary conforming to a transform model.
      crosswalk: A definition, or a dictionary conforming to the CrosswalkModel, or a path to a saved definition.
      data_source: Path to a tabular data source, or a dictionary conforming to a data source model.

    Example:
      Create a new `TransformDefinition`, and perform a crosswalk, then save the definition and transformed data
      as follows:

      ```python
      import whyqd as qd

      transform = qd.TransformDefinition(crosswalk=CROSSWALK, data_source=DATASOURCE)
      transform.process()
      transform.save(directory=DIRECTORY)
      ```
    """

    def __init__(
        self,
        *,
        transform: TransformModel | dict | Path | str | None = None,
        crosswalk: CrosswalkDefinition | CrosswalkModel | dict | Path | str | None = None,
        data_source: DataSourceModel | dict | Path | str | None = None,
    ) -> None:
        super().__init__(model_name="transform")
        self.reader = DataSourceParser()
        self.data_source = None
        self.data = None
        self.crosswalk = CrosswalkDefinition()
        self.set(transform=transform, crosswalk=crosswalk, data_source=data_source)
        self.destination_mimetype = settings.WHYQD_DEFAULT_MIMETYPE
        self.destination_path = Path(settings.WHYQD_DIRECTORY)

    @property
    def get(self) -> TransformModel | None:
        """Get the transform model.

        Returns:
          Pydantic TransformModel or None
        """
        return self.model

    def set(
        self,
        *,
        transform: TransformModel | dict | Path | str | None = None,
        crosswalk: CrosswalkDefinition | CrosswalkModel | dict | Path | str | None = None,
        data_source: DataSourceModel | dict | Path | str | None = None,
    ) -> None:
        """Update or create the transform.

        Parameters:
          transform: Path to a transform definition, or a dictionary conforming to a transform model.
          crosswalk: A definition, or a dictionary conforming to the CrosswalkModel, or a path to a saved definition.
          data_source: Path to a tabular data source, or a dictionary conforming to a data source model.
        """
        self.model = self.core.create_or_update_model(modelType=TransformModel, source=transform, model=self.model)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self.model.dataSource and not data_source:
            self.data_source = self.model.dataSource
        elif data_source:
            if isinstance(data_source, DataSourceModel):
                self.data_source = data_source
            else:
                self.data_source = self.core.create_or_update_model(modelType=DataSourceModel, source=data_source)
            self.model.dataSource = self.data_source
        if self.model.crosswalk and not crosswalk:
            self.crosswalk.set(crosswalk=self.model.crosswalk)
        elif crosswalk:
            if isinstance(crosswalk, CrosswalkDefinition):
                self.crosswalk = crosswalk
            else:
                self.crosswalk.set(crosswalk=crosswalk)
            self.model.crosswalk = self.crosswalk.get

    #########################################################################################
    # PERFORM TRANSFORMATION PROCESS
    #########################################################################################

    def process(self) -> None:
        """Perform a crosswalk. You can access the dataframe after completion at `.data`, if it exists.

        Raises:
          ValueError: If there are missing required destination fields in the crosswalk.
        """
        if not self.model.dataSource or not self.model.crosswalk:
            raise ValueError("Before performing data transform provide both a data source and a crosswalk.")
        # Validate crosswalk
        self.crosswalk.validate()
        # Perform crosswalk
        df = self.reader.get(source=self.model.dataSource)
        df = self.crosswalk.crud.transform_all(df=df)
        destination_names = [f.name for f in self.crosswalk.schema_destination.fields.get_all() if f.name in df.columns]
        # Coerce to schema and prepare data source model
        df = self.reader.coerce_to_schema(df=df[destination_names], schema=self.crosswalk.schema_destination)
        required_names = [f.name for f in self.crosswalk.schema_destination.fields.get_required()]
        if set(required_names) - set(df.columns):
            raise ValueError(
                f"Missing required destination fields in crosswalked data: {set(required_names) - set(df.columns)}"
            )
        self.data = df

    #########################################################################################
    # VALIDATION UTILITIES
    #########################################################################################

    def validate(
        self,
        *,
        transform: TransformModel | dict | Path | str,
        data_destination: DataSourceModel | dict | Path | str,
        mimetype_destination: str | MimeType | None = None,
        data_source: DataSourceModel | dict | Path | str | None = None,
        mimetype_source: str | MimeType | None = None,
    ) -> bool:
        """Validate the transformation process and all data checksums. Will perform all actions on each interim
        data source.

        Parameters:
          transform: Path to a transform definition, or a dictionary conforming to a transform model.
          data_destination: Path to a tabular data source, or a dictionary conforming to a data source model. Destination
                            data for crosswalk validation.
          mimetype_destination: **whyqd** supports reading from CSV, XLS, XLSX, Feather and Parquet files. Required if
                                `data_destination` is not of `DataSourceModel`.
          data_source: Path to a tabular data source, or a dictionary conforming to a data source model. Should be defined
                      in `transform`, but you may have a different version from a different location.
          mimetype_source: **whyqd** supports reading from CSV, XLS, XLSX, Feather and Parquet files. Required if
                          `data_source` is provided (i.e. not from the `transform`) and not of `DataSourceModel`.

        Raises:
          ValueError: If any steps fail to validate.

        Returns:
          A boolean `True` on successful validation.
        """
        # Prepare
        self.set(transform=transform)
        if data_source is not None:
            source_df = self.reader.get(
                source=data_source, mimetype=mimetype_source, preserve=self.model.dataSource.preserve
            )
        else:
            source_df = self.reader.get(source=self.model.dataSource)
        # Validate source
        if not self.model.dataSource.checksum:
            raise ValueError("Validation failed. Data source has no saved checksum.")
        self.reader.get_checksum(df=source_df, crosscheck=self.model.dataSource.checksum)
        # Validate destination
        destination_df = self.reader.get(
            source=data_destination, mimetype=mimetype_destination, preserve=self.model.dataDestination.preserve
        )
        if not self.model.dataDestination.checksum:
            raise ValueError("Validation failed. Data destination has no saved checksum.")
        self.reader.get_checksum(df=destination_df, crosscheck=self.model.dataDestination.checksum)
        # Validate crosswalk
        self.crosswalk.validate()
        crosswalk_df = self.crosswalk.crud.transform_all(df=source_df)
        destination_names = [
            f.name for f in self.crosswalk.schema_destination.fields.get_all() if f.name in crosswalk_df.columns
        ]
        crosswalk_df = self.reader.coerce_to_schema(
            df=crosswalk_df[destination_names], schema=self.crosswalk.schema_destination
        )
        required_names = [f.name for f in self.crosswalk.schema_destination.fields.get_required()]
        if set(required_names) - set(crosswalk_df.columns):
            raise ValueError(
                f"Validation failed. Missing required destination fields in crosswalked data: {set(required_names) - set(crosswalk_df.columns)}"
            )
        self.reader.get_checksum(df=crosswalk_df, crosscheck=self.model.dataDestination.checksum)
        return True

    #########################################################################################
    # SAVE UTILITIES
    #########################################################################################

    def save(
        self,
        *,
        filename: str | None = None,
        mimetype: str | None = None,
        directory: str | Path | None = None,
        created_by: str | None = None,
        hide_uuid: bool = False,
    ) -> bool:
        """Save model as a json file, and save crosswalked destination dataframe as a chosen mimetype.

        !!! info
            **whyqd** supports any of the following file mime types:

            - `CSV`: "text/csv"
            - `XLS`: "application/vnd.ms-excel"
            - `XLSX`: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            - `PARQUET` (or `PRQ`): "application/vnd.apache.parquet"
            - `FEATHER` (or `FTR`): "application/vnd.apache.feather"

            Specify the mime type as a text string, uppper- or lower-case. Neither of
            [Parquet](https://parquet.apache.org/docs/overview/) or [Feather](https://arrow.apache.org/docs/python/feather.html)
            yet have official mimetypes, so this is what we're using for now.

            **NOTE:** by default, transformed data are saved as `PARQUET` as this is the most efficient.

        Parameters:
          directory:  Defaults to working directory
          filename:  Defaults to model name
          mimetype: **whyqd** supports saving to CSV, XLS, XLSX, Feather and Parquet files. Defaults to Parquet.
          created_by:  Declare the model creator/updater
          hide_uuid:  Hide all UUIDs in the nested JSON output.

        Returns:
          Boolean True if saved.
        """
        if self.data is None:
            raise ValueError("No destination data available. First run a crosswalk.")
        if mimetype:
            mimetype = self.reader.get_mimetype(mimetype=mimetype)
            self.destination_mimetype = mimetype
        else:
            mimetype = self.reader.get_mimetype(mimetype=self.destination_mimetype)
        if directory and self.core.check_source(source=directory):
            self.destination_path = Path(directory)
        if filename:
            source = self.destination_path / f"{self.core.get_now()}-{filename}.{mimetype.name}"
        else:
            source = (
                self.destination_path
                / f"{self.core.get_now()}-{self.model.crosswalk.schemaDestination.name}.{mimetype.name}"
            )
        self.model.dataDestination = self.reader.get_source_data_model(df=self.data, source=source, mimetype=mimetype)
        self.reader.set(df=self.data, source=source, mimetype=mimetype)
        super().save(filename=filename, directory=directory, created_by=created_by, hide_uuid=hide_uuid)
