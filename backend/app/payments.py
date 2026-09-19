from abc import ABC, abstractmethod
import uuid, hmac, hashlib, time
from decimal import Decimal
import httpx
from .config import settings


def _public_client(timeout_seconds: int):
    """Create an outbound HTTPS client with DNS pinning and redirects disabled.

    Payment-provider URLs are security-sensitive: validation at configuration time alone
    does not prevent DNS rebinding between validation and the actual request. The helper
    resolves/pins the public address at connection time while preserving the TLS hostname.
    """
    from .main import _pinned_public_http_client
    return _pinned_public_http_client(timeout_seconds)

class PaymentProvider(ABC):
    name: str
    @abstractmethod
    async def create(self, amount, order_id, description, return_url): ...
    @abstractmethod
    async def refund(self, payment_id, amount, currency, description="VPN Shop refund"): ...
    @abstractmethod
    async def get_refund_status(self, refund_id: str): ...
    @abstractmethod
    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, expected_currency: str, expected_order_id: str|None = None): ...

class YooKassaProvider(PaymentProvider):
    name = "yookassa"
    async def create(self, amount, order_id, description, return_url):
        payload = {
            "amount":{"value":f"{amount:.2f}","currency":settings.default_currency},
            "capture":True,
            "save_payment_method":True,
            "confirmation":{"type":"redirect","return_url":return_url},
            "description":description,
            "metadata":{"order_id":order_id}
        }
        async with _public_client(20) as c:
            r=await c.post(settings.yookassa_api_url.rstrip("/")+"/v3/payments", auth=(settings.yookassa_shop_id,settings.yookassa_secret_key),
                           json=payload,headers={"Idempotence-Key":order_id})
            r.raise_for_status(); d=r.json()
            pm=(d.get("payment_method") or {})
            return {"id":d["id"],"url":d["confirmation"]["confirmation_url"],"status":d.get("status"),"recurring_token":pm.get("id") if pm.get("saved") else None}

    async def charge_recurring(self, amount, order_id, description, payment_method_id):
        payload={"amount":{"value":f"{amount:.2f}","currency":settings.default_currency},"capture":True,"payment_method_id":payment_method_id,"description":description,"metadata":{"order_id":order_id}}
        async with _public_client(20) as c:
            r=await c.post(settings.yookassa_api_url.rstrip("/")+"/v3/payments",auth=(settings.yookassa_shop_id,settings.yookassa_secret_key),json=payload,headers={"Idempotence-Key":order_id})
            r.raise_for_status(); d=r.json()
        return {"id":d["id"],"status":d.get("status")}

    async def refund(self, payment_id, amount, currency, description="VPN Shop refund"):
        payload={"payment_id":payment_id,"amount":{"value":f"{Decimal(str(amount)):.2f}","currency":currency},"description":description}
        idem=f"refund-{payment_id}"
        async with _public_client(20) as c:
            r=await c.post(settings.yookassa_api_url.rstrip("/")+"/v3/refunds",auth=(settings.yookassa_shop_id,settings.yookassa_secret_key),json=payload,headers={"Idempotence-Key":idem})
            r.raise_for_status(); d=r.json()
        return {"id":d.get("id"),"status":d.get("status")}

    async def get_refund_status(self, refund_id: str):
        async with _public_client(10) as c:
            r=await c.get(settings.yookassa_api_url.rstrip("/")+f"/v3/refunds/{refund_id}",auth=(settings.yookassa_shop_id,settings.yookassa_secret_key)); r.raise_for_status(); d=r.json()
        return str(d.get("status") or "").lower()


    async def find_by_order_id(self, order_id: str, max_pages: int = 5):
        """Find a recent payment carrying our immutable order_id metadata.

        YooKassa exposes payment lists and returns metadata on each payment. This is
        used only for recovery of a durable `creation_unknown` intent, never as a
        replacement for the provider idempotency key.
        """
        cursor = None
        async with _public_client(10) as c:
            for _ in range(max_pages):
                params={"limit":100}
                if cursor: params["cursor"]=cursor
                r=await c.get(settings.yookassa_api_url.rstrip("/")+"/v3/payments",auth=(settings.yookassa_shop_id,settings.yookassa_secret_key),params=params)
                r.raise_for_status(); data=r.json()
                for item in data.get("items") or []:
                    if str((item.get("metadata") or {}).get("order_id") or "") == str(order_id):
                        return item
                cursor=data.get("next_cursor")
                if not cursor: break
        return None

    async def get_payment_status(self, payment_id: str):
        async with _public_client(10) as c:
            r=await c.get(settings.yookassa_api_url.rstrip("/")+f"/v3/payments/{payment_id}",
                          auth=(settings.yookassa_shop_id,settings.yookassa_secret_key))
            r.raise_for_status(); d=r.json()
        return str(d.get("status") or "").lower()

    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, expected_currency: str, expected_order_id: str|None = None):
        async with _public_client(10) as c:
            r=await c.get(settings.yookassa_api_url.rstrip("/")+f"/v3/payments/{payment_id}",
                          auth=(settings.yookassa_shop_id,settings.yookassa_secret_key))
            r.raise_for_status(); d=r.json()
        amount=d.get("amount",{})
        if expected_order_id is not None and str((d.get("metadata") or {}).get("order_id") or "") != str(expected_order_id):
            return False
        return d.get("status")=="succeeded" and Decimal(str(amount.get("value",-1))).quantize(Decimal("0.01"))==Decimal(str(expected_amount)).quantize(Decimal("0.01")) and amount.get("currency")==expected_currency

