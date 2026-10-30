from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    triplestore_url: str = "http://localhost:7878"
    triplestore_query_endpoint: str = "/query"
    triplestore_update_endpoint: str = "/update"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # Providers are selected with a "provider:model" reference. The provider
    # alone is enough: the engine falls back to a sensible default model.
    search_model: str = "openai:gpt-4.1-mini"

    database_url: str = "postgresql+psycopg://pypo:pypo@localhost:5432/pypo"
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
