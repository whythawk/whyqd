# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pathlib import Path

from whyqd.dtypes import ChecksumContent, MimeType
from whyqd.models import DataSourceModel, CrosswalkModel, TransformModel
from whyqd.models.utc import UtcParser
from whyqd.core import CrosswalkDefinition
from whyqd.core.base import BaseDefinition
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
        self.data_source = None
        self.data = None
        self.crosswalk = CrosswalkDefinition()
        self.utc = UtcParser()
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
        # The package imports this module, so its version is read here, once it has loaded
        import whyqd

        self.model.started = self.utc.now()
        self.model.ended = None
        self.model.whyqd = whyqd.__version__
        # Validate crosswalk
        self.crosswalk.validate()
        # Perform crosswalk, coercing to source schema prior to crosswalk
        df = self.reader.get(source=self.model.dataSource)
        df = self.reader.coerce_to_schema(df=df, schema=self.crosswalk.schema_source)
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
        self.model.ended = self.utc.now()

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
        # The checksums are 1.x's, so the files are read as 1.x read them
        from whyqd.parsers.v1 import V1ChecksumParser

        v1 = V1ChecksumParser()

        def crosscheck(df, checksum: str) -> None:
            if (generated := v1.table(df=df)) != checksum:
                raise ValueError(
                    f"Checksum provided ({checksum}) is not equal to the generated checksum ({generated}). Check your data source."
                )

        # Prepare
        self.set(transform=transform)
        # Validate source
        source_checksum = self.model.dataSource.get_checksum(ChecksumContent.TABLE_1X)
        if source_checksum:
            if data_source is not None:
                source_df = v1.read(
                    source=data_source, mimetype=mimetype_source, preserve=self.model.dataSource.preserve
                )
            else:
                source_df = v1.read(source=self.model.dataSource)
            crosscheck(source_df, source_checksum)
        else:
            model = self.model.dataSource
            if isinstance(data_source, DataSourceModel):
                model = data_source
            elif isinstance(data_source, dict):
                model = DataSourceModel(**data_source)
            elif data_source is not None:
                model = model.model_copy(update={"path": str(data_source)})
            hashed = model.get_checksum(ChecksumContent.BYTES)
            if not hashed:
                raise ValueError("Validation failed. Data source has no saved checksum.")
            if self.core.get_checksum(source=model.path) != hashed:
                raise ValueError(f"Validation failed. `{model.path}` is not the file its byte hash was taken from.")
            source_df = self.reader.get(source=model)
        # Validate destination
        destination_df = v1.read(
            source=data_destination, mimetype=mimetype_destination, preserve=self.model.dataDestination.preserve
        )
        destination_checksum = self.model.dataDestination.get_checksum(ChecksumContent.TABLE_1X)
        if not destination_checksum:
            raise ValueError("Validation failed. Data destination has no saved checksum.")
        crosscheck(destination_df, destination_checksum)
        # Validate crosswalk, coercing to source schema prior to crosswalk
        self.crosswalk.validate()
        source_df = self.reader.coerce_to_schema(df=source_df, schema=self.crosswalk.schema_source)
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
        crosscheck(crosswalk_df, destination_checksum)
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
        format: str | None = None,
    ) -> bool:
        """Save model as a json file, and save crosswalked destination dataframe as a chosen mimetype.

        !!! info
            **NOTE:** by default, transformed data are saved as `PARQUET` as this is the most efficient.

            Declare your mime type like so:

            ```python
            MIMETYPE = "csv" # upper- or lower-case is fine
            ```


        Parameters:
          directory:  Defaults to working directory
          filename:  Defaults to model name
          mimetype: **whyqd** supports saving to CSV, XLS, XLSX, Feather and Parquet files. Defaults to Parquet.
          created_by:  Declare the model creator/updater
          hide_uuid:  Hide all UUIDs in the nested JSON output.
          format: The definition format to write, one of `settings.FORMAT_VERSIONS` (`whyqd.config.settings`). Defaults to the current one.

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
                / f"{self.core.get_now()}-{self.model.crosswalk.schemaDestination.name}-{self.model.uuid}.{mimetype.name}"
            )
        self.model.dataDestination = self.reader.get_source_data_model(df=self.data, source=source, mimetype=mimetype)
        self.reader.set(df=self.data, source=source, mimetype=mimetype)
        super().save(filename=filename, directory=directory, created_by=created_by, hide_uuid=hide_uuid, format=format)
