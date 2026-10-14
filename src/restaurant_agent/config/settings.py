from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    amap_mcp_url: str | None = None
    amap_mcp_key: str | None = None
    mcp_bearer_token: str | None = None
    restaurant_provider: str = "dianping"
    browser_harness_executable: str = "browser-harness"
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_api_base_url: str = "https://open.feishu.cn/open-apis"
