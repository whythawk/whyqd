# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
from collections import Counter
from importlib.metadata import PackageNotFoundError, entry_points, version

from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pydantic import BaseModel

from whyqd.dtypes import ExtensionKind, FieldType
from whyqd.models import CrosswalkModel, ExtensionModel, SchemaModel


class ExtensionParser:
    """Actions and types whyqd does not include, provided by installed packages.

    A package registers each through a Python
    [entry point](https://packaging.python.org/en/latest/specifications/entry-points/), in the group
    `whyqd.actions` or `whyqd.types`, named as a definition writes it. A definition declares every extension it uses,
    and reading one fails, naming what is wrong, never falling back: a declared package that is not installed, an
    installed version outside the declared range, two declarations of one name, or a declaration under a built-in's
    name. An installed pre-release counts as installed, as the
    [version specifier standard](https://packaging.python.org/en/latest/specifications/version-specifiers/#handling-of-pre-releases)
    has it.

    Example:
      ```python
      from whyqd.parsers.extension import ExtensionParser

      extensions = ExtensionParser()
      declaration = extensions.declare(name="NORMALISE_ADDRESS", kind="action")
      # ExtensionModel(name="NORMALISE_ADDRESS", kind="action", distribution="whyqd-postal", version=">=1.2.3,<2")
      ```
    """

    def declare(self, *, name: str, kind: ExtensionKind | str, distribution: str | None = None) -> ExtensionModel:
        """Declare an installed extension, accepting its installed version up to the next major one.

        Parameters:
          name: The action's or type's name.
          kind: `action` or `type`.
          distribution: The package providing it; needed only where two installed packages provide the name.

        Raises:
          ValueError: If no installed package provides it, or several do and `distribution` does not say which.
        """
        kind = ExtensionKind(kind)
        found = [
            e for e in entry_points(group=kind.group, name=name) if not distribution or e.dist.name == distribution
        ]
        if not found:
            raise ValueError(f"No installed package provides the {kind.value} `{name}` in `{kind.group}`.")
        if len(found) > 1:
            raise ValueError(
                f"Several packages provide the {kind.value} `{name}`: {', '.join(e.dist.name for e in found)}. "
                "Name the one to use as `distribution`."
            )
        installed = Version(found[0].dist.version)
        return ExtensionModel(
            name=name,
            kind=kind,
            distribution=found[0].dist.name,
            version=f">={installed},<{installed.major + 1}",
        )

    def check(self, *, model: BaseModel) -> None:
        """Refuse a definition whose extensions, or those of any schema or crosswalk it holds, cannot be used here."""
        declared = self.declared(model)
        names = Counter((e.kind, e.name) for e in declared)
        for (kind, name), count in names.items():
            if count > 1:
                raise ValueError(f"The {kind} `{name}` is declared {count} times; a definition names each once.")
            if name in self.builtins(kind=ExtensionKind(kind)):
                raise ValueError(f"The {kind} `{name}` is one of whyqd's own, so no extension may take its name.")
        for extension in declared:
            try:
                installed = version(extension.distribution)
            except PackageNotFoundError:
                raise ValueError(
                    f"The {extension.kind} `{extension.name}` needs `{extension.distribution}`, which is not installed."
                ) from None
            if not SpecifierSet(extension.version).contains(installed, prereleases=True):
                raise ValueError(
                    f"The {extension.kind} `{extension.name}` needs `{extension.distribution}` "
                    f"{extension.version}, and {installed} is installed."
                )
            group = ExtensionKind(extension.kind).group
            if not any(e.dist.name == extension.distribution for e in entry_points(group=group, name=extension.name)):
                raise ValueError(
                    f"`{extension.distribution}` does not provide the {extension.kind} `{extension.name}` in `{group}`."
                )

    def declared(self, model: BaseModel) -> list[ExtensionModel]:
        """Every declaration in a schema or crosswalk, and in those it embeds; a transform's record is not one."""
        found = list(model.extensions) if isinstance(model, (SchemaModel, CrosswalkModel)) else []
        for name in type(model).model_fields:
            value = getattr(model, name)
            if isinstance(value, (SchemaModel, CrosswalkModel)):
                found += self.declared(value)
        return found

    def builtins(self, *, kind: ExtensionKind) -> set[str]:
        if kind is ExtensionKind.TYPE:
            return {t.value for t in FieldType}
        # The actions import whyqd's parsers, so they are found once those have loaded
        from whyqd.crosswalk.actions import actions

        return set(actions)
