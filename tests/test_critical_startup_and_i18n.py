from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_settings_cover_paths_used_at_import_and_backup():
    cfg = (ROOT / "backend/app/config.py").read_text()
    for snippet in [
        'alias="MEDIA_DIR"',
        'default="/data/media"',
        'alias="BACKUPS_DIR"',
        'default="/data/backups"',
        'alias="PROJECT_DIR"',
        'default="/project"',
        'alias="BACKUP_S3_PREFIX"',
        'alias="YANDEX_CLIENT_ID"',
        'alias="YANDEX_CLIENT_SECRET"',
        'alias="YANDEX_REDIRECT_URI"',
        'alias="VK_CLIENT_ID"',
        'alias="CABINET_URL"',
        'alias="CABINET_DOMAIN"',
        'alias="PAYMENTS_SANDBOX"',
        'alias="MAINTENANCE_MODE"',
        'default=False, alias="MAINTENANCE_MODE"',
        'alias="DEFAULT_LANGUAGE"',
    ]:
        assert snippet in cfg


def test_invalid_content_length_has_json_response_in_scope():
    main = (ROOT / "backend/app/main.py").read_text()
    dispatch = main[main.index("async def _dispatch"):main.index("response = await call_next(request)")]
    assert dispatch.index("from fastapi.responses import JSONResponse") < dispatch.index("Invalid Content-Length")


def test_yookassa_webhook_ip_allowlist_fails_closed():
    main = (ROOT / "backend/app/main.py").read_text()
    payments = (ROOT / "backend/app/payments.py").read_text()
    assert 'if not settings.yookassa_webhook_ip_allowlist or not _ip_allowed(client_ip,settings.yookassa_webhook_ip_allowlist): raise HTTPException(403,"Webhook IP not allowed")' in main
    assert "YooKassa webhook IP allowlist is not configured" in payments
    assert "Missing remote address for YooKassa webhook" in payments


def test_media_deletion_uses_basename_only():
    main = (ROOT / "backend/app/main.py").read_text()
    assert 'pathlib.Path(old.removeprefix("/media/")).name' in main
    assert 'pathlib.Path(settings.media_dir,old.removeprefix("/media/"))' not in main
    assert 'pathlib.Path(settings.media_dir,row.value.removeprefix("/media/"))' not in main


def test_admin_enterprise_view_compiles_as_jsx_and_keeps_labels():
    admin = (ROOT / "admin/src/main.tsx").read_text()
    assert "<Корпоративный контур" not in admin
    assert "<Корпоративный d={d}" in admin
    for label in ["Корпоративный контур", "Брендинг панели", "Переключить тему", "Операции", "Аналитика", "Инциденты", "Провайдеры", "Клиенты", "Функции", "Ключи доступа", "24/7 мониторинг", "Campaign Manager", "Rules Engine", "мультиустройства", "Trial", "Личный кабинет"]:
        assert label in admin
    assert '"status"' in admin and '"deployments"' in admin and '"notifications"' in admin
    assert "CabinetCMS" in admin
    style = (ROOT / "admin/src/style.css").read_text()
    assert "--primary: #00e5c0" in style
    assert "Sora" in style
    assert "#6d5dfc" not in style
    assert "#4f6cff" not in style


def test_interfaces_have_russian_and_english_catalogs():
    admin_i18n = (ROOT / "admin/src/i18n.tsx").read_text()
    mini_i18n = (ROOT / "miniapp/src/i18n.tsx").read_text()
    mini = (ROOT / "miniapp/src/main.tsx").read_text()
    bot = (ROOT / "backend/app/bot.py").read_text()
    assert "export type Lang = \"ru\" | \"en\"" in admin_i18n
    assert "Sign in" in admin_i18n and "Войти" in admin_i18n
    assert "Referral program" in mini_i18n and "Реферальная программа" in mini
    assert "Автопродление" in mini
    assert '"en"' in bot and "Welcome to {name}!" in bot and "Добро пожаловать в {name}!" in bot
