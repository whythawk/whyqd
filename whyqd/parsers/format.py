# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import hashlib
import json

import rfc8785
from pydantic import BaseModel

from whyqd.config.settings import settings
from whyqd.dtypes import ChecksumContent, FieldType


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
    NEW = (
        "dialect",
        "profile",
        "policy",
        "termList",
        "code",
        "reason",
        "correspondence",
        "started",
        "ended",
        "whyqd",
        "references",
        "extensions",
    )
    LENGTHS = {"minimum": "minLength", "maximum": "maxLength"}
    VALUES = {v: k for k, v in LENGTHS.items()}

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
        return {self.KEY: version} | self.name_schemas(self.drop_empty_attributes(written))

    def upgrade(self, value):
        """1.x to the current format: a data source's bare checksum names what it hashed; a field's `time` is a
        `duration`; and a string field's `minimum` and `maximum`, which 1.x described as lengths, are `minLength` and
        `maxLength`."""
        if isinstance(value, list):
            return [self.upgrade(v) for v in value]
        if not isinstance(value, dict):
            return value
        value = {k: self.upgrade(v) for k, v in value.items()}
        if "mime" in value and isinstance(value.get("checksum"), str):
            value["checksums"] = [self.checksum(value=value.pop("checksum"), content=ChecksumContent.TABLE_1X)]
        for field in value.get("fields") or []:
            if field.get("type") == FieldType.TIME.value:
                field["type"] = FieldType.DURATION.value
            if field.get("type") == FieldType.STRING.value and field.get("constraints"):
                field["constraints"] = {self.LENGTHS.get(k, k): v for k, v in field["constraints"].items()}
        return value

    def downgrade(self, value):
        """The current format to 1.x, which holds one checksum per data source: the table as 1.x read it.

        The byte hash and an embedded schema's content checksum are left out, since whyqd recomputes both. An edit's
        time is written without its zone, as 1.x wrote it, being UTC. A part new in 2.0 is refused, naming it.
        """
        if isinstance(value, list):
            return [self.downgrade(v) for v in value]
        if not isinstance(value, dict):
            return value
        value = {k: self.downgrade(v) for k, v in value.items()}
        for key in self.NEW:
            if key in value:
                raise ValueError(
                    f"`{key}` on `{value.get('name') or value.get('path')}` is new in 2.0, so 1.x cannot hold it."
                )
        if isinstance(value.get("updated"), str):
            value["updated"] = value["updated"].removesuffix("Z")
        for field in value.get("fields") or []:
            self.downgrade_field(field)
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

    def downgrade_field(self, field: dict) -> None:
        """Write a field's type and bounds as 1.x names them, refusing a time of day, which 1.x's `time` is not, and a
        length on anything but a string."""
        name, kind = field.get("name"), field.get("type")
        if kind == FieldType.TIME.value:
            raise ValueError(f"Field `{name}` is a time of day, which 1.x cannot hold: its `time` is a length of time.")
        if kind == FieldType.DURATION.value:
            field["type"] = FieldType.TIME.value
        constraints = field.get("constraints") or {}
        if not any(k in constraints for k in self.VALUES):
            return
        if kind != FieldType.STRING.value:
            raise ValueError(f"Field `{name}` bounds the length of a `{kind}`, which 1.x cannot hold.")
        if any(k in constraints for k in self.LENGTHS):
            raise ValueError(f"String field `{name}` bounds both its value and its length, which 1.x cannot hold.")
        field["constraints"] = {self.VALUES.get(k, k): v for k, v in constraints.items()}

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

    def drop_empty_attributes(self, value):
        """Leave out a data source's empty `attributes`, which 1.x always wrote."""
        if isinstance(value, list):
            return [self.drop_empty_attributes(v) for v in value]
        if not isinstance(value, dict):
            return value
        return {k: self.drop_empty_attributes(v) for k, v in value.items() if not (k == "attributes" and v == {})}

    def drop_uuid(self, value):
        if isinstance(value, list):
            return [self.drop_uuid(v) for v in value]
        if not isinstance(value, dict):
            return value
        return {k: self.drop_uuid(v) for k, v in value.items() if k != "uuid"}
