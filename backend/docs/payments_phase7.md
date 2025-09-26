# Payments Phase 7 Guide

## Test Environment Setup
- Populate `.env` with Stripe test keys (e.g., `STRIPE_SECRET_KEY=sk_test_xxx`) and keep `PAYMENTS_WEBHOOK_VERIFY=true` for signature checks. Set it to `false` when using the local simulator.
- Start services with `make up` (or `docker compose up -d --build`) and run `docker compose exec api alembic upgrade head` to apply migrations.
- Seed billing data via existing Phase 6 flows or any fixture that creates reservations and invoices.

## Generate a Payment Intent
```bash
docker compose exec api curl -s \
  -X POST http://api:8000/api/v1/payments/create-intent \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": "<invoice-uuid>"}'
```
The response returns `client_secret` and the persisted `transaction_id`. The intent amount reflects the invoice total minus any held deposit.

## Simulate a Webhook in Local Mode
1. Ensure `APP_ENV=local` and optionally set `PAYMENTS_WEBHOOK_VERIFY=false`.
2. Call the simulator:
```bash
docker compose exec api curl -s \
  -X POST http://api:8000/api/v1/payments/dev/simulate-webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_fake"}}}'
```
The handler consumes any held deposit, marks the invoice paid, and records a `payment_events` row.

## Issue Refunds
- Trigger a refund:
```bash
docker compose exec api curl -s \
  -X POST http://api:8000/api/v1/payments/refund \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": "<invoice-uuid>", "amount": 25.00}'
```
- Stripe test mode (or the offline simulator) updates the transaction to `partial_refund` when `amount` is below the charged total, and to `refunded` when omitted.