class PlategaProvider(PaymentProvider):
    name = "platega"
    async def refund(self, payment_id, amount, currency, description="VPN Shop refund"):
        if not settings.platega_refund_url:
            raise RuntimeError("Platega refund endpoint is not configured; refusing to call another provider")
        payload={"payment_id":str(payment_id),"amount":f"{Decimal(str(amount)):.2f}","currency":currency,"description":description}
        headers={"X-MerchantId":settings.platega_merchant_id,"X-Secret":settings.platega_secret,"Idempotency-Key":f"refund-{payment_id}"}
        async with _public_client(20) as c:
            r=await c.post(settings.platega_refund_url,json=payload,headers=headers); r.raise_for_status(); d=r.json()
        return {"id":d.get("refundId") or d.get("id") or d.get("transactionId"),"status":str(d.get("status") or "processing").lower()}

    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, expected_currency: str, expected_order_id: str|None = None):
        headers={"X-MerchantId":settings.platega_merchant_id,"X-Secret":settings.platega_secret}
        async with _public_client(10) as c:
            r=await c.get(settings.platega_api_url.rstrip("/")+f"/transaction/{payment_id}",headers=headers); r.raise_for_status(); d=r.json()
        details=d.get("paymentDetails") or {}
        if expected_order_id is not None and str(d.get("payload") or d.get("Payload") or "") != str(expected_order_id):
            return False
        return str(d.get("status","")).upper()=="CONFIRMED" and Decimal(str(details.get("amount",-1))).quantize(Decimal("0.01"))==Decimal(str(expected_amount)).quantize(Decimal("0.01")) and str(details.get("currency"))==expected_currency

    async def get_refund_status(self, refund_id: str):
        if not settings.platega_refund_status_url: raise RuntimeError("Platega refund status endpoint is not configured")
        url=settings.platega_refund_status_url.rstrip("/")+"/"+str(refund_id)
        headers={"X-MerchantId":settings.platega_merchant_id,"X-Secret":settings.platega_secret}
        async with _public_client(10) as c:
            r=await c.get(url,headers=headers); r.raise_for_status(); d=r.json()
        return str(d.get("status") or "").lower()

    async def create(self, amount, order_id, description, return_url):
        payload={"paymentMethod":2,"paymentDetails":{"amount":amount,"currency":settings.default_currency},
                 "description":description,"return":return_url,"failedUrl":return_url,
                 "payload":order_id}
        headers={"X-MerchantId":settings.platega_merchant_id,"X-Secret":settings.platega_secret,"Content-Type":"application/json"}
        async with _public_client(20) as c:
            r=await c.post(settings.platega_api_url.rstrip("/")+"/transaction/process",json=payload,headers=headers)
            r.raise_for_status(); d=r.json()
            return {"id":d.get("transactionId") or d.get("id"),"url":d.get("redirect") or d.get("url")}

class RollyPayProvider(PaymentProvider):
    name = "rollypay"
    async def refund(self, payment_id, amount, currency, description="VPN Shop refund"):
        if not settings.rollypay_refund_url:
            raise RuntimeError("RollyPay refund endpoint is not configured; refusing to call another provider")
        payload={"payment_id":str(payment_id),"amount":f"{Decimal(str(amount)):.2f}","payment_currency":currency,"description":description}
        nonce=str(uuid.uuid4())
        headers={"X-API-Key":settings.rollypay_api_key,"X-Nonce":nonce,"Idempotency-Key":f"refund-{payment_id}","Content-Type":"application/json"}
        async with _public_client(20) as c:
            r=await c.post(settings.rollypay_refund_url,json=payload,headers=headers); r.raise_for_status(); d=r.json()
        return {"id":d.get("refund_id") or d.get("refundId") or d.get("id"),"status":str(d.get("status") or "processing").lower()}

    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, expected_currency: str, expected_order_id: str|None = None):
        headers={"X-API-Key":settings.rollypay_api_key,"X-Nonce":str(uuid.uuid4())}
        async with _public_client(10) as c:
            r=await c.get(settings.rollypay_api_url.rstrip("/")+f"/api/v1/payments/{payment_id}",headers=headers); r.raise_for_status(); d=r.json()
        if expected_order_id is not None and str(d.get("order_id") or "") != str(expected_order_id):
            return False
        return str(d.get("status","")).lower()=="paid" and Decimal(str(d.get("amount",-1))).quantize(Decimal("0.01"))==Decimal(str(expected_amount)).quantize(Decimal("0.01")) and str(d.get("payment_currency"))==expected_currency

    async def get_refund_status(self, refund_id: str):
        if not settings.rollypay_refund_status_url: raise RuntimeError("RollyPay refund status endpoint is not configured")
        url=settings.rollypay_refund_status_url.rstrip("/")+"/"+str(refund_id)
        headers={"X-API-Key":settings.rollypay_api_key,"X-Nonce":str(uuid.uuid4())}
        async with _public_client(10) as c:
            r=await c.get(url,headers=headers); r.raise_for_status(); d=r.json()
        return str(d.get("status") or "").lower()

    async def create(self, amount, order_id, description, return_url):
        payload={"amount":f"{amount:.2f}","payment_currency":settings.default_currency,"payment_method":"sbp",
                 "order_id":order_id,"description":description,"success_redirect_url":return_url,"fail_redirect_url":return_url}
        if settings.rollypay_test_mode:
            payload["test"] = True
        headers={"X-API-Key":settings.rollypay_api_key,"X-Nonce":str(uuid.uuid4()),"Content-Type":"application/json"}
        async with _public_client(20) as c:
            r=await c.post(settings.rollypay_api_url.rstrip("/")+"/api/v1/payments",json=payload,headers=headers)
            r.raise_for_status(); d=r.json()
            return {"id":d["payment_id"],"url":d["pay_url"]}

