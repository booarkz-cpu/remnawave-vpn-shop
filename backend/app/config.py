"""
Конфигурация приложения.

Все значения читаются из переменных окружения или из файла .env
(см. .env.example).
"""
from __future__ import annotations

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- Приложение ----------
    app_secret: str = Field(default="change-me", alias="APP_SECRET")
    app_secret_previous: str = Field(default="", alias="APP_SECRET_PREVIOUS")
    app_env: str = Field(default="production", alias="APP_ENV")
    default_language: str = Field(default="ru", alias="DEFAULT_LANGUAGE")
    tz: str = Field(default="Europe/Moscow", alias="TZ")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ---------- PostgreSQL ----------
    db_user: str = Field(default="vpnshop", alias="DB_USER")
    db_password: str = Field(default="change-me", alias="DB_PASSWORD")
    db_name: str = Field(default="vpnshop", alias="DB_NAME")
    database_url: str = Field(
        default="postgresql+asyncpg://vpnshop:change-me@db:5432/vpnshop",
        alias="DATABASE_URL",
    )

    # ---------- Redis ----------
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")

    # ---------- Telegram ----------
    bot_token: str = Field(default="", alias="BOT_TOKEN")
    bot_username: str = Field(default="", alias="BOT_USERNAME")
    admin_telegram_id: int = Field(default=0, alias="ADMIN_TELEGRAM_ID")

    # ---------- Remnawave ----------
    remnawave_url: str = Field(default="", alias="REMNAWAVE_URL")
    remnawave_token: str = Field(default="", alias="REMNAWAVE_TOKEN")
    remnawave_cb_failures: int = Field(default=5, alias="REMNAWAVE_CB_FAILURES")
    remnawave_cb_cooldown: int = Field(default=30, alias="REMNAWAVE_CB_COOLDOWN")

    # ---------- Админ-панель ----------
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="change-me", alias="ADMIN_PASSWORD")
    admin_cors_origins: str = Field(
        default="", alias="ADMIN_CORS_ORIGINS"
    )
    public_base_url: str = Field(
        default="https://api.example.com", alias="PUBLIC_BASE_URL"
    )
    mini_app_url: str = Field(
        default="https://app.example.com", alias="MINI_APP_URL"
    )
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="none", alias="COOKIE_SAMESITE")

    # ---------- Домены ----------
    admin_domain: str = Field(default="localhost", alias="ADMIN_DOMAIN")
    app_domain: str = Field(default="localhost", alias="APP_DOMAIN")
    api_domain: str = Field(default="localhost", alias="API_DOMAIN")
    miniapp_domain: str = Field(default="localhost", alias="MINIAPP_DOMAIN")
    bot_domain: str = Field(default="localhost", alias="BOT_DOMAIN")
    webhook_domain: str = Field(default="localhost", alias="WEBHOOK_DOMAIN")
    panel_domain: str = Field(default="localhost", alias="PANEL_DOMAIN")
    caddy_email: str = Field(
        default="admin@example.com", alias="CADDY_EMAIL"
    )
    caddy_http_port: int = Field(default=80, alias="CADDY_HTTP_PORT")
    caddy_https_port: int = Field(default=443, alias="CADDY_HTTPS_PORT")

    # ---------- Валюта и цены ----------
    default_currency: str = Field(default="RUB", alias="DEFAULT_CURRENCY")
    price_1: int = Field(default=199, alias="PRICE_1")
    price_3: int = Field(default=499, alias="PRICE_3")
    price_6: int = Field(default=899, alias="PRICE_6")
    price_12: int = Field(default=1499, alias="PRICE_12")

    # ---------- YooKassa ----------
    yookassa_api_url: str = Field(
        default="https://api.yookassa.ru", alias="YOOKASSA_API_URL"
    )
    yookassa_shop_id: str = Field(default="", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(
        default="", alias="YOOKASSA_SECRET_KEY"
    )
    yookassa_webhook_ip_allowlist: str = Field(
        default="", alias="YOOKASSA_WEBHOOK_IP_ALLOWLIST"
    )

    # ---------- Platega ----------
    platega_api_url: str = Field(
        default="https://app.platega.io", alias="PLATEGA_API_URL"
    )
    platega_merchant_id: str = Field(
        default="", alias="PLATEGA_MERCHANT_ID"
    )
    platega_secret: str = Field(default="", alias="PLATEGA_SECRET")
    platega_refund_url: str = Field(
        default="", alias="PLATEGA_REFUND_URL"
    )
    platega_refund_status_url: str = Field(
        default="", alias="PLATEGA_REFUND_STATUS_URL"
    )

    # ---------- RollyPay ----------
    rollypay_api_url: str = Field(
        default="https://rollypay.io", alias="ROLLYPAY_API_URL"
    )
    rollypay_api_key: str = Field(default="", alias="ROLLYPAY_API_KEY")
    rollypay_signing_secret: str = Field(
        default="", alias="ROLLYPAY_SIGNING_SECRET"
    )
    rollypay_test_mode: bool = Field(
        default=False, alias="ROLLYPAY_TEST_MODE"
    )
    rollypay_refund_url: str = Field(
        default="", alias="ROLLYPAY_REFUND_URL"
    )
    rollypay_refund_status_url: str = Field(
        default="", alias="ROLLYPAY_REFUND_STATUS_URL"
    )

    # ---------- CryptoBot ----------
    cryptobot_token: str = Field(default="", alias="CRYPTOBOT_TOKEN")
    cryptobot_network: str = Field(
        default="mainnet", alias="CRYPTOBOT_NETWORK"
    )

    # ---------- Stripe ----------
    stripe_secret_key: str = Field(
        default="", alias="STRIPE_SECRET_KEY"
    )
    stripe_webhook_secret: str = Field(
        default="", alias="STRIPE_WEBHOOK_SECRET"
    )

    # ---------- Вебхуки ----------
    webhook_base_url: str = Field(
        default="https://shop.example.com", alias="WEBHOOK_BASE_URL"
    )

    # ---------- Бизнес-логика ----------
    referral_reward_percent: float = Field(
        default=5.0, alias="REFERRAL_REWARD_PERCENT"
    )
    notification_expiry_days: int = Field(
        default=3, alias="NOTIFICATION_EXPIRY_DAYS"
    )
    auto_renew_enabled: bool = Field(
        default=False, alias="AUTO_RENEW_ENABLED"
    )
    fulfillment_max_attempts: int = Field(
        default=8, alias="FULFILLMENT_MAX_ATTEMPTS"
    )
    worker_role: str = Field(default="worker", alias="WORKER_ROLE")

    # ---------- S3 ----------
    backup_s3_enabled: bool = Field(
        default=False, alias="BACKUP_S3_ENABLED"
    )
    s3_endpoint_url: str = Field(default="", alias="S3_ENDPOINT_URL")
    s3_bucket: str = Field(default="", alias="S3_BUCKET")
    s3_region: str = Field(default="auto", alias="S3_REGION")
    s3_access_key: str = Field(default="", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="S3_SECRET_KEY")

    # ---------- Мониторинг ----------
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    metrics_token: str = Field(default="", alias="METRICS_TOKEN")
    alert_telegram_chat_id: str = Field(
        default="", alias="ALERT_TELEGRAM_CHAT_ID"
    )
    alert_email: str = Field(default="", alias="ALERT_EMAIL")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM")

    # ---------- Безопасность ----------
    firewall_mode: str = Field(default="strict", alias="FIREWALL_MODE")
    require_pinned_images: bool = Field(
        default=True, alias="REQUIRE_PINNED_IMAGES"
    )

    # ---------- Образы ----------
    python_base_image: str = Field(default="", alias="PYTHON_BASE_IMAGE")
    node_base_image: str = Field(default="", alias="NODE_BASE_IMAGE")
    nginx_base_image: str = Field(default="", alias="NGINX_BASE_IMAGE")
    redis_image: str = Field(default="", alias="REDIS_IMAGE")
    postgres_image: str = Field(default="", alias="POSTGRES_IMAGE")
    caddy_image: str = Field(default="", alias="CADDY_IMAGE")

    # ---------- Релизы ----------
    release_manifest_url: str = Field(
        default="", alias="RELEASE_MANIFEST_URL"
    )
    release_manifest_public_key: str = Field(
        default="", alias="RELEASE_MANIFEST_PUBLIC_KEY"
    )

    # ---------- Порты ----------
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    admin_port: int = Field(default=3000, alias="ADMIN_PORT")
    miniapp_port: int = Field(default=8080, alias="MINIAPP_PORT")

    # ---------- Файлы и каталоги ----------
    # Docker Compose монтирует эти пути в backend/worker. Не меняйте их,
    # если не меняете volumes в docker-compose.yml.
    media_dir: str = Field(default="/data/media", alias="MEDIA_DIR")
    backups_dir: str = Field(default="/data/backups", alias="BACKUPS_DIR")
    project_dir: str = Field(default="/project", alias="PROJECT_DIR")
    backup_s3_prefix: str = Field(default="vpn-shop", alias="BACKUP_S3_PREFIX")

    # ---------- Yandex ID ----------
    yandex_client_id: str = Field(default="", alias="YANDEX_CLIENT_ID")
    yandex_client_secret: str = Field(default="", alias="YANDEX_CLIENT_SECRET")
    yandex_redirect_uri: str = Field(default="", alias="YANDEX_REDIRECT_URI")

    # Жёсткий env-флаг. Операционный режим также хранится в настройке БД maintenance_mode.
    maintenance_mode: bool = Field(default=False, alias="MAINTENANCE_MODE")

    # ---------- Валидаторы ----------
    @field_validator("admin_cors_origins", mode="before")
    @classmethod
    def _normalize_cors(cls, v: object) -> object:
        """Убираем пробелы и пустые элементы."""
        if isinstance(v, str):
            return ",".join(
                part.strip() for part in v.split(",") if part.strip()
            )
        return v

    def admin_cors_origins_list(self) -> List[str]:
        """Вернуть список origin'ов для CORS middleware."""
        if not self.admin_cors_origins:
            return []
        return [
            o.strip()
            for o in self.admin_cors_origins.split(",")
            if o.strip()
        ]


settings = Settings()
