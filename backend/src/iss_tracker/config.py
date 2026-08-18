from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tle_url: str = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle"
    tle_cache_ttl_seconds: int = 7_200
    tle_hard_expiry_seconds: int = 259_200
    tle_stale_warning_seconds: int = 86_400
    tle_fetch_timeout_seconds: float = 10.0

    satellite_name: str = "ISS (ZARYA)"

    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    log_level: str = "INFO"

    stream_interval_seconds: float = 1.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
