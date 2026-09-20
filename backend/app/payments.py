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
from ipaddress import ip_address, ip_network
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


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
        """Ленивая инициализация HTTP-клиента с таймаутами."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=5.0),
                verify=True,
                http2=True,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=5,
                ),
                follow_redirects=False,
            )
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
        return response.json()

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
        """Проверить IP-адрес отправителя по allowlist."""
        if not remote_addr or not settings.yookassa_webhook_ip_allowlist:
            return

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
        return response.json()

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
        return response.json()

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
        else:
            raise PaymentError(f"Неизвестный провайдер: {name}")
    return _providers[name]


async def close_all_providers() -> None:
    """Закрыть HTTP-клиенты всех провайдеров при остановке."""
    for provider in _providers.values():
        await provider.close()
