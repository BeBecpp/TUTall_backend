from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

DEFAULT_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ajays22-orgs.github.io",
    "https://ajays22-orgs.github.io/TUTall",
    "https://bebecpp.github.io",
    "https://bebecpp.github.io/TUTall_frontend",
]


class Settings(BaseSettings):
    app_name: str = Field(default="TUTall Backend", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_version: str = "1.0.0"

    enable_ai: bool = Field(default=True, validation_alias="ENABLE_AI")
    enable_openrouter: bool = Field(default=True, validation_alias="ENABLE_OPENROUTER")
    enable_gemini: bool = Field(default=False, validation_alias="ENABLE_GEMINI")
    enable_groq: bool = Field(default=False, validation_alias="ENABLE_GROQ")
    demo_mode: bool = Field(default=False, validation_alias="DEMO_MODE")

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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

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
    def openrouter_configured(self) -> bool:
        return (
            bool(self.openrouter_api_key.strip())
            and self.enable_ai
            and self.enable_openrouter
            and not self.demo_mode
        )

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip()) and self.enable_ai and self.enable_gemini

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key.strip()) and self.enable_ai and self.enable_groq

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
        return self.openrouter_configured or self.gemini_configured or self.groq_configured

    @property
    def active_strategy(self) -> str:
        return "openrouter -> accessstem_local"

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
