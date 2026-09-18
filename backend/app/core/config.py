from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "MeetMind AI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-5-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
