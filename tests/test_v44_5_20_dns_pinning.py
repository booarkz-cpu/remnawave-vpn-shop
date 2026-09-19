from pathlib import Path
import ast
import asyncio
import ipaddress
import socket

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / 'backend/app/main.py'
MAIN = MAIN_PATH.read_text()


def _security_helpers_namespace():
    tree = ast.parse(MAIN)
    wanted = {'_PinnedPublicDNSBackend', '_pinned_public_http_client', '_resolve_public_host'}
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in wanted]
    class _HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code=status_code; self.detail=detail
            super().__init__(detail)
    ns = {'ipaddress': ipaddress, 'socket': socket, 'HTTPException': _HTTPException}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(MAIN_PATH), 'exec'), ns)
    return ns


def test_monitoring_uses_pinned_transport_and_disables_proxy_env():
    block = MAIN[MAIN.index('async def monitor_checks_scheduler()'):MAIN.index('# ---------- Enterprise suite V44')]
    helper = MAIN[MAIN.index('class _PinnedPublicDNSBackend'):MAIN.index('def validate_public_url')]
    assert '_pinned_public_http_client' in block
    assert 'trust_env=False' in helper
    assert 'follow_redirects=False' in helper
    assert '_pool._network_backend=_PinnedPublicDNSBackend()' in helper
    assert 'return await self._backend.connect_tcp(target,port,timeout,local_address,socket_options)' in helper


def test_public_dns_validation_rejects_any_non_global_answer(monkeypatch):
    ns = _security_helpers_namespace()
    def fake_getaddrinfo(host, port, type=None):
        return [
            (2, 1, 6, '', ('93.184.216.34', port)),
            (2, 1, 6, '', ('10.0.0.7', port)),
        ]
    monkeypatch.setattr(socket, 'getaddrinfo', fake_getaddrinfo)
    try:
        ns['_resolve_public_host']('example.test', 443)
    except Exception as exc:
        assert 'private or local' in str(exc)
    else:
        raise AssertionError('mixed public/private DNS answers must be rejected')


def test_pinned_backend_connects_to_checked_literal(monkeypatch):
    ns = _security_helpers_namespace()
    seen = {}
    import httpcore
    async def fake_connect(self, host, port, timeout=None, local_address=None, socket_options=None):
        seen['host'] = host
        seen['port'] = port
        return object()
    monkeypatch.setattr(httpcore.AnyIOBackend, 'connect_tcp', fake_connect)
    monkeypatch.setattr(socket, 'getaddrinfo', lambda host, port, type=None: [
        (2, 1, 6, '', ('93.184.216.34', port)),
    ])
    backend = ns['_PinnedPublicDNSBackend']()
    asyncio.run(backend.connect_tcp('example.test', 443, timeout=1))
    assert seen == {'host': '93.184.216.34', 'port': 443}
