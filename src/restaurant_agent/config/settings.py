from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    amap_mcp_url: str | None = None
    amap_mcp_key: str | None = None
    mcp_bearer_token: str | None = None
    restaurant_provider: str = "dianping"
    browser_harness_executable: str = "browser-harness"
