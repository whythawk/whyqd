# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import json
from pathlib import Path
from typing import TypeVar

import randomname
from pydantic import BaseModel

from whyqd.config.settings import settings
from whyqd.parsers.extension import ExtensionParser
from whyqd.parsers.format import FormatParser

Model = TypeVar("Model", bound=BaseModel)


class DefinitionParser:
    """Build and save whyqd's definitions: a schema, crosswalk, data source, or transform, and what they hold.

    A definition is built from a saved file, a dictionary, or a model, upgraded to the current format as it is read,
    and refused where an extension it declares cannot be used here. It is saved as its format writes it, into a
    directory made if it does not exist.

    Examples:
      ```python
      from whyqd.models import SchemaModel
      from whyqd.parsers.definition import DefinitionParser

      definitions = DefinitionParser()
      schema = definitions.build(kind=SchemaModel, source="urban_population.schema")
      ```
    """

    def __init__(self) -> None:
        self.formats = FormatParser()
        self.extensions = ExtensionParser()

    def build(
        self,
        *,
        kind: type[Model],
        source: Model | dict | Path | str | None = None,
        model: Model | None = None,
    ) -> Model:
        """A model of `kind` from `source`, updating `model` where one is given.

        Parameters:
          kind: The model's class.
          source: A saved definition's path, a dictionary, or a model; with none, a new model named at random.
          model: A model whose slots `source` updates.

        Raises:
          ValueError: If `source` is none of those, or the definition declares an extension it cannot use here.
        """
        if not source:
            built = kind(name=randomname.get_name())
        elif isinstance(source, (Path, str)):
            built = kind(**self.formats.read(source=self.load(source=source)))
        elif isinstance(source, dict):
            built = kind(**self.formats.read(source=source))
        elif isinstance(source, kind):
            built = source
        else:
            raise ValueError(
                "`source` must either be a path to a source file, or a dictionary conforming to the model type."
            )
        if model:
            # Merged as dictionaries, so the result is validated anew
            merged = model.model_dump(by_alias=True, exclude_defaults=True, exclude_none=True)
            merged |= built.model_dump(exclude_unset=True)
            built = kind(**merged)
        self.extensions.check(model=built)
        return built

    def load(self, *, source: Path | str) -> dict:
        """A saved definition's JSON.

        Raises:
          FileNotFoundError: If there is no file at `source`.
          JSONDecodeError: If the file is not JSON.
        """
        with open(source, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError as e:
                raise json.decoder.JSONDecodeError(f"File at `{source}` not valid json. {e.msg}", e.doc, e.pos) from e

    def directory(self, directory: Path | str | None = None) -> Path:
        """The directory to save into, `settings.WHYQD_DIRECTORY` by default, made if it does not exist."""
        directory = Path(directory or settings.WHYQD_DIRECTORY)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def save(self, *, text: str, path: Path) -> bool:
        """Write a definition's text to `path`.

        Returns:
          `True` once written.
        """
        path.write_text(text, encoding="utf-8")
        return True
