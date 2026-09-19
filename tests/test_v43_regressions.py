from pathlib import Path
ROOT=Path(__file__).parents[1]
def read(rel): return (ROOT/rel).read_text()

def test_admin_content_never_returns_raw_all_settings():
    s=read('backend/app/main.py'); part=s[s.index('async def admin_content'):s.index('async def admin_setting')]
    assert 'select(AppSetting).where(AppSetting.key.in_(safe_keys|secret_keys))' in part
    assert 'setting_values={x.key:x.value for x in ss if x.key in safe_keys}' in part
    assert 'return {"settings":setting_values,"secret_status":secret_status' in part

def test_menu_urls_are_https_only_and_typed():
    s=read('backend/app/main.py')
    assert 'pattern="^(webapp|url|field)$"' in s
    b=read('backend/app/bot.py')
    assert 'if not url.startswith("https://"): continue' in b
    assert 'if not m.action.startswith("https://"): continue' in b

def test_miniapp_buttons_are_bounded_and_field_references_validated():
    s=read('backend/app/main.py')
    assert 'if len(payload.buttons)>30' in s
    assert 'b.get("field_key") not in field_keys' in s
