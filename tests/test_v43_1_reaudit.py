from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/"backend/app/main.py").read_text()

def test_menu_field_buttons_validate_existing_enabled_field():
    assert 'Кнопка field ссылается на неизвестное или отключённое поле' in MAIN
    assert 'select(CustomField.id).where(CustomField.key==payload.action,CustomField.enabled.is_(True))' in MAIN

def test_menu_count_is_bounded():
    assert 'if existing_count>=30: raise HTTPException(400,"Можно настроить не более 30 кнопок")' in MAIN

def test_media_directories_are_created_before_write():
    assert 'pathlib.Path(settings.media_dir).mkdir(parents=True,exist_ok=True)' in MAIN

def test_connection_info_has_no_unreachable_duplicate_return():
    marker='async def connection_info'
    section=MAIN.split(marker,1)[1].split('@app.put("/api/me/auto-renew")',1)[0]
    assert section.count('return Response(')==1
    assert 'return {"subscription_url":sub.subscription_url' not in section

def test_production_gate_requires_full_e2e():
    assert 'status.get("status")!="passed" or not status.get("full_e2e")' in MAIN
