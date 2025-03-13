from __future__ import annotations
from pydantic import Json, BaseModel
from collections.abc import MutableMapping
from pathlib import Path
from datetime import date, datetime
import json

from whyqd.parsers import CoreParser
from whyqd.models import VersionModel, CitationModel


class BaseDefinition:
    """Core shared base definition functionality."""

    def __init__(self, *, model_name: str) -> None:
        self.core = CoreParser()
        self.model = None
        self.model_name = model_name  # method / schema / transform / etc.

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
        if not self.model.citation:
            raise ValueError("No citation has been declared yet.")
        return self.model.citation.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)

    def set_citation(self, *, citation: CitationModel) -> None:
        """Update or create the citation.

        **whyqd** is designed to support a research process and ensure citation of the incredible work done by
        research-based data scientists.

        A citation has the following definable fields::

        - **author**: The name(s) of the author(s) (in the case of more than one author, separated by `and`),
        - **title**: The title of the work,
        - **url**: The URL field is used to store the URL of a web page or FTP download. It is a non-standard BibTeX field,
        - **publisher**: The publisher's name,
        - **institution**: The institution that was involved in the publishing, but not necessarily the publisher,
        - **doi**: The doi field is used to store the digital object identifier (DOI) of a journal article, conference paper,
          book chapter or book. It is a non-standard BibTeX field. It's recommended to simply use the DOI, and not a DOI link,
        - **month**: The month of publication (or, if unpublished, the month of creation). Use three-letter abbreviation,
        - **year**: The year of publication (or, if unpublished, the year of creation),
        - **licence**: The terms under which the associated resource are licenced for reuse,
        - **note**: Miscellaneous extra information.

        Parameters:
          citation: A dictionary conforming to the CitationModel.

        Example:
          ```python
          import whyqd as qd

          datasource = qd.DataSourceDefinition()
          datasource.derive_model(source=SOURCE_DATA, mimetype=MIMETYPE)
          citation = {
              "author": "Gavin Chait",
              "month": "feb",
              "year": 2020,
              "title": "Portsmouth City Council normalised database of commercial ratepayers",
              "url": "https://github.com/whythawk/whyqd/tree/master/tests/data",
              "licence": "Attribution 4.0 International (CC BY 4.0)",
          }
          datasource.set_citation(citation=citation)
          ```
        """
        # Create a temporary CitationModel
        self.model.citation = self.core.create_or_update_model(
            modelType=CitationModel, source=citation, model=self.model.citation
        )

    #########################################################################################
    # SAVE UTILITIES
    #########################################################################################

    def exclude_uuid(self, *, model: BaseModel | dict):
        # https://stackoverflow.com/a/49723101/295606
        if isinstance(model, BaseModel):
            model = model.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True, exclude={"uuid": True})
        excluded = {}
        for key, field in model.items():
            if key != "uuid":
                if isinstance(field, MutableMapping):
                    excluded[key] = self.exclude_uuid(model=field)
                elif field and isinstance(field, list) and isinstance(field[0], MutableMapping):
                    # Assuming field consistency ... no mixed Mutables and non-Mutables
                    excluded[key] = []
                    for f in field:
                        excluded[key].append(self.exclude_uuid(model=f))
                else:
                    if isinstance(field, (datetime, date)):
                        # To make sure json.dumps doesn't run into datetime errors
                        field = field.isoformat()
                    excluded[key] = field
        return excluded

    def get_json(self, hide_uuid: bool = False) -> Json | None:
        """Get the json model.

        Parameters:
          hide_uuid: Hide all UUIDs in the nested JSON output. Mostly useful for validation assertions where the only
                     differences between sources are the UUIDs.

        Returns:
          Json-conforming output, or None.
        """
        self._refresh_model_terms()
        if self.model and not hide_uuid:
            return self.model.model_dump_json(by_alias=True, exclude_defaults=True, exclude_none=True)
        elif self.model and hide_uuid:
            return json.dumps(self.exclude_uuid(model=self.model))
        return None

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
        self._refresh_model_terms()
        if not self.model:
            raise ValueError(f"{self.model_name.title()} model does not exist.")
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
        path = directory / filename
        if "version" in self.model.model_dump():
            update = VersionModel(**{"description": f"Save {self.model_name}."})
            if created_by:
                update.name = created_by
            self.model.version.append(update)
        return self.core.save_file(data=self.get_json(hide_uuid=hide_uuid), source=path)
