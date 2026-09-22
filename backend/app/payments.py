"""
Модуль интеграции с платежными системами.

Провайдеры: YooKassa, Platega, RollyPay.

Безопасность:
- YooKassa: проверка IP-адреса отправителя по allowlist.
- Platega: HMAC-SHA256 подпись вебхука.
- RollyPay: HMAC-SHA256 + проверка timestamp.
- Защита от replay-атак (окно 5 минут для RollyPay).
- Идемпотентность по event_id (YooKassa).
- HTTP-клиент с таймаутами и keep-alive.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from ipaddress import ip_address, ip_network
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _public_client(timeout_seconds: int):
    """Исходящие запросы к платёжным API идут только через DNS-pinned клиент."""
    from .main import _pinned_public_http_client
    return _pinned_public_http_client(timeout_seconds)


def _money(amount) -> str:
    return f"{Decimal(str(amount)).quantize(Decimal('0.01')):.2f}"


def _checkout(data: Dict[str, Any]) -> Dict[str, Any]:
    confirmation = data.get("confirmation") or {}
    url = confirmation.get("confirmation_url") or data.get("url") or data.get("redirect") or data.get("paymentUrl") or data.get("link")
    payment_id = data.get("id") or data.get("payment_id") or data.get("transactionId") or data.get("transaction_id")
    return {"id": payment_id, "url": url, "status": data.get("status") or data.get("Status")}


# ============================================================
# Исключения
# ============================================================

class PaymentError(Exception):
    """Базовое исключение для ошибок платежных систем."""


class SignatureVerificationError(PaymentError):
    """Ошибка проверки вебхука (подпись или IP)."""


class WebhookReplayError(PaymentError):
    """Ошибка повторного использования вебхука (replay attack)."""


class WebhookAlreadyProcessedError(PaymentError):
    """Вебхук с таким event_id уже был обработан."""


# ============================================================
# Базовый провайдер
# ============================================================

class BasePaymentProvider(ABC):
    """Абстрактный базовый класс для платежных провайдеров."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Клиент с фиксацией DNS. Нельзя открывать прямой httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            self._client = _public_client(20)
        return self._client

    async def close(self) -> None:
        """Закрыть HTTP-клиент."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @abstractmethod
    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Создать платеж."""
        raise NotImplementedError

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Получить статус платежа."""
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        remote_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Проверить вебхук и вернуть его данные."""
        raise NotImplementedError


# ============================================================
# YooKassa Provider
# ============================================================

