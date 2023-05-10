from pydantic import BaseSettings


class Settings(BaseSettings):
    # 10**9 == 1gb ==> try 8gb?
    # dev_shm must be aligned in docker-compose
    #   shm_size: "8gb"
    WHYQD_MEMORY: int = 6000000000
    WHYQD_CPUS: int = 3
    WHYQD_SPILLWAY: str = "/tmp/spill"
    WHYQD_DIRECTORY: str = ""
    WHYQD_DEFAULT_MIMETYPE: str = "application/vnd.apache.parquet"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
