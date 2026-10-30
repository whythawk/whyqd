# SPDX-License-Identifier: BSD-3-Clause
from pydantic import Field
from typing import ClassVar, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    WHYQD_DIRECTORY: Optional[str] = Field(default="")
    WHYQD_DEFAULT_MIMETYPE: Optional[str] = Field(default="application/vnd.apache.parquet")
    # Fixed by the code, so no environment variable reaches them: a whyqd told it reads a format it has no code for
    # would drop that format's keys, and a renamed algorithm would stop every stored checksum verifying
    FORMAT_VERSIONS: ClassVar[tuple[str, ...]] = ("1.x", "2.0")
    FORMAT_CURRENT: ClassVar[str] = "2.0"
    CHECKSUM_ALGORITHM: ClassVar[str] = "BLAKE2b-512"
    # The encodings a dialect may declare, by the WHATWG Encoding Standard's name in lower case, each with its labels
    # (https://encoding.spec.whatwg.org/#names-and-labels) and the Python codec that decodes it as the standard does
    ENCODINGS: ClassVar[dict[str, dict]] = {
        "utf-8": {
            "codec": "utf-8",
            "labels": ("unicode-1-1-utf-8", "unicode11utf8", "unicode20utf8", "utf-8", "utf8", "x-unicode20utf8"),
        },
        "utf-16le": {
            "codec": "utf-16-le",
            "labels": ("csunicode", "iso-10646-ucs-2", "ucs-2", "unicode", "unicodefeff", "utf-16", "utf-16le"),
        },
        "utf-16be": {"codec": "utf-16-be", "labels": ("unicodefffe", "utf-16be")},
        "windows-1252": {
            "codec": "cp1252",
            "labels": (
                "ansi_x3.4-1968", "ascii", "cp1252", "cp819", "csisolatin1", "ibm819", "iso-8859-1", "iso-ir-100",
                "iso8859-1", "iso88591", "iso_8859-1", "iso_8859-1:1987", "l1", "latin1", "us-ascii",
                "windows-1252", "x-cp1252",
            ),
        },
        "macintosh": {"codec": "mac_roman", "labels": ("csmacintosh", "mac", "macintosh", "x-mac-roman")},
    }
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", env_file_encoding="utf-8")


settings = Settings()
