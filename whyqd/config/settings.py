from pydantic import BaseSettings


class Settings(BaseSettings):
    # 10**9 == 1gb ==> try 8gb?
    # dev_shm must be aligned in docker-compose
    #   shm_size: "8gb"
    WHYQD_MEMORY: int = 8000000000
    WHYQD_CPUS: int = 2

    class Config:
        case_sensitive = True


settings = Settings()
