from datetime import datetime
from decimal import Decimal
import secrets
from sqlalchemy import String, Integer, BigInteger, DateTime, Boolean, Numeric, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int|None] = mapped_column(BigInteger, unique=True, index=True)
    yandex_id: Mapped[str|None] = mapped_column(String(255), unique=True, index=True)
    vk_id: Mapped[str|None] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str|None] = mapped_column(String(320), unique=True, index=True)
    email_password_hash: Mapped[str|None] = mapped_column(String(512))
    username: Mapped[str|None] = mapped_column(String(255))
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=lambda: secrets.token_urlsafe(8).upper())
    referred_by_id: Mapped[int|None] = mapped_column(Integer, index=True)
    auto_renew_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referral_balance: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0, nullable=False)
    wallet_balance: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at: Mapped[datetime|None] = mapped_column(DateTime)

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_limit_gb: Mapped[int|None] = mapped_column(Integer)
    device_limit: Mapped[int|None] = mapped_column(Integer)
    remnawave_profile_id: Mapped[str|None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_payments_user_idempotency_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_payment_id: Mapped[str|None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    order_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    original_amount: Mapped[Decimal|None] = mapped_column(Numeric(12,2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12,2), default=0, nullable=False)
    # Snapshot commercial terms at checkout so later admin edits to a Plan cannot
    # change the entitlement of an already purchased payment.
    duration_days_snapshot: Mapped[int|None] = mapped_column(Integer)
    traffic_limit_gb_snapshot: Mapped[int|None] = mapped_column(Integer)
    device_limit_snapshot: Mapped[int|None] = mapped_column(Integer)
    remnawave_profile_id_snapshot: Mapped[str|None] = mapped_column(String(255))
    referrer_id_snapshot: Mapped[int|None] = mapped_column(Integer, index=True)
    promo_code: Mapped[str|None] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    fulfillment_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    fulfillment_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fulfillment_error: Mapped[str|None] = mapped_column(Text)
    next_retry_at: Mapped[datetime|None] = mapped_column(DateTime)
    fulfillment_max_attempts: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    fulfillment_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    idempotency_key: Mapped[str|None] = mapped_column(String(128), index=True)
    purpose: Mapped[str] = mapped_column(String(24), default="subscription", nullable=False)
    bonus_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checkout_url: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at: Mapped[datetime|None] = mapped_column(DateTime)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, unique=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    remnawave_uuid: Mapped[str|None] = mapped_column(String(255))
    subscription_url: Mapped[str|None] = mapped_column(Text)
    expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    # Immutable entitlement limits of the currently active subscription.
    # These are copied from the paid/trial grant so later Plan edits cannot
    # silently change an existing customer's device/traffic entitlement.
    traffic_limit_gb_snapshot: Mapped[int|None] = mapped_column(Integer)
    device_limit_snapshot: Mapped[int|None] = mapped_column(Integer)
    remnawave_profile_id_snapshot: Mapped[str|None] = mapped_column(String(255))
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    grace_until: Mapped[datetime|None] = mapped_column(DateTime)
    scheduled_cancel_at: Mapped[datetime|None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime|None] = mapped_column(DateTime)
    last_renewal_failure_at: Mapped[datetime|None] = mapped_column(DateTime)

class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    telegram_id: Mapped[int|None] = mapped_column(BigInteger, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="viewer", nullable=False)
    totp_secret_encrypted: Mapped[str|None] = mapped_column(Text)
    recovery_codes_encrypted: Mapped[str|None] = mapped_column(Text)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at: Mapped[datetime|None] = mapped_column(DateTime)

class FinancialLedger(Base):
    __tablename__ = "financial_ledger"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operation_key: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    user_id: Mapped[int|None] = mapped_column(Integer, index=True)
    payment_id: Mapped[int|None] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_after: Mapped[Decimal|None] = mapped_column(Numeric(12,2))
    metadata_json: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(320), nullable=False, default="system")
    target: Mapped[str|None] = mapped_column(String(200))
    details: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)

class BotMenuItem(Base):
    __tablename__ = "bot_menu_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    item_type: Mapped[str] = mapped_column(String(32), default="webapp", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class CabinetMenuItem(Base):
    __tablename__ = "cabinet_menu_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="custom", nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class CustomField(Base):
    __tablename__ = "custom_fields"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), default="text", nullable=False)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

