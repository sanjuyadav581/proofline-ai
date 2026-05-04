from pydantic_settings import BaseSettings
from pydantic import SecretStr
from functools import lru_cache


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_embeddings_deployment: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"

    # Postgres — no defaults for credentials (must come from .env)
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str = "hackdb"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
