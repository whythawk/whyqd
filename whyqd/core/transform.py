# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import warnings
from pathlib import Path
from typing import ClassVar

from whyqd.dtypes import ChecksumContent, FieldType, FindingKind, MimeType
from whyqd.models import (
    ActionScriptModel,
    CrosswalkModel,
    DataSourceModel,
    FieldModel,
    FindingModel,
    ReportModel,
    TransformModel,
)
from whyqd.models.utc import UtcParser
from whyqd.core import CrosswalkDefinition
from whyqd.core.base import BaseDefinition
from whyqd.config.settings import settings


class ConformanceError(ValueError):
    """A transform that cannot conform to its destination schema, and so is not built. `report` says why: every refused
    cell and failed constraint the run found. A `ValueError`, so code catching that still catches it."""

    def __init__(self, message: str, *, report: ReportModel) -> None:
        super().__init__(message)
        self.report = report


class TransformDefinition(BaseDefinition):
    """Create and manage a transform to perform a schema to schema crosswalk on a tabular data source.

    Parameters:
      transform: Path to a transform definition, or a dictionary conforming to a transform model.
      crosswalk: A definition, or a dictionary conforming to the CrosswalkModel, or a path to a saved definition.
      data_source: Path to a tabular data source, or a dictionary conforming to a data source model.

    Examples:
      Create a new `TransformDefinition`, and perform a crosswalk, then save the definition and transformed data
      as follows:

      ```python
      import whyqd as qd

      transform = qd.TransformDefinition(crosswalk=CROSSWALK, data_source=DATASOURCE)
      transform.process()
      transform.save(directory=DIRECTORY)
      ```
    """

    # The actions that read their sources as a type, whatever the source schema declares
    READS_AS: ClassVar[dict[str, str]] = {
        "CALCULATE": FieldType.NUMBER.value,
        "SELECT_NEWEST": FieldType.DATE.value,
        "SELECT_OLDEST": FieldType.DATE.value,
    }
    # The actions that take each value with the date beside it
    DATED: ClassVar[frozenset[str]] = frozenset({"SELECT_NEWEST", "SELECT_OLDEST"})
    # The actions whose destination takes a source's value as it is, so the two types must agree
    MAPS_DIRECTLY: ClassVar[frozenset[str]] = frozenset({"RENAME", "SELECT", "SELECT_NEWEST", "SELECT_OLDEST"})
    UNREADY: ClassVar[str] = "Before performing data transform provide both a data source and a crosswalk."

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
        self.report = None
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
        self.model = self.definitions.build(kind=TransformModel, source=transform, model=self.model)
        # And update the original data
        # https://fastapi.tiangolo.com/tutorial/body-updates/#partial-updates-with-patch
        if self.model.dataSource and not data_source:
            self.data_source = self.model.dataSource
        elif data_source:
            if isinstance(data_source, DataSourceModel):
                self.data_source = data_source
            else:
                self.data_source = self.definitions.build(kind=DataSourceModel, source=data_source)
            self.model.dataSource = self.data_source
        if self.model.crosswalk and not crosswalk:
            self.crosswalk.set(crosswalk=self.model.crosswalk)
        elif crosswalk:
            if isinstance(crosswalk, CrosswalkDefinition):
                self.crosswalk = crosswalk
            else:
                self.crosswalk.set(crosswalk=crosswalk)
            self.model.crosswalk = self.crosswalk.get

    def process(self, *, strict: bool = False) -> None:
        """Perform a crosswalk. You can access the dataframe after completion at `.data`, if it exists, and what the run
        found at `.report`.

        Parameters:
          strict: Treat every warning as a fault, so a run either builds exactly what a plain run builds, with nothing
            to check, or halts. Never stored on a definition.

        Raises:
          ConformanceError: If the table cannot conform to the destination schema, or under `strict` a value was read
            with something to check.
          ValueError: If there are missing required destination fields in the crosswalk.
        """
        if not self.model.dataSource or not self.model.crosswalk:
            raise ValueError(self.UNREADY)
        # The package imports this module, so its version is read here, once it has loaded
        import whyqd

        self.model.started = self.utc.now()
        self.model.ended = None
        self.model.whyqd = whyqd.__version__
        # Validate crosswalk
        self.crosswalk.validate()
        self.bound(source=self.model.dataSource)
        self.data = None
        self.data = self.conform(source=self.model.dataSource, strict=strict)
        self.model.ended = self.utc.now()

    def diagnose(self, *, propose: bool = False) -> ReportModel:
        """What a run would find, building nothing and changing nothing here: the report `process` would leave, each
        refused cell and warning among its findings. With `propose`, for each column read as a type, the policy to
        declare on its source field where one reading reads every cell, and otherwise a fact saying why none can be.
        Nothing is applied: declare what you decide on the source schema's field.

        A column is read as the type its source field declares, or an action reads it as, or the destination field an
        action maps it to. A source field already declaring a policy is left as it is.

        Parameters:
          propose: Also propose a policy for each typed column.

        Returns:
          The report.

        Raises:
          ValueError: Without both a data source and a crosswalk, or where a required destination field is never built.

        Examples:
          ```python
          import whyqd as qd

          transform = qd.TransformDefinition(crosswalk=CROSSWALK, data_source=DATASOURCE)
          report = transform.diagnose(propose=True)
          for proposal in report.proposals:
              print(proposal.field, proposal.value, proposal.evidence)
          ```
        """
        from whyqd.reading.proposal import ProposalParser

        if not self.model.dataSource or not self.model.crosswalk:
            raise ValueError(self.UNREADY)
        held = self.report
        self.crosswalk.validate()
        self.bound(source=self.model.dataSource)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self.conform(source=self.model.dataSource)
            except ConformanceError:
                pass
        report, self.report = self.report, held
        if propose:
            proposer = ProposalParser()
            table, types = self.reader.typed_table(source=self.model.dataSource)
            for name, dtype in self.typed().items():
                if name not in table.columns:
                    continue
                found = proposer.propose(field=name, cells=table[name], types=types[name], dtype=dtype)
                if isinstance(found, FindingModel):
                    report.findings.append(found)
                elif found is not None:
                    report.proposals.append(found)
        return report

    def typed(self) -> dict[str, str]:
        """Each source field read as a type, and that type: the destination's where an action maps the field directly,
        an action's where it reads the field as one, and the field's own where it declares one. A field already
        declaring a policy is left out, its reading being the wrangler's."""
        from whyqd.reading.conformance import ConformanceParser

        destination_fields = self.crosswalk.schema_destination.fields.get_all()
        _, inputs, _, mapped = self.reads(conformance=ConformanceParser(), destination_fields=destination_fields)
        found = {**mapped, **inputs}
        for field in self.crosswalk.schema_source.fields.get_all():
            if field.policy is not None:
                found.pop(field.name, None)
            elif field.dtype != FieldType.STRING.value:
                found[field.name] = field.dtype
        return found

    def conform(self, *, source: DataSourceModel, strict: bool = False):
        """The table the crosswalk builds from `source`, conforming to the destination schema, or a halt that leaves its
        reasons in `report`. Under `strict`, every warning is a fault.

        Raises:
          ConformanceError: If the table cannot conform.
          ValueError: If a required destination field is never built.
        """
        from whyqd.reading.conformance import ConformanceParser

        conformance = ConformanceParser()
        origin, destination = self.crosswalk.schema_source, self.crosswalk.schema_destination
        destination_fields = destination.fields.get_all()
        policies, inputs, read_fields, _ = self.reads(conformance=conformance, destination_fields=destination_fields)
        table, types = self.reader.typed_table(source=source)
        df = conformance.source(
            table=table, types=types, fields=origin.fields.get_all(), missing=origin.get.missingValues, inputs=inputs
        )
        df = self.crosswalk.crud.transform_all(df=df)
        conformance.settle_source(df=df, read_fields=read_fields)
        row_key = [c for c in df.columns if conformance.row_key.is_part(c)]
        names = [f.name for f in destination_fields if f.name in df.columns]
        required = {f.name for f in destination.fields.get_required()} - set(df.columns)
        if required:
            raise ValueError(f"Missing required destination fields in crosswalked data: {required}")
        df = conformance.destination(
            df=df[[*row_key, *names]],
            fields=destination_fields,
            missing=destination.get.missingValues,
            policies=policies,
        )
        if strict:
            conformance.faults += [
                found.model_copy(update={"kind": FindingKind.FAULT}) for found in conformance.warnings
            ]
            conformance.warnings = []
        self.report = conformance.report(path=source.path, mime=source.mime)
        if conformance.faults:
            raise ConformanceError(
                f"`{source.name}` cannot conform to `{destination.get.name}`: {len(conformance.faults)} problems in "
                f"{len({f.field for f in conformance.faults})} fields. Read `report`, resolve them, and run again. "
                "[whyqd:transform-halted]",
                report=self.report,
            )
        if conformance.warnings:
            warnings.warn(
                f"`{source.name}` read with {len(conformance.warnings)} things to check. Read `report`. "
                "[whyqd:transform-warned]",
                UserWarning,
                stacklevel=2,
            )
        return df[names]

    def reads(self, *, conformance, destination_fields: list) -> tuple[dict, dict, set, dict]:
        """What the crosswalk's actions read: the policy each destination field's text is built under, the undeclared
        source fields an action reads as a type, every source field read, and the destination type of each source field
        an action maps directly. Each policy is checked against its field, and a source field against the destination it
        maps to."""
        by_name = {field.name: field for field in destination_fields}
        for field in destination_fields:
            if field.policy and (field.policy.format is not None or field.policy.rules is not None):
                raise ValueError(
                    f"Destination field `{field.name}` declares how a publisher wrote it, which a shared schema cannot "
                    "know. Move its `format` and `rules` to the source field or the action. "
                    "[whyqd:policy-on-destination]"
                )
        policies, inputs, read_fields, mapped = {}, {}, set(), {}
        for script in self.crosswalk.crud.get_all():
            parsed = self.crosswalk.crud.parse(script=script)
            name = parsed["action"].name
            destinations = parsed.get("destination") or []
            destinations = destinations if isinstance(destinations, list) else [destinations]
            sources = [term for term in self.flatten(parsed.get("source")) if isinstance(term, FieldModel)]
            read_fields |= {field.name for field in sources}
            dated = name in self.DATED
            if name in self.READS_AS:
                inputs |= {field.name: self.READS_AS[name] for field in (sources[1::2] if dated else sources)}
            if name in self.MAPS_DIRECTLY:
                for target in destinations:
                    for field in sources[::2] if dated else sources:
                        if target.name in by_name:
                            conformance.conflict(source=field, destination=by_name[target.name])
                            mapped[field.name] = by_name[target.name].dtype
            policy = script.policy if isinstance(script, ActionScriptModel) else None
            if policy is not None:
                outputs = policy if isinstance(policy, dict) else {target.name: policy for target in destinations}
                # A copy is read, so the step keeps its policy as written
                outputs = {target: held.model_copy(deep=True) for target, held in outputs.items()}
                for target, held in outputs.items():
                    if target in by_name:
                        held.standardise(dtype=by_name[target].dtype)
                        held.check(name=target, dtype=by_name[target].dtype)
                policies |= outputs
        return policies, inputs, read_fields, mapped

    def flatten(self, terms) -> list:
        """A parsed script's source terms, however deep an action nested them."""
        if not terms:
            return []
        if isinstance(terms, dict):
            return self.flatten(terms.get("source"))
        if isinstance(terms, (list, tuple)):
            return [found for term in terms for found in self.flatten(term)]
        return [terms]

    def validate(
        self,
        *,
        transform: TransformModel | dict | Path | str,
        data_destination: DataSourceModel | dict | Path | str,
        mimetype_destination: str | MimeType | None = None,
        data_source: DataSourceModel | dict | Path | str | None = None,
        mimetype_source: str | MimeType | None = None,
    ) -> bool:
        """Verify a transform: its source is the file it was built from, its output is the file given, and running its
        crosswalk again on the source builds that output.

        Parameters:
          transform: Path to a transform definition, or a dictionary conforming to a transform model.
          data_destination: The output file to check, by path.
          mimetype_destination: The output file's format: CSV, XLS, XLSX, Feather, or Parquet.
          data_source: The source, where it is not the one the transform names: a data source, a dictionary of one,
            or the path of the same file elsewhere.
          mimetype_source: For a source given by path, its format, where it differs from the stored one.

        Raises:
          ImportError: If the `verify-1x` extra is not installed.
          ValueError: If any steps fail to validate.

        Returns:
          A boolean `True` on successful validation.
        """
        # An output's checksums are 1.x's, so the files are read as 1.x read them
        v1 = self.reader.v1

        def crosscheck(df, checksum: str) -> None:
            if (generated := v1.table(df=df)) != checksum:
                raise ValueError(
                    f"Checksum provided ({checksum}) is not equal to the generated checksum ({generated}). Check your "
                    "data source."
                )

        # Prepare
        self.set(transform=transform)
        # Validate source
        model = self.model.dataSource
        if isinstance(data_source, DataSourceModel):
            model = data_source
        elif isinstance(data_source, dict):
            model = self.definitions.build(kind=DataSourceModel, source=data_source)
        elif data_source is not None:
            moved = {"path": str(data_source)}
            if mimetype_source:
                moved["mime"] = self.reader.get_mimetype(mimetype=mimetype_source)
            model = model.model_copy(update=moved)
        self.reader.verify(source=model)
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
        self.bound(source=model)
        try:
            crosswalk_df = self.conform(source=model)
        except ValueError as e:
            raise ValueError(f"Validation failed. {e}") from e
        crosscheck(crosswalk_df, destination_checksum)
        return True

    def bound(self, *, source: DataSourceModel) -> None:
        """Refuse a row-level action naming a row past the end of the data source's file, by its `index`, since a
        schema carried from another file holds no row count.

        Raises:
          ValueError: Naming the rows past its end, or where the data source has no row count to check them by.
        """
        named = self.crosswalk.crud.rows()
        if not named:
            return
        if source.index is None:
            raise ValueError(
                f"`{source.name}` has no row count, so the rows the crosswalk names cannot be checked. Derive it "
                "again. [whyqd:rows-uncounted]"
            )
        if past := sorted({r for r in named if not 0 <= r < source.index}):
            raise ValueError(
                f"The crosswalk names rows {past} of `{source.name}`, which has {source.index}, numbered from 0. "
                "Check the rows each action names. [whyqd:row-past-end]"
            )

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
          format: The definition format to write, one of `settings.FORMAT_VERSIONS` (`whyqd.config.settings`).
                  Defaults to the current one.

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
        if directory:
            self.destination_path = self.definitions.directory(directory)
        today = self.utc.now().date().isoformat()
        if filename:
            source = self.destination_path / f"{today}-{filename}.{mimetype.name}"
        else:
            source = (
                self.destination_path
                / f"{today}-{self.model.crosswalk.schemaDestination.name}-{self.model.uuid}.{mimetype.name}"
            )
        self.model.dataDestination = self.reader.get_source_data_model(df=self.data, source=source, mimetype=mimetype)
        self.reader.set(df=self.data, source=source, mimetype=mimetype)
        return super().save(
            filename=filename, directory=directory, created_by=created_by, hide_uuid=hide_uuid, format=format
        )
