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
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", env_file_encoding="utf-8")


settings = Settings()
