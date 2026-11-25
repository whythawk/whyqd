# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from typing import TYPE_CHECKING
from pydantic import Json, BaseModel
from datetime import date, datetime

from whyqd.parsers.definition import DefinitionParser
from whyqd.models import VersionModel, CitationModel

if TYPE_CHECKING:
    from whyqd.sources.datasource import DataSourceParser


class BaseDefinition:
    """Core shared base definition functionality."""

    def __init__(self, *, model_name: str) -> None:
        self.definitions = DefinitionParser()
        self.model = None
        self.model_name = model_name  # method / schema / transform / etc.
        self._reader = None

    @property
    def reader(self) -> DataSourceParser:
        # The reader loads the engine, which reading a definition must not
        if self._reader is None:
            from whyqd.sources.datasource import DataSourceParser

            self._reader = DataSourceParser()
        return self._reader

    def __repr__(self) -> str:
        """Returns the string representation of the model."""
        if self.model:
            return f"{self.model_name.title()}: `{self.model.name}`"
        return f"{self.model_name.title()}"

    @property
    def describe(self) -> dict[str, None] | None:
        """Get the model name, title and description.

         - name: Term used for filename and referencing.
         - title: Human-readable term used as name.
         - description: Detailed description for the model. Reference its objective and use-case.

        Returns:
          A dictionary with the `name`, `title` and `description` for the `Definition`.
        """
        if self.model:
            return {
                "name": self.model.name,
                "title": self.model.title,
                "description": self.model.description,
            }
        return None

    def _refresh_model_terms(self) -> None:
        """Any process to be run to ensure concord between this definition and its model."""
        pass

    def _refresh_model_fields(self) -> None:
        """Refreshes the list of model fields and connects them to the Field CRUD"""
        pass

    def get_citation(self) -> dict[str, str | dict[str, str]]:
        """Get the citation as a dictionary.

        Raises:
          ValueError: If no citation has been declared or the build is incomplete.

        Returns:
          A dictionary conforming to the CitationModel.
        """
        if not self.model.citation:
            raise ValueError(
                f"`{self.model.name}` has no citation yet. Set one with `set_citation`. [whyqd:citation-none]"
            )
        return self.model.citation.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)

    def set_citation(self, *, citation: CitationModel) -> None:
        """Update or create the citation.

        **whyqd** is designed to support a research process and ensure citation of the incredible work done by
        research-based data scientists.

        A citation has the following definable fields:

        - **author**: The name(s) of the author(s) (in the case of more than one author, separated by `and`),
        - **title**: The title of the work,
        - **url**: The URL of a web page or FTP download; a non-standard BibTeX field,
        - **publisher**: The publisher's name,
        - **institution**: The institution that was involved in the publishing, but not necessarily the publisher,
        - **doi**: The digital object identifier (DOI) of a journal article, conference paper, book chapter, or book; a
          non-standard BibTeX field. Give the DOI itself, not a link to it,
        - **month**: The month of publication (or, if unpublished, of creation), as a three-letter abbreviation,
        - **year**: The year of publication (or, if unpublished, the year of creation),
        - **licence**: The terms under which the associated resource are licenced for reuse,
        - **note**: Miscellaneous extra information.

        Parameters:
          citation: A dictionary conforming to the CitationModel.

        Examples:
          ```python
          import whyqd as qd

          datasource = qd.DataSourceDefinition()
          datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE)
          citation = {
              "author": "A. N. Author",
              "month": "feb",
              "year": 2020,
              "title": "A town's business rates, one row a property",
              "url": "https://github.com/whythawk/whyqd/tree/master/tests/data",
              "licence": "Attribution 4.0 International (CC BY 4.0)",
          }
          datasource.set_citation(citation=citation)
          ```
        """
        # Create a temporary CitationModel
        self.model.citation = self.definitions.build(kind=CitationModel, source=citation, model=self.model.citation)

    def exclude_uuid(self, *, model: BaseModel | dict) -> dict:
        """A definition without its UUIDs, in the current format, for comparing two that differ only by them.

        Parameters:
          model: A model, or a saved definition in any format whyqd reads.
        """
        formats = self.definitions.formats
        if isinstance(model, BaseModel):
            model = model.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)
        else:
            model = formats.read(source=model)
        # A time as its text, so the result serialises as JSON
        return formats.walk(
            model,
            lambda d: {k: v.isoformat() if isinstance(v, (datetime, date)) else v for k, v in d.items() if k != "uuid"},
        )

    def get_json(self, hide_uuid: bool = False, format: str | None = None) -> Json | None:
        """Get the json model.

        Parameters:
          hide_uuid: Hide all UUIDs in the nested JSON output. Mostly useful for validation assertions where the only
                     differences between sources are the UUIDs.
          format: The definition format to write, one of `settings.FORMAT_VERSIONS` (`whyqd.config.settings`).
                  Defaults to the current one; give
                  `"1.x"` to share with someone whose whyqd is older.

        Raises:
          ValueError: If `format` is unknown, or the definition holds something it cannot.

        Returns:
          Json-conforming output, or None.
        """
        self._refresh_model_terms()
        if not self.model:
            return None
        formats = self.definitions.formats
        return formats.dumps(formats.write(model=self.model, format=format, hide_uuid=hide_uuid))

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
        self._refresh_model_terms()
        if not self.model:
            raise ValueError(
                f"This {self.model_name} definition is empty, so there is nothing to save. Set or derive it first. "
                "[whyqd:definition-empty]"
            )
        directory = self.definitions.directory(directory)
        if not filename:
            filename = f"{self.model.name}.{self.model_name}"
        if filename.split(".")[-1] != self.model_name:
            filename += f".{self.model_name}"
        if "version" in self.model.model_dump():
            update = VersionModel(**{"description": f"Save {self.model_name}."})
            if created_by:
                update.name = created_by
            self.model.version.append(update)
        return self.definitions.save(text=self.get_json(hide_uuid=hide_uuid, format=format), path=directory / filename)
