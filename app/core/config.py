from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Warehouse Management System"
    database_url: str = "sqlite:///./warehouse.db"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30


settings = Settings()
