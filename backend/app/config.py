from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_secret: str
    app_secret_previous: str = ""
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    cookie_secure: bool = True
    cookie_samesite: str = "none"
    public_base_url: str = "http://localhost:8000"
    mini_app_url: str = "http://localhost:8080"
    bot_token: str = ""
    admin_email: str = ""
    admin_password: str = ""
    remnawave_url: str = ""
    remnawave_token: str = ""
    yookassa_api_url: str = "https://api.yookassa.ru"
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_webhook_ip_allowlist: str = "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11,77.75.156.35,77.75.154.128/25,2a02:5180::/32"
    platega_api_url: str = "https://app.platega.io"
    platega_merchant_id: str = ""
    platega_secret: str = ""
    rollypay_api_url: str = "https://rollypay.io"
    rollypay_test_mode: bool = False
    rollypay_api_key: str = ""
    rollypay_signing_secret: str = ""
    default_currency: str = "RUB"
    admin_cors_origins: str = ""
    api_domain: str = ""
    admin_domain: str = ""
    app_domain: str = ""
    firewall_mode: str = "strict"
    yandex_client_id: str = ""
    yandex_client_secret: str = ""
    yandex_redirect_uri: str = ""
    media_dir: str = "/data/media"
    backups_dir: str = "/data/backups"
    project_dir: str = "/project"
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    backup_s3_prefix: str = "vpn-shop"
    backup_s3_enabled: bool = False
    referral_reward_percent: Decimal = Decimal("5.0")
    notification_expiry_days: int = 3
    worker_role: str = "api"
    metrics_enabled: bool = True
    remnawave_cb_failures: int = 5
    remnawave_cb_cooldown: int = 30
    auto_renew_enabled: bool = False
    alert_telegram_chat_id: str = ""
    alert_email: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    fulfillment_max_attempts: int = 8
    maintenance_mode: bool = False
    metrics_token: str = ""
    platega_refund_url: str = ""
    rollypay_refund_url: str = ""
    platega_refund_status_url: str = ""
    rollypay_refund_status_url: str = ""
    release_manifest_url: str = ""
    release_manifest_public_key: str = ""
    require_pinned_images: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
