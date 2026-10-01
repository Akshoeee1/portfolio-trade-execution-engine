from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    FERNET_KEY: str = "Tq9FwTZHZ5KYgbltUTOH0L-5ChPF0ljohW5H9wALMsc="  # dev default, override in .env

    ZERODHA_API_KEY: str = ""
    ZERODHA_API_SECRET: str = ""

    FYERS_CLIENT_ID: str = ""
    FYERS_SECRET_KEY: str = ""
    FYERS_REDIRECT_URI: str = "http://localhost:8000/auth/fyers/callback"

    UPSTOX_CLIENT_ID: str = ""
    UPSTOX_CLIENT_SECRET: str = ""
    UPSTOX_REDIRECT_URI: str = "http://localhost:8000/auth/upstox/callback"

    ANGELONE_API_KEY: str = ""
    GROWW_API_KEY: str = ""

    NOTIFICATION_WEBHOOK_URL: str = ""  # if set, batch summaries are also POSTed here


settings = Settings()
