# Release Notes — V2.0.0-realise

## Product
- Billing Center
- Subscription lifecycle / grace period
- Customer 360
- Security Center + user session revocation
- Gift codes with remote provisioning
- Refund Dry Run
- Risk summary
- System Health
- Existing Jobs, Support, Anti-fraud, Incident Mode and Analytics retained

## Security / reliability
- Subscription expiry now has explicit remote revoke state machine.
- User JWTs are backed by server-side revocable sessions.
- Gift activation uses durable operation state and expected expiry values.
- Existing payment/refund/fulfillment lock ordering and stale-state protections retained.

## Database
Migration: `0032_v2_0_0_product_features`

## Verification
267 tests passed. See `V2_0_0_PRODUCT_AND_CRITICAL_AUDIT_RU.md`.
