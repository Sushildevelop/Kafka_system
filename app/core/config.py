from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_env: str
    debug: bool

    mongodb_url: str | None = None
    mongodb_write_url: str | None = None
    mongodb_read_url: str | None = None
    mongodb_database: str
    mongodb_read_preference: Literal["secondary", "secondaryPreferred"] = "secondaryPreferred"
    mongodb_write_timeout_ms: int = 5000

    kafka_bootstrap_servers: str
    kafka_topic: str
    kafka_test_partitions: int
    kafka_consumer_group: str
    kafka_auto_offset_reset: str

    kafka_chat_consumer_group: str = "study-group-chat-fanout"
    kafka_chat_partitions: int = 3
    chat_media_max_size_mb: int = 50

    google_client_id: str
    google_allowed_client_ids: str | None = None
    auth_session_secret: str
    auth_session_expire_minutes: int = 1440

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_write_url(self) -> str:
        uri = self.mongodb_write_url or self.mongodb_url
        if uri is None:
            raise ValueError("MONGODB_WRITE_URL (or legacy MONGODB_URL) is required")
        return _with_uri_options(
            uri,
            {
                "readPreference": "primary",
                "w": "majority",
                "wtimeoutMS": self.mongodb_write_timeout_ms,
            },
        )

    @property
    def database_read_url(self) -> str:
        uri = self.mongodb_read_url or self.mongodb_write_url or self.mongodb_url
        if uri is None:
            raise ValueError("MONGODB_READ_URL or a write URL must be configured")
        return _with_uri_options(
            uri,
            {
                "readPreference": self.mongodb_read_preference,
                "readConcernLevel": "majority",
            },
        )

    @property
    def google_audiences(self) -> list[str]:
        values = [self.google_client_id]
        if self.google_allowed_client_ids:
            values.extend(
                value.strip()
                for value in self.google_allowed_client_ids.split(",")
                if value.strip()
            )
        return list(dict.fromkeys(values))


def _with_uri_options(uri: str, options: dict[str, str | int]) -> str:
    parts = urlsplit(uri)
    names = {key.lower() for key in options}
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in names
    ]
    query.extend((key, str(value)) for key, value in options.items())
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path or "/", urlencode(query), parts.fragment)
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
