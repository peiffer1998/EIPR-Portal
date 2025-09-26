
# Billing Phase 6 Usage

This guide captures development curls for the pricing, invoice, and deposit flows added in Phase 6.

## Quote Reservation Pricing

```
curl -X POST   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   http://localhost:8000/api/v1/pricing/quote   -d '{
    "reservation_id": "RESERVATION_UUID",
    "promotion_code": "WELCOME10"
  }'
```

## Create Invoice From Reservation

```
curl -X POST   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   http://localhost:8000/api/v1/invoices/from-reservation   -d '{
    "reservation_id": "RESERVATION_UUID"
  }'
```

## Apply Invoice Promotion

```
curl -X POST   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   http://localhost:8000/api/v1/invoices/INVOICE_UUID/apply-promo   -d '{
    "code": "WELCOME10"
  }'
```

## Manage Reservation Deposits

```
# Hold a deposit
curl -X POST   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   http://localhost:8000/api/v1/reservations/RESERVATION_UUID/deposits/hold   -d '{"amount": "50.00"}'

# Consume the deposit at checkout
deposit_id=$(curl -s ... )
curl -X POST   -H "Authorization: Bearer $TOKEN"   -H "Content-Type: application/json"   http://localhost:8000/api/v1/reservations/RESERVATION_UUID/deposits/consume   -d '{"amount": "50.00"}'
```

> Replace `RESERVATION_UUID`, `INVOICE_UUID`, and `$TOKEN` with real values from your environment.