class YooKassaProvider(BasePaymentProvider):
    """
    Провайдер YooKassa.

    Проверка вебхука выполняется по IP-адресу отправителя
    (allowlist из настроек) + идемпотентность по event_id.
    """

    def __init__(self) -> None:
        super().__init__()
        self._processed_events: Dict[str, datetime] = {}
        self._event_ttl = timedelta(hours=24)

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        client = await self._get_client()
        idempotence_key = str(uuid.uuid4())

        payload: Dict[str, Any] = {
            "amount": {"value": f"{amount:.2f}", "currency": currency},
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": metadata.get(
                    "return_url", settings.public_base_url
                ),
            },
            "description": description,
            "metadata": metadata,
        }

        email = metadata.get("email")
        if email:
            payload["receipt"] = {
                "customer": {"email": email},
                "items": [
                    {
                        "description": description,
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency": currency,
                        },
                        "vat_code": 1,
                    }
                ],
            }

        response = await client.post(
            f"{settings.yookassa_api_url}/v3/payments",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            headers={
                "Idempotence-Key": idempotence_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.get(
            f"{settings.yookassa_api_url}/v3/payments/{payment_id}",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("status") or "")

    async def refund_payment(
        self, payment_id: str, amount: float, currency: str
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "payment_id": payment_id,
            "amount": {"value": f"{amount:.2f}", "currency": currency},
        }
        response = await client.post(
            f"{settings.yookassa_api_url}/v3/refunds",
            auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            headers={"Idempotence-Key": str(uuid.uuid4())},
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _verify_ip(self, remote_addr: Optional[str]) -> None:
        """Проверить IP-адрес отправителя по allowlist. Пустой список отклоняет вебхук."""
        if not settings.yookassa_webhook_ip_allowlist:
            raise SignatureVerificationError("YooKassa webhook IP allowlist is not configured")
        if not remote_addr:
            raise SignatureVerificationError("Missing remote address for YooKassa webhook")

        allowed = [
            ip_network(n.strip())
            for n in settings.yookassa_webhook_ip_allowlist.split(",")
            if n.strip()
        ]

        try:
            addr = ip_address(remote_addr)
        except ValueError:
            raise SignatureVerificationError(
                f"Некорректный IP: {remote_addr}"
            )

        if not any(addr in net for net in allowed):
            raise SignatureVerificationError(
                f"IP {remote_addr} не входит в allowlist YooKassa"
            )

    def verify_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        remote_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Проверить вебхук YooKassa:
        1. IP-адрес (allowlist).
        2. Парсинг JSON.
        3. Идемпотентность по event_id.
        """
        # 1. IP
        self._verify_ip(remote_addr)

        # 2. JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise PaymentError(f"Невалидный JSON в вебхуке: {e}")

        # 3. Идемпотентность
        event_id = data.get("event") or data.get("object", {}).get("id")
        if event_id:
            self._cleanup_old_events()
            if event_id in self._processed_events:
                raise WebhookAlreadyProcessedError(
                    f"Событие {event_id} уже обработано"
                )
            self._processed_events[event_id] = datetime.now(timezone.utc)

        return data

    def _cleanup_old_events(self) -> None:
        """Удалить старые записи из кэша обработанных событий."""
        now = datetime.now(timezone.utc)
        expired = [
            eid
            for eid, ts in self._processed_events.items()
            if now - ts > self._event_ttl
        ]
        for eid in expired:
            del self._processed_events[eid]

    async def create(self, amount: Decimal, order_id: str, description: str, return_url: str) -> Dict[str, Any]:
        data = await self.create_payment(float(amount), settings.default_currency, description, {"order_id": order_id, "return_url": return_url})
        return _checkout(data)

    async def charge_recurring(self, amount: Decimal, order_id: str, description: str, payment_method_id: str) -> Dict[str, Any]:
        """Повторное списание сохранённым способом оплаты. Idempotence-Key = order_id."""
        payload = {
            "amount": {"value": _money(amount), "currency": settings.default_currency},
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": description,
            "metadata": {"order_id": order_id},
        }
        async with _public_client(10) as client:
            response = await client.post(
                f"{settings.yookassa_api_url}/v3/payments",
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
                headers={"Idempotence-Key": order_id, "Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        return _checkout(response.json())

    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, currency: str, expected_order_id: str|None = None) -> bool:
        async with _public_client(10) as client:
            response = await client.get(
                f"{settings.yookassa_api_url}/v3/payments/{payment_id}",
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            )
        if response.status_code >= 400:
            return False
        d = response.json()
        paid = str(d.get("status") or "").lower() in {"succeeded", "paid", "success"}
        amount_value = Decimal(str((d.get("amount") or {}).get("value") or "0"))
        currency_ok = str((d.get("amount") or {}).get("currency") or "").upper() == str(currency).upper()
        order = str((d.get("metadata") or {}).get("order_id") or "")
        if expected_order_id and order != expected_order_id:
            return False
        return paid and amount_value == Decimal(str(expected_amount)) and currency_ok

    async def find_by_order_id(self, order_id: str):
        async with _public_client(10) as client:
            response = await client.get(
                f"{settings.yookassa_api_url}/v3/payments",
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
                params={"limit": 100},
            )
        response.raise_for_status()
        for item in response.json().get("items") or []:
            if str((item.get("metadata") or {}).get("order_id") or "") == order_id:
                return item
        return None

    async def refund(self, payment_id: str, amount, currency: str, reason: str = "") -> Dict[str, Any]:
        idem=f"refund-{payment_id}"
        async with _public_client(20) as client:
            response = await client.post(
                f"{settings.yookassa_api_url}/v3/refunds",
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
                headers={"Idempotence-Key": idem, "Content-Type": "application/json"},
                json={"payment_id": payment_id, "amount": {"value": _money(amount), "currency": currency}, "description": (reason or "Refund")[:250]},
            )
        response.raise_for_status()
        data = response.json()
        return {"id": data.get("id"), "status": data.get("status")}

    async def get_refund_status(self, refund_id: str) -> str:
        async with _public_client(10) as client:
            response = await client.get(
                f"{settings.yookassa_api_url}/v3/refunds/{refund_id}",
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
            )
        response.raise_for_status()
        return str(response.json().get("status") or "")


# ============================================================
# Platega Provider
# ============================================================

class PlategaProvider(BasePaymentProvider):
    """Провайдер Platega."""

    def __init__(self) -> None:
        super().__init__()

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "amount": amount,
            "currency": currency,
            "description": description,
            "metadata": metadata,
            "payload": metadata.get("payload") or metadata.get("order_id") or "",
            "return_url": metadata.get(
                "return_url", settings.public_base_url
            ),
        }
        response = await client.post(
            f"{settings.platega_api_url}/api/payment",
            headers={
                "X-Merchant": settings.platega_merchant_id,
                "X-Secret": settings.platega_secret,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.get(
            f"{settings.platega_api_url}/api/payment/{payment_id}",
            headers={
                "X-Merchant": settings.platega_merchant_id,
                "X-Secret": settings.platega_secret,
            },
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("status") or data.get("Status") or "")

    async def create(self, amount: Decimal, order_id: str, description: str, return_url: str) -> Dict[str, Any]:
        data = await self.create_payment(float(amount), settings.default_currency, description, {"order_id": order_id, "return_url": return_url, "payload": order_id})
        return _checkout(data)

    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, currency: str, expected_order_id: str|None = None) -> bool:
        async with _public_client(10) as client:
            response = await client.get(
                f"{settings.platega_api_url}/transaction/{payment_id}",
                headers={"X-Merchant": settings.platega_merchant_id, "X-Secret": settings.platega_secret},
            )
        if response.status_code >= 400:
            return False
        d = response.json()
        paid = str(d.get("status") or d.get("Status") or "").upper() in {"CONFIRMED", "SUCCESS", "SUCCEEDED", "PAID"}
        amount_value = Decimal(str(d.get("amount") or d.get("Amount") or "0"))
        order = str(d.get("payload") or d.get("Payload") or "")
        if expected_order_id and order != expected_order_id:
            return False
        return paid and amount_value == Decimal(str(expected_amount))

    async def refund(self, payment_id: str, amount, currency: str, reason: str = "") -> Dict[str, Any]:
        if not settings.platega_refund_url:
            raise PaymentError("Platega refund URL is not configured")
        idem=f"refund-{payment_id}"
        async with _public_client(20) as client:
            response = await client.post(
                settings.platega_refund_url,
                headers={"X-Merchant": settings.platega_merchant_id, "X-Secret": settings.platega_secret, "Idempotence-Key": idem},
                json={"id": payment_id, "amount": _money(amount), "currency": currency, "description": reason[:250]},
            )
        response.raise_for_status()
        data = response.json()
        return {"id": data.get("id") or data.get("refund_id") or payment_id, "status": data.get("status") or data.get("Status") or "processing"}

    async def get_refund_status(self, refund_id: str) -> str:
        url = settings.platega_refund_status_url or settings.platega_refund_url
        if not url:
            raise PaymentError("Platega refund status URL is not configured")
        async with _public_client(10) as client:
            response = await client.get(url.rstrip("/") + "/" + refund_id, headers={"X-Merchant": settings.platega_merchant_id, "X-Secret": settings.platega_secret})
        response.raise_for_status()
        data = response.json()
        return str(data.get("status") or data.get("Status") or "")

    def verify_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        remote_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Проверка подписи вебхука Platega (HMAC-SHA256)."""
        signature = (
            headers.get("X-Signature")
            or headers.get("x-signature")
        )
        if not signature:
            raise SignatureVerificationError(
                "Отсутствует заголовок X-Signature"
            )

        expected = hmac.new(
            settings.platega_secret.encode(), body, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise SignatureVerificationError(
                "Неверная подпись Platega"
            )

        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise PaymentError(f"Невалидный JSON: {e}")


# ============================================================
# RollyPay Provider
# ============================================================

class RollyPayProvider(BasePaymentProvider):
    """Провайдер RollyPay."""

    def __init__(self) -> None:
        super().__init__()

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        client = await self._get_client()
        payload = {
            "amount": amount,
            "currency": currency,
            "description": description,
            "metadata": metadata,
            "return_url": metadata.get(
                "return_url", settings.public_base_url
            ),
            "order_id": metadata.get("order_id") or "",
            "test": settings.rollypay_test_mode,
        }
        response = await client.post(
            f"{settings.rollypay_api_url}/api/v1/payments",
            headers={
                "Authorization": f"Bearer {settings.rollypay_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.get(
            f"{settings.rollypay_api_url}/api/v1/payments/{payment_id}",
            headers={
                "Authorization": f"Bearer {settings.rollypay_api_key}"
            },
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("status") or "")

    async def create(self, amount: Decimal, order_id: str, description: str, return_url: str) -> Dict[str, Any]:
        data = await self.create_payment(float(amount), settings.default_currency, description, {"order_id": order_id, "return_url": return_url})
        return _checkout(data)

    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, currency: str, expected_order_id: str|None = None) -> bool:
        async with _public_client(10) as client:
            response = await client.get(
                f"{settings.rollypay_api_url}/api/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {settings.rollypay_api_key}"},
            )
        if response.status_code >= 400:
            return False
        d = response.json()
        paid = str(d.get("status") or "").lower() in {"paid", "success", "succeeded"}
        amount_value = Decimal(str(d.get("amount") or "0"))
        order = str(d.get("order_id") or "")
        if expected_order_id and order != expected_order_id:
            return False
        return paid and amount_value == Decimal(str(expected_amount))

    async def refund(self, payment_id: str, amount, currency: str, reason: str = "") -> Dict[str, Any]:
        if not settings.rollypay_refund_url:
            raise PaymentError("RollyPay refund URL is not configured")
        nonce=str(uuid.uuid4())
        idem=f"refund-{payment_id}"
        body = json.dumps({"payment_id": payment_id, "amount": _money(amount), "currency": currency, "description": reason[:250]}).encode()
        signature = hmac.new(settings.rollypay_signing_secret.encode(), body, hashlib.sha256).hexdigest()
        async with _public_client(20) as client:
            response = await client.post(
                settings.rollypay_refund_url,
                content=body,
                headers={"Authorization": f"Bearer {settings.rollypay_api_key}", "X-Nonce":nonce, "X-Signature": signature, "Idempotence-Key": idem, "Content-Type": "application/json"},
            )
        response.raise_for_status()
        data = response.json()
        return {"id": data.get("id") or data.get("refund_id") or payment_id, "status": data.get("status") or "processing"}

    async def get_refund_status(self, refund_id: str) -> str:
        url = settings.rollypay_refund_status_url or settings.rollypay_refund_url
        if not url:
            raise PaymentError("RollyPay refund status URL is not configured")
        async with _public_client(10) as client:
            response = await client.get(url.rstrip("/") + "/" + refund_id, headers={"Authorization": f"Bearer {settings.rollypay_api_key}"})
        response.raise_for_status()
        return str(response.json().get("status") or "")

    def verify_webhook(
        self,
        headers: Dict[str, str],
        body: bytes,
        remote_addr: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Проверка подписи вебхука RollyPay (HMAC-SHA256) + timestamp.
        """
        signature = (
            headers.get("X-RollyPay-Signature")
            or headers.get("x-rollypay-signature")
        )
        if not signature:
            raise SignatureVerificationError(
                "Отсутствует заголовок X-RollyPay-Signature"
            )

        expected = hmac.new(
            settings.rollypay_signing_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise SignatureVerificationError(
                "Неверная подпись RollyPay"
            )

        # Проверка timestamp (защита от replay)
        ts_header = (
            headers.get("X-RollyPay-Timestamp")
            or headers.get("x-rollypay-timestamp")
        )
        if ts_header:
            try:
                ts = int(ts_header)
            except ValueError:
                raise SignatureVerificationError(
                    "Неверный формат timestamp"
                )
            now = int(time.time())
            if abs(now - ts) > 300:
                raise WebhookReplayError(
                    "Подпись RollyPay устарела"
                )

        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise PaymentError(f"Невалидный JSON: {e}")


class SandboxProvider:
    """Local payment provider for tests without live gateways."""

    async def create(self, amount, order_id: str, description: str, return_url: str):
        if not settings.payments_sandbox:
            raise PaymentError("Sandbox payments are disabled")
        payment_id = f"sandbox-{order_id}"
        url = f"{(settings.cabinet_url or settings.mini_app_url or return_url).rstrip('/')}/?sandbox_payment={payment_id}"
        return {"id": payment_id, "url": url, "status": "succeeded"}

    async def verify_succeeded(self, payment_id: str, expected_amount: Decimal, currency: str, expected_order_id: str | None = None):
        if not settings.payments_sandbox:
            return False
        if not str(payment_id).startswith("sandbox-"):
            return False
        if expected_order_id and f"sandbox-{expected_order_id}" != payment_id and expected_order_id not in payment_id:
            return False
        return True

    async def get_payment_status(self, payment_id: str) -> str:
        return "succeeded" if settings.payments_sandbox and str(payment_id).startswith("sandbox-") else "canceled"

    async def refund(self, payment_id: str, amount: Decimal, currency: str = "RUB"):
        return {"id": f"refund-{payment_id}", "status": "succeeded"}

    async def get_refund_status(self, refund_id: str) -> str:
        return "succeeded"

    async def charge_recurring(self, *args, **kwargs):
        raise PaymentError("Sandbox does not support recurring charges")


# ============================================================
# Фабрика провайдеров
# ============================================================

_providers: Dict[str, BasePaymentProvider] = {}


def get_payment_provider(name: str) -> BasePaymentProvider:
    """Вернуть singleton-провайдер по имени."""
    if name not in _providers:
        if name == "yookassa":
            _providers[name] = YooKassaProvider()
        elif name == "platega":
            _providers[name] = PlategaProvider()
        elif name == "rollypay":
            _providers[name] = RollyPayProvider()
        elif name == "sandbox":
            _providers[name] = SandboxProvider()  # type: ignore[assignment]
        else:
            raise PaymentError(f"Неизвестный провайдер: {name}")
    return _providers[name]


async def close_all_providers() -> None:
    """Закрыть HTTP-клиенты всех провайдеров при остановке."""
    for provider in _providers.values():
        await provider.close()


def verify_platega_headers(merchant_id: str | None, secret: str | None) -> bool:
    if not merchant_id or not secret or not settings.platega_merchant_id or not settings.platega_secret:
        return False
    return hmac.compare_digest(merchant_id, settings.platega_merchant_id) and hmac.compare_digest(secret, settings.platega_secret)


def verify_rollypay(raw: bytes, timestamp: str, signature: str) -> bool:
    if not raw or not timestamp or not signature or not settings.rollypay_signing_secret:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > 300:
        return False
    expected = hmac.new(settings.rollypay_signing_secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def staging_create_payment(provider: str, creds: Dict[str, Any], amount: Decimal, order_id: str, description: str, return_url: str) -> Dict[str, Any]:
    """Создать платёж только по переданным staging credentials.

    Production settings are deliberately never consulted.
    """
    from .main import validate_public_url, _pinned_public_http_client
    provider = str(provider)
    if provider == "yookassa":
        api_url = creds.get("api_url")
        api_url = validate_public_url(api_url, allow_empty=False)
        payload = {"amount": {"value": _money(amount), "currency": "RUB"}, "capture": True, "confirmation": {"type": "redirect", "return_url": return_url}, "description": description, "metadata": {"order_id": order_id}}
        auth = (str(creds.get("shop_id") or ""), str(creds.get("secret_key") or ""))
        headers = {"Idempotence-Key": order_id, "Content-Type": "application/json"}
        path = "/v3/payments"
    elif provider == "platega":
        api_url = creds.get("api_url")
        api_url = validate_public_url(api_url, allow_empty=False)
        payload = {"amount": float(amount), "currency": "RUB", "description": description, "payload": order_id, "return_url": return_url}
        auth = None
        headers = {"X-Merchant": str(creds.get("merchant_id") or ""), "X-Secret": str(creds.get("secret") or ""), "Content-Type": "application/json"}
        path = "/api/payment"
    elif provider == "rollypay":
        api_url = creds.get("api_url")
        api_url = validate_public_url(api_url, allow_empty=False)
        payload = {"amount": float(amount), "currency": "RUB", "description": description, "order_id": order_id, "return_url": return_url}
        payload["test"] = True
        auth = None
        headers = {"Authorization": f"Bearer {creds.get('api_key') or ''}", "Content-Type": "application/json"}
        path = "/api/v1/payments"
    else:
        raise PaymentError(f"Неизвестный провайдер: {provider}")
    async with _pinned_public_http_client(20) as c:
        response = await c.post(str(api_url).rstrip("/") + path, headers=headers, json=payload, auth=auth)
    response.raise_for_status()
    return _checkout(response.json())