def verify_rollypay(raw_body: bytes, timestamp: str, signature: str, max_age: int = 300) -> bool:
    if not timestamp or not signature or not settings.rollypay_signing_secret:
        return False
    try:
        ts=int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time())-ts)>max_age:
        return False
    expected=hmac.new(settings.rollypay_signing_secret.encode(), timestamp.encode()+b"."+raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected,signature)

def verify_platega_headers(merchant_id: str|None, secret: str|None) -> bool:
    return bool(settings.platega_merchant_id and settings.platega_secret and
                merchant_id and secret and hmac.compare_digest(merchant_id, settings.platega_merchant_id) and
                hmac.compare_digest(secret, settings.platega_secret))

async def staging_create_payment(provider: str, cfg: dict, amount: Decimal, order_id: str, description: str, return_url: str):
    """Create a payment using ONLY credentials supplied in the encrypted staging config.
    Production settings are deliberately never consulted here."""
    currency = str(cfg.get("currency") or settings.default_currency)
    # Staging provider endpoints are administrator-supplied. Validate them and pin
    # DNS resolution at connection time to prevent SSRF/DNS-rebinding attacks.
    from .main import validate_public_url, _pinned_public_http_client
    async with _pinned_public_http_client(20) as c:
        if provider == "yookassa":
            shop, secret = cfg.get("shop_id"), cfg.get("secret_key")
            if not shop or not secret: raise RuntimeError("Не заданы sandbox-данные ЮKassa")
            payload={"amount":{"value":f"{amount:.2f}","currency":currency},"capture":True,"confirmation":{"type":"redirect","return_url":return_url},"description":description,"metadata":{"order_id":order_id,"staging_e2e":"true"}}
            api_url=str(cfg.get("api_url") or "https://api.yookassa.ru")
            validate_public_url(api_url, allow_empty=False)
            r=await c.post(api_url.rstrip("/")+"/v3/payments",auth=(shop,secret),json=payload,headers={"Idempotence-Key":order_id}); r.raise_for_status(); d=r.json()
            return {"id":d["id"],"url":d["confirmation"]["confirmation_url"]}
        if provider == "platega":
            merchant, secret = cfg.get("merchant_id"), cfg.get("secret")
            if not merchant or not secret: raise RuntimeError("Не заданы sandbox-данные Platega")
            payload={"paymentMethod":2,"paymentDetails":{"amount":amount,"currency":currency},"description":description,"return":return_url,"failedUrl":return_url,"payload":order_id}
            api_url=str(cfg.get("api_url") or "https://app.platega.io")
            validate_public_url(api_url, allow_empty=False)
            r=await c.post(api_url.rstrip("/")+"/transaction/process",json=payload,headers={"X-MerchantId":merchant,"X-Secret":secret,"Content-Type":"application/json"}); r.raise_for_status(); d=r.json()
            return {"id":d.get("transactionId") or d.get("id"),"url":d.get("redirect") or d.get("url")}
        if provider == "rollypay":
            key = cfg.get("api_key")
            if not key: raise RuntimeError("Не задан sandbox API-ключ RollyPay")
            payload={"amount":f"{amount:.2f}","payment_currency":currency,"payment_method":"sbp","order_id":order_id,"description":description,"success_redirect_url":return_url,"fail_redirect_url":return_url,"test":True}
            api_url=str(cfg.get("api_url") or "https://rollypay.io")
            validate_public_url(api_url, allow_empty=False)
            r=await c.post(api_url.rstrip("/")+"/api/v1/payments",json=payload,headers={"X-API-Key":key,"X-Nonce":str(uuid.uuid4()),"Content-Type":"application/json"}); r.raise_for_status(); d=r.json()
            return {"id":d["payment_id"],"url":d["pay_url"]}
    raise RuntimeError(f"Неизвестный staging-провайдер: {provider}")
