# Store Module Usage (Phase 11)

## Staff Workflows

- **Create or update packages:** `POST /api/v1/store/package-types` with name, applies_to (`boarding`, `daycare`, `grooming`, `currency`), credits, price, and active flag. Use `PATCH /api/v1/store/package-types/{id}` to edit or `DELETE` to remove.
- **Purchase packages on behalf of an owner:** `POST /api/v1/store/packages/purchase` with `owner_id`, `package_type_id`, and optional `quantity`. The endpoint creates a reservation stub, invoice, and package credit ledger entry.
- **Apply package credits to an invoice:** `POST /api/v1/store/invoices/{invoice_id}/apply-package-credits`. Returns total applied and units consumed; caps automatically at the invoice balance.
- **Issue and redeem gift certificates:**
  - Issue: `POST /api/v1/store/gift-certificates/issue` with `purchaser_owner_id`, `amount`, optional recipient fields, and optional expiry.
  - Redeem: `POST /api/v1/store/gift-certificates/redeem` with `code` and `owner_id`. Remaining value is transferred to store credit ledger.
- **Manual store credit adjustments:**
  - Add credit: `POST /api/v1/store/credit/add` with `owner_id`, `amount`, and optional `note`.
  - Balance lookup: `GET /api/v1/store/credit/balance?owner_id=`
- **Apply store credit to invoices:** `POST /api/v1/store/invoices/{invoice_id}/apply-store-credit` with `amount`. The service enforces owner match, available balance, and invoice amount caps.

## Owner Portal Workflows

- **Balances:** `GET /api/v1/portal/store/balances` lists package credits and store credit balance.
- **Available packages:** `GET /api/v1/portal/store/package-types` to display active packages and remaining credits.
- **Buy a package:** `POST /api/v1/portal/store/packages/buy` with `package_type_id` (and optional `quantity`). Returns the invoice id and Stripe client secret (when applicable).
- **Buy a gift certificate:** `POST /api/v1/portal/store/gift-certificates/buy` with `amount` and optional `recipient_email`. Response includes invoice id and the generated code.
- **Redeem a code:** `POST /api/v1/portal/store/gift-certificates/redeem` with `code` to move remaining value to store credit.
- **Apply store credit:** `POST /api/v1/portal/invoices/{invoice_id}/apply-store-credit` with `amount` to reduce open balances before payment.

## Notes

- `credits_total` on invoices now reflects package, gift certificate, and store credit applications. `total_amount` is automatically recalculated as `total - credits_total` and never drops below zero.
- Stripe payment intent creation fails fast when the amount due is zero (`ValueError: Invoice balance is zero; no payment required`).
- Package credit consumption respects reservation type (`boarding`, `daycare`, `grooming`) unless the package uses `currency`, which applies to any service.
- Store credit totals are tracked in `store_credit_ledger` with enumerated sources (`purchase_gc`, `redeem_gc`, `refund`, `manual`, `consume`).
- Background notification hooks reuse existing email infrastructure; configure SMTP via environment variables (`SMTP_HOST`, `SMTP_PORT`, etc.) for production.
