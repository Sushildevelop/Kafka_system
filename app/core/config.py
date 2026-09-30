from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_env: str
    debug: bool

    # MONGODB_URL is retained only as a safe migration path for the previous
    # single-client configuration. New deployments must set the explicit URLs.
    mongodb_url: str | None = None
    mongodb_write_url: str | None = None
    mongodb_read_url: str | None = None
    mongodb_database: str
    mongodb_read_preference: Literal["secondary", "secondaryPreferred"] = (
        "secondaryPreferred"
    )
    mongodb_write_timeout_ms: int = 5000

    kafka_bootstrap_servers: str
    kafka_topic: str
    kafka_test_partitions: int
    kafka_consumer_group: str
    kafka_auto_offset_reset: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_write_url(self) -> str:
        """Return a URI that pins operations to the primary with durable writes."""
        database_url = self.mongodb_write_url or self.mongodb_url
        if database_url is None:
            raise ValueError("MONGODB_WRITE_URL (or legacy MONGODB_URL) is required")
        return _with_uri_options(
            database_url,
            {
                "readPreference": "primary",
                "w": "majority",
                "wtimeoutMS": self.mongodb_write_timeout_ms,
            },
        )

    @property
    def database_read_url(self) -> str:
        """Prefer a secondary for reads, using the write URI as a seed fallback."""
        read_url = self.mongodb_read_url or self.mongodb_write_url or self.mongodb_url
        if read_url is None:
            raise ValueError("MONGODB_READ_URL or a write URL must be configured")
        return _with_uri_options(
            read_url,
            {
                "readPreference": self.mongodb_read_preference,
                "readConcernLevel": "majority",
            },
        )


def _with_uri_options(uri: str, options: dict[str, str | int]) -> str:
    parts = urlsplit(uri)
    option_names = {key.lower() for key in options}
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in option_names
    ]
    query.extend((key, str(value)) for key, value in options.items())
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path or "/", urlencode(query), parts.fragment)
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
