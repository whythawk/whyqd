# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import hashlib
import json

import rfc8785
from pydantic import BaseModel

from whyqd.config.settings import settings
from whyqd.dtypes import ChecksumContent


class FormatParser:
    """Read and write the definition formats whyqd knows.

    A saved definition names its format in `formatVersion`, at the top of the file; a file without one is 1.x.
    Reading upgrades a definition to the current format in memory, and writing gives the current format unless an
    older one is asked for. A definition holding anything the older format cannot is refused, never cut down.

    Example:
      ```python
      from whyqd.parsers.format import FormatParser

      formats = FormatParser()
      upgraded = formats.read(source={"path": "data.csv", "checksum": "1f2e…", ...})
      formats.write(model=model, format="1.x")
      ```
    """

    KEY = "formatVersion"
    SCHEMAS = ("schemaSource", "schemaDestination")

    def check(self, *, version: str) -> None:
        if version not in settings.FORMAT_VERSIONS:
            raise ValueError(
                f"Definition format `{version}` is not one this whyqd reads or writes. "
                f"It knows {', '.join(settings.FORMAT_VERSIONS)}."
            )

    def dumps(self, written: dict) -> str:
        """Serialise a written definition as compact JSON."""
        return json.dumps(written, separators=(",", ":"), ensure_ascii=False)

    def checksum(self, *, value: str, content: ChecksumContent) -> dict:
        return {"algorithm": settings.CHECKSUM_ALGORITHM, "checksumValue": value, "content": content.value}

    def read(self, *, source: dict) -> dict:
        """Return a saved definition in the current format, refusing one newer than this whyqd knows."""
        source = dict(source)
        version = source.pop(self.KEY, "1.x")
        self.check(version=version)
        if version == "1.x":
            return self.upgrade(source)
        return source

    def write(self, *, model: BaseModel, format: str | None = None, hide_uuid: bool = False) -> dict:
        """Return a definition as `format` writes it, by default the current one."""
        version = format or settings.FORMAT_CURRENT
        self.check(version=version)
        written = model.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        if hide_uuid:
            written = self.drop_uuid(written)
        if version == "1.x":
            return self.downgrade(written)
        return {self.KEY: version} | self.name_schemas(written)

    def upgrade(self, value):
        """1.x to the current format: a data source's bare checksum names what it hashed."""
        if isinstance(value, list):
            return [self.upgrade(v) for v in value]
        if not isinstance(value, dict):
            return value
        value = {k: self.upgrade(v) for k, v in value.items()}
        if "mime" in value and isinstance(value.get("checksum"), str):
            value["checksums"] = [self.checksum(value=value.pop("checksum"), content=ChecksumContent.TABLE_1X)]
        return value

    def downgrade(self, value):
        """The current format to 1.x, which holds one checksum per data source: the table as 1.x read it.

        The byte hash and an embedded schema's content checksum are left out, since whyqd recomputes both.
        """
        if isinstance(value, list):
            return [self.downgrade(v) for v in value]
        if not isinstance(value, dict):
            return value
        value = {k: self.downgrade(v) for k, v in value.items()}
        for key in self.SCHEMAS:
            if isinstance(value.get(key), dict):
                value[key].pop("checksums", None)
        if "mime" in value and "checksums" in value:
            table = [c for c in value.pop("checksums") if c["content"] == ChecksumContent.TABLE_1X.value]
            if not table:
                raise ValueError(
                    f"`{value.get('path')}` has no `table-1x` checksum among its `checksums`, so 1.x cannot hold it."
                )
            value["checksum"] = table[0]["checksumValue"]
        return value

    def name_schemas(self, value):
        """Give each embedded schema a checksum of its content, so two versions under one uuid are told apart."""
        if isinstance(value, list):
            return [self.name_schemas(v) for v in value]
        if not isinstance(value, dict):
            return value
        value = {k: self.name_schemas(v) for k, v in value.items()}
        for key in self.SCHEMAS:
            schema = value.get(key)
            if isinstance(schema, dict):
                content = {k: v for k, v in schema.items() if k not in {"version", "checksums"}}
                digest = hashlib.blake2b(rfc8785.dumps(content)).hexdigest()
                schema["checksums"] = [self.checksum(value=digest, content=ChecksumContent.DEFINITION)]
        return value

    def drop_uuid(self, value):
        if isinstance(value, list):
            return [self.drop_uuid(v) for v in value]
        if not isinstance(value, dict):
            return value
        return {k: self.drop_uuid(v) for k, v in value.items() if k != "uuid"}