class MenuImage(Base):
    __tablename__ = "menu_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Promotion(Base):
    __tablename__ = "promotions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="percent", nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    plan_ids: Mapped[list|None] = mapped_column(JSON, nullable=True)
    starts_at: Mapped[datetime|None] = mapped_column(DateTime)
    ends_at: Mapped[datetime|None] = mapped_column(DateTime)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exclusive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class PromoCode(Base):
    __tablename__ = "promo_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="percent", nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    plan_ids: Mapped[list|None] = mapped_column(JSON, nullable=True)
    starts_at: Mapped[datetime|None] = mapped_column(DateTime)
    ends_at: Mapped[datetime|None] = mapped_column(DateTime)
    usage_limit: Mapped[int|None] = mapped_column(Integer)
    reserved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    first_purchase_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_uses_per_user: Mapped[int|None] = mapped_column(Integer)
    min_amount: Mapped[Decimal|None] = mapped_column(Numeric(12,2))
    referral_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class GiftCode(Base):
    __tablename__ = "gift_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int|None] = mapped_column(Integer)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    purchaser_user_id: Mapped[int|None] = mapped_column(Integer, index=True)
    idempotency_key: Mapped[str|None] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class GiftRedemption(Base):
    __tablename__ = "gift_redemptions"
    __table_args__ = (UniqueConstraint("gift_code_id", "user_id", name="uq_gift_redemption_code_user"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    gift_code_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="processing", nullable=False)
    remote_user_id: Mapped[str|None] = mapped_column(String(255))
    expected_before_expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    expected_after_expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Advertisement(Base):
    __tablename__ = "advertisements"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    image_url: Mapped[str|None] = mapped_column(Text)
    button_text: Mapped[str|None] = mapped_column(String(100))
    button_url: Mapped[str|None] = mapped_column(Text)
    starts_at: Mapped[datetime|None] = mapped_column(DateTime)
    ends_at: Mapped[datetime|None] = mapped_column(DateTime)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

class Broadcast(Base):
    __tablename__ = "broadcasts"
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str|None] = mapped_column(Text)
    button_text: Mapped[str|None] = mapped_column(String(100))
    button_url: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    target: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime|None] = mapped_column(DateTime)

class AuthExchangeCode(Base):
    __tablename__ = "auth_exchange_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class BackupJob(Base):
    __tablename__ = "backup_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    filename: Mapped[str|None] = mapped_column(String(255))
    size_bytes: Mapped[int|None] = mapped_column(BigInteger)
    sha256: Mapped[str|None] = mapped_column(String(64))
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime|None] = mapped_column(DateTime)


class AdminSession(Base):
    __tablename__ = "admin_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    jti_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    ip: Mapped[str|None] = mapped_column(String(64))
    user_agent: Mapped[str|None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime|None] = mapped_column(DateTime)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    jti_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    ip: Mapped[str|None] = mapped_column(String(64))
    user_agent: Mapped[str|None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime|None] = mapped_column(DateTime)

class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    promo_code_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    payment_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class PromoReservation(Base):
    __tablename__ = "promo_reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    promo_code_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    payment_id: Mapped[int|None] = mapped_column(Integer, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="reserved", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ReferralReward(Base):
    __tablename__ = "referral_rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    referred_user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    payment_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="credited", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ProvisioningOperation(Base):
    __tablename__ = "provisioning_operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    operation_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="provision")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    remote_user_id: Mapped[str|None] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime|None] = mapped_column(DateTime)
    expected_before_expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    expected_after_expires_at: Mapped[datetime|None] = mapped_column(DateTime)


class PaymentProviderEvent(Base):
    __tablename__ = "payment_provider_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_payment_provider_events_provider_event"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    payment_id: Mapped[int|None] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(32), default="verified", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str|None] = mapped_column(Text)
    processed_at: Mapped[datetime|None] = mapped_column(DateTime)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ReferralLedger(Base):
    __tablename__ = "referral_ledger"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    source_user_id: Mapped[int|None] = mapped_column(Integer, index=True)
    payment_id: Mapped[int|None] = mapped_column(Integer, unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="reward")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AutoRenewMethod(Base):
    __tablename__ = "auto_renew_methods"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_attempt_at: Mapped[datetime|None] = mapped_column(DateTime)
    last_success_at: Mapped[datetime|None] = mapped_column(DateTime)
    last_error: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RefundRequest(Base):
    __tablename__ = "refund_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False)
    reason: Mapped[str|None] = mapped_column(Text)
    provider_refund_id: Mapped[str|None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    admin_reply: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False)
    admin_note: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class WorkerState(Base):
    __tablename__ = "worker_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="online", nullable=False)
    current_job: Mapped[str|None] = mapped_column(String(255))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class ReleaseRecord(Base):
    __tablename__ = "release_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    rollback_archive: Mapped[str|None] = mapped_column(Text)
    details: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime|None] = mapped_column(DateTime)

