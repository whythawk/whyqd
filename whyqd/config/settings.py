from pydantic import Field
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 10**9 == 1gb ==> try 8gb?
    # dev_shm must be aligned in docker-compose, e.g.
    #   shm_size: "8gb"
    WHYQD_MEMORY: Optional[int] = Field(default=None)
    WHYQD_CPUS: Optional[int] = Field(default=None)
    WHYQD_SPILLWAY: Optional[str] = Field(default="/spill")
    WHYQD_DIRECTORY: Optional[str] = Field(default="")
    WHYQD_DEFAULT_MIMETYPE: Optional[str] = Field(default="application/vnd.apache.parquet")
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", env_file_encoding="utf-8")


settings = Settings()
