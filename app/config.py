from functools import lru_cache
import logging
import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

DEFAULT_ORIGINS = [
    "https://tutall.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://ajays22-orgs.github.io",
    "https://ajays22-orgs.github.io/TUTall",
    "https://bebecpp.github.io",
    "https://bebecpp.github.io/TUTall_frontend",
]


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"", "none", "null"}:
            return default
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


class Settings(BaseSettings):
    app_name: str = Field(default="TUTall Backend", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_version: str = "1.0.0"

    enable_ai: bool = Field(default=True, validation_alias="ENABLE_AI")
    enable_cohere: bool = Field(default=True, validation_alias="ENABLE_COHERE")
    enable_openrouter: bool = Field(default=True, validation_alias="ENABLE_OPENROUTER")
    enable_gemini: bool = Field(default=False, validation_alias="ENABLE_GEMINI")
    enable_groq: bool = Field(default=False, validation_alias="ENABLE_GROQ")
    demo_mode: bool = Field(default=False, validation_alias="DEMO_MODE")

    cohere_api_key: str = Field(default="", validation_alias="COHERE_API_KEY")
    cohere_model: str = Field(default="command-r7b-12-2024", validation_alias="COHERE_MODEL")

    openrouter_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="mistralai/mistral-7b-instruct:free",
        validation_alias="OPENROUTER_MODEL",
    )

    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", validation_alias="GEMINI_MODEL")
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", validation_alias="GROQ_MODEL")

    allowed_origins: str = Field(
        default=",".join(DEFAULT_ORIGINS),
        validation_alias="ALLOWED_ORIGINS",
    )

    max_topic_length: int = Field(default=120, validation_alias="MAX_TOPIC_LENGTH")
    max_text_length: int = Field(default=800, validation_alias="MAX_TEXT_LENGTH")
    rate_limit_per_minute: int = Field(default=40, validation_alias="RATE_LIMIT_PER_MINUTE")
    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    model_config = SettingsConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("enable_ai", "enable_cohere", "enable_openrouter", mode="before")
    @classmethod
    def _parse_true_default_bool(cls, value: object) -> bool:
        return _coerce_bool(value, True)

    @field_validator("enable_gemini", "enable_groq", "demo_mode", mode="before")
    @classmethod
    def _parse_false_default_bool(cls, value: object) -> bool:
        return _coerce_bool(value, False)

    @property
    def cors_origins(self) -> list[str]:
        configured = [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]
        merged = list(dict.fromkeys([*DEFAULT_ORIGINS, *configured]))
        return merged

    @property
    def cohere_configured(self) -> bool:
        return (
            bool(self.cohere_api_key.strip())
            and self.enable_ai
            and self.enable_cohere
            and not self.demo_mode
        )

    @property
    def openrouter_configured(self) -> bool:
        return (
            bool(self.openrouter_api_key.strip())
            and self.enable_ai
            and self.enable_openrouter
            and not self.demo_mode
        )

    @property
    def gemini_configured(self) -> bool:
        return (
            bool(self.gemini_api_key.strip())
            and self.enable_ai
            and self.enable_gemini
            and not self.demo_mode
        )

    @property
    def groq_configured(self) -> bool:
        return (
            bool(self.groq_api_key.strip())
            and self.enable_ai
            and self.enable_groq
            and not self.demo_mode
        )

    @property
    def cohere_enabled(self) -> bool:
        return self.enable_ai and self.enable_cohere and not self.demo_mode

    @property
    def gemini_enabled(self) -> bool:
        return self.enable_ai and self.enable_gemini

    @property
    def groq_enabled(self) -> bool:
        return self.enable_ai and self.enable_groq

    @property
    def openrouter_enabled(self) -> bool:
        return self.enable_ai and self.enable_openrouter and not self.demo_mode

    @property
    def ai_configured(self) -> bool:
        return (
            self.cohere_configured
            or self.openrouter_configured
            or self.gemini_configured
            or self.groq_configured
        )

    @property
    def active_strategy(self) -> str:
        return "cohere -> openrouter -> gemini -> groq -> accessstem_local"

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url.strip())


def _safe_default_settings() -> Settings:
    return Settings.model_construct(
        app_name="TUTall Backend",
        app_env=os.getenv("APP_ENV", "production"),
        app_version="1.0.0",
        enable_ai=True,
        enable_cohere=True,
        enable_openrouter=True,
        enable_gemini=False,
        enable_groq=False,
        demo_mode=False,
        cohere_api_key="",
        cohere_model="command-r7b-12-2024",
        openrouter_api_key="",
        openrouter_model="mistralai/mistral-7b-instruct:free",
        gemini_api_key="",
        gemini_model="gemini-1.5-flash",
        groq_api_key="",
        groq_model="llama-3.1-8b-instant",
        allowed_origins=",".join(DEFAULT_ORIGINS),
        max_topic_length=120,
        max_text_length=800,
        rate_limit_per_minute=40,
        database_url="",
    )


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:
        logger.warning("Settings validation failed; using safe defaults (%s)", type(exc).__name__)
        return _safe_default_settings()
