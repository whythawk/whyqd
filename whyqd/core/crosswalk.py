# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from pathlib import Path
from typing import ClassVar

from whyqd.config.patterns import PythonPatterns
from whyqd.dtypes import FindingKind
from whyqd.models import CrosswalkModel, CrosswalkReportModel, FindingModel, ProposalModel, SchemaModel
from whyqd.core import SchemaDefinition
from whyqd.crud import CRUDAction
from whyqd.core.base import BaseDefinition


class CrosswalkDefinition(BaseDefinition):
    """Create and manage a method to perform a schema to schema crosswalk.

    !!! tip "Strategy"
        Guidance on how to use this definition is in the strategies section on
        [Crosswalk Strategies](../strategies/crosswalk.md).

    Parameters:
      crosswalk: A dictionary conforming to the CrosswalkModel, or a path to a saved definition.
      schema_source: Path to a saved schema, or a dictionary conforming to one, or a definition.
      schema_destination: Path to a saved schema, or a dictionary conforming to one, or a definition.

    Examples:
      Create a new `CrosswalkDefinition` as follows:

      ```python
      import whyqd as qd

      crosswalk = qd.CrosswalkDefinition()
      crosswalk.set(schema_source=SCHEMA_SOURCE, schema_destination=SCHEMA_DESTINATION)
      ```
    """

    # The code of a step's refusal that has none of its own yet
    STEP_REFUSED: ClassVar[str] = "step-refused"

    def __init__(
        self,
        *,
        crosswalk: CrosswalkModel | dict | Path | str | None = None,
        schema_source: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
        schema_destination: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
    ) -> None:
        super().__init__(model_name="crosswalk")
        self.crud = CRUDAction()
        self.schema_source = SchemaDefinition()
        self.schema_destination = SchemaDefinition()
        self.set(crosswalk=crosswalk, schema_source=schema_source, schema_destination=schema_destination)

    def _refresh_model_terms(self) -> None:
        """Refreshes the list of terms and connects them to the Form Model"""
        if self.model:
            self.model.actions = self.crud.get_all()

    def _refresh_model_fields(self) -> None:
        """Refreshes the list of terms and connects them to the Field CRUD"""
        if self.model and self.model.actions:
            self.crud.add_multi(terms=self.model.actions)
        if self.model and not self.model.actions:
            self.crud.reset()

    @property
    def get(self) -> CrosswalkModel | None:
        """Get the crosswalk model.

        Returns:
          A Pydantic CrosswalkModel or None
        """
        self._refresh_model_terms()
        return self.model

    def set(
        self,
        *,
        crosswalk: CrosswalkModel | dict | Path | str | None = None,
        schema_source: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
        schema_destination: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
        drop: list[int] | None = None,
    ) -> None:
        """Update or create the crosswalk.

        Parameters:
          crosswalk: A dictionary conforming to the CrosswalkModel, or a path to a saved definition.
          schema_source: Path to a saved schema, or a dictionary conforming to one, or a definition.
          schema_destination: Path to a saved schema, or a dictionary conforming to one, or a definition.
          drop: The steps of `crosswalk` to leave out, by their place among its steps, from 0, as `diagnose`
            proposes for a step that would be refused. Save the crosswalk to keep it without them.
        """
        self.model = self.definitions.build(kind=CrosswalkModel, source=crosswalk, model=self.model)
        if drop:
            self.model.actions = [step for place, step in enumerate(self.model.actions or []) if place not in drop]
        if self.model.schemaSource and not schema_source:
            self.schema_source.set(schema=self.model.schemaSource)
        elif schema_source:
            if isinstance(schema_source, SchemaDefinition):
                self.schema_source = schema_source
            else:
                self.schema_source.set(schema=schema_source)
            self.model.schemaSource = self.schema_source.get
        if self.model.schemaDestination and not schema_destination:
            self.schema_destination.set(schema=self.model.schemaDestination)
        elif schema_destination:
            if isinstance(schema_destination, SchemaDefinition):
                self.schema_destination = schema_destination
            else:
                self.schema_destination.set(schema=schema_destination)
            self.model.schemaDestination = self.schema_destination.get
        if self.model.schemaSource and self.model.schemaDestination:
            self.crud.set_schema(schema_source=self.schema_source, schema_destination=self.schema_destination)
            self._refresh_model_fields()

    @property
    def actions(self) -> CRUDAction:
        """Returns the active crud model for all Action operations. See [Action CRUD](action.md) for API.

        Returns:
          For all Action CRUD behaviours.
        """
        if not self.model.schemaSource or not self.model.schemaDestination:
            raise ValueError(
                f"Crosswalk `{self.model.name}` has no source and destination schemas yet. Set both before its steps. "
                "[whyqd:crosswalk-schemas]"
            )
        return self.crud

    def validate(self) -> bool:
        """Validate that all required fields are returned from the crosswalk.

        Raises:
          ValueError: If required destination fields are not present in the crosswalk.

        Returns:
          A boolean `True` if successful.
        """
        required = self.crud.validate(required=True)
        if required:
            names = "`, `".join(f.name for f in required)
            raise ValueError(
                f"Crosswalk `{self.model.name}` has no step building required destination fields `{names}`. Add a step "
                "for each. [whyqd:crosswalk-required]"
            )
        return True

    def diagnose(
        self,
        *,
        crosswalk: CrosswalkModel | dict | Path | str,
        schema_source: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
        schema_destination: SchemaDefinition | SchemaModel | dict | Path | str | None = None,
        propose: bool = False,
    ) -> CrosswalkReportModel:
        """Each step of a saved crosswalk that loading it would refuse, found without refusing. Nothing is applied, and
        this definition does not change: load the crosswalk with `set`'s `drop`, naming the steps to leave out.

        Parameters:
          crosswalk: A saved crosswalk, by path, dictionary, or model.
          schema_source: The source schema, where the crosswalk does not hold it.
          schema_destination: The destination schema, where the crosswalk does not hold it.
          propose: Also propose, for each refused step, leaving it out.

        Examples:
          ```python
          import whyqd as qd

          report = qd.CrosswalkDefinition().diagnose(crosswalk=CROSSWALK_PATH, propose=True)
          crosswalk = qd.CrosswalkDefinition()
          crosswalk.set(crosswalk=CROSSWALK_PATH, drop=[proposal.value for proposal in report.proposals])
          ```
        """
        model = self.definitions.build(kind=CrosswalkModel, source=crosswalk)
        checked = CrosswalkDefinition()
        checked.set(
            crosswalk=model.model_copy(update={"actions": []}),
            schema_source=schema_source,
            schema_destination=schema_destination,
        )
        report = CrosswalkReportModel(name=model.name)
        for place, step in enumerate(model.actions or []):
            try:
                checked.actions.parse(script=step.script)
            except ValueError as e:
                coded = PythonPatterns.MESSAGE.match(str(e))
                code, message = (coded.group(2), coded.group(1)) if coded else (self.STEP_REFUSED, str(e))
                report.findings.append(FindingModel(code=code, kind=FindingKind.FAULT, message=message, step=place))
                if propose:
                    report.proposals.append(
                        ProposalModel(setting="drop", value=place, evidence=f"`{step.script}`: {message}")
                    )
        return report