class SecurityIncident(Base):
    __tablename__ = "security_incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    details: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime|None] = mapped_column(DateTime)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    next_retry_at: Mapped[datetime|None] = mapped_column(DateTime)
    locked_at: Mapped[datetime|None] = mapped_column(DateTime)
    worker_id: Mapped[str|None] = mapped_column(String(128), index=True)
    error: Mapped[str|None] = mapped_column(Text)
    payload: Mapped[dict|None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime|None] = mapped_column(DateTime)

class FraudSignal(Base):
    __tablename__ = "fraud_signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int|None] = mapped_column(Integer, index=True)
    ip: Mapped[str|None] = mapped_column(String(64), index=True)
    fingerprint: Mapped[str|None] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True, nullable=False)
    details: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime|None] = mapped_column(DateTime)

class PayoutTransaction(Base):
    __tablename__ = "payout_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    withdrawal_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="processing", index=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at: Mapped[datetime|None] = mapped_column(DateTime)

class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)



class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(24), default="in_app", nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    read_at: Mapped[datetime|None] = mapped_column(DateTime)
    sent_at: Mapped[datetime|None] = mapped_column(DateTime)


class StatusComponent(Base):
    __tablename__ = "status_components"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="operational", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Deployment(Base):
    __tablename__ = "deployments"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_version: Mapped[str|None] = mapped_column(String(64))
    strategy: Mapped[str] = mapped_column(String(24), default="canary", nullable=False)
    traffic_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="planned", index=True, nullable=False)
    error_rate_percent: Mapped[Decimal] = mapped_column(Numeric(6,3), default=0, nullable=False)
    rollback_reason: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime|None] = mapped_column(DateTime)

class PaymentProviderHealth(Base):
    __tablename__ = "payment_provider_health"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_latency_ms: Mapped[int|None] = mapped_column(Integer)
    last_error: Mapped[str|None] = mapped_column(Text)
    circuit_open_until: Mapped[datetime|None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class SecurityIncidentEvent(Base):
    __tablename__ = "security_incident_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str|None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime|None] = mapped_column(DateTime)

class BackupVerification(Base):
    __tablename__ = "backup_verifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    backup_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    checksum_ok: Mapped[bool|None] = mapped_column(Boolean)
    archive_safe: Mapped[bool|None] = mapped_column(Boolean)
    restore_tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error: Mapped[str|None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime|None] = mapped_column(DateTime)

class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    credential_id: Mapped[str] = mapped_column(String(1024), unique=True, index=True, nullable=False)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transports: Mapped[str|None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100), default="Passkey", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at: Mapped[datetime|None] = mapped_column(DateTime)


class UserDevice(Base):
    __tablename__ = "user_devices"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    device_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Устройство", nullable=False)
    platform: Mapped[str|None] = mapped_column(String(64))
    last_ip: Mapped[str|None] = mapped_column(String(64))
    last_seen_at: Mapped[datetime|None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    revoked_at: Mapped[datetime|None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="broadcast", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    audience: Mapped[dict|None] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    starts_at: Mapped[datetime|None] = mapped_column(DateTime)
    ends_at: Mapped[datetime|None] = mapped_column(DateTime)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    conditions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    actions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    last_run_at: Mapped[datetime|None] = mapped_column(DateTime)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class MonitoringCheck(Base):
    __tablename__ = "monitoring_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(8), default="GET", nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_status: Mapped[str|None] = mapped_column(String(32))
    last_latency_ms: Mapped[int|None] = mapped_column(Integer)
    last_error: Mapped[str|None] = mapped_column(Text)
    last_checked_at: Mapped[datetime|None] = mapped_column(DateTime)
    failure_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class TrialGrant(Base):
    __tablename__ = "trial_grants"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    # Freeze trial entitlement at claim time. Later admin edits to Plan must not
    # change a grant that has already been promised to the user.
    traffic_limit_gb_snapshot: Mapped[int|None] = mapped_column(Integer)
    device_limit_snapshot: Mapped[int|None] = mapped_column(Integer)
    remnawave_profile_id_snapshot: Mapped[str|None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    expected_before_expires_at: Mapped[datetime|None] = mapped_column(DateTime)
    expected_after_expires_at: Mapped[datetime|None] = mapped_column(DateTime)
