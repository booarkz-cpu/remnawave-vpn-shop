# V44.5.6 — Very Deep Audit Report

## Scope

Full source review of the current 44.5.5 baseline, with focus on payment/refund state machines, idempotency, entitlement safety, referral money movement, concurrency, admin authorization, SSRF, backup/restore, worker paths and release integrity.

The review explicitly treated business-logic and concurrency as first-class risks, consistent with OWASP guidance: server-side state must enforce workflows, check-then-act operations must be atomic, and external non-idempotent operations need durable idempotency.

## New findings fixed

### HIGH — Refund retry could leave a paid refund permanently unreconciled
YooKassa refund requests used a random idempotency key. If the HTTP request timed out after the provider accepted the refund, the application could enter `review` without a durable way to reproduce the same provider operation safely.

**Fix:** YooKassa refund idempotency is now deterministic: `refund-{payment_id}`. The execute endpoint also permits retry from `review`, so an ambiguous provider response can be retried with the same idempotency key rather than creating a second refund.

### HIGH — Pending refund revoke retry could revoke a newer subscription
The background `refunded_pending_revoke` retry path directly disabled the user's current Remnawave user. That bypassed the existing protection which checks for later successful payments. A refund of an older payment could therefore disable access purchased by a newer payment.

**Fix:** scheduler retry now uses `_safe_revoke_for_refunded_payment()`, which checks later paid/fulfilled payments before revocation.

### HIGH — Referral reward clawback could be missed after revoke retry
The manual `retry-revoke` path could complete the refund/revoke transition without executing the referral reward reversal. This could leave referral credit outstanding after a successful refund.

**Fix:** both background and manual revoke-retry paths now call the idempotent referral clawback.

## Regression protection

Added regression tests for all three business invariants plus deterministic provider idempotency.

## Verification

- pytest: **148 passed**
- Python compileall: **PASS**
- Bash syntax checks: **PASS**
- Docker Compose YAML parsing: **PASS**
- ZIP integrity: **PASS**
- Release version consistency: **PASS**

## Remaining external verification gap

A real payment-provider sandbox, live Remnawave API and production Docker runtime are not available in this execution environment. Those external E2E paths are therefore not represented as passed.
