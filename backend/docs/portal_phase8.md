# Phase 8 Customer Portal Guide

## Local prerequisites
- Start infrastructure: `docker compose up -d api db redis mailhog minio createbuckets`
- Launch the portal dev server: `docker compose up -d portal`
- Ensure `.env` sets `PORTAL_ACCOUNT_SLUG` to the target account slug.

## Owner experience walkthrough
1. Visit `http://localhost:5173/login` and register as a new pet parent.
2. Sign in and land on the dashboard showing pets, upcoming stays, invoices, and document count.
3. Navigate to **Reservations**
   - Submit a boarding request via the form (choose pet, service, start/end, notes).
   - Cancel any pending reservation directly from the upcoming list.
4. Go to **Invoices**
   - Open an unpaid invoice, enter test card details (4242 4242 4242 4242) and submit.
   - Confirm the success banner appears and the invoice moves to the paid list.
5. Visit **Uploads**
   - Select a target (owner or pet), choose a file, optionally add notes, and upload.
   - Validate the compressed WebP link is available in the document gallery.

## Key API endpoints
- `POST /api/v1/portal/login` and `/register_owner`
- `GET /api/v1/portal/me` – now includes documents array
- `POST /api/v1/portal/reservations/request` and `POST /{id}/cancel`
- `POST /api/v1/portal/payments/create-intent` → returns `client_secret`, `amount_due`
- `POST /api/v1/portal/documents/presign` → `upload_ref`, `upload_url`
- `PUT /api/v1/portal/documents/uploads/{upload_ref}` to stream bytes
- `POST /api/v1/portal/documents/finalize` → returns stored document metadata
- `GET /api/v1/storage/usage` – staff summary of original vs WebP bytes

## Testing checklist
- Backend: `PYTHONPATH=. .venv/bin/python -m pytest -q`
- Frontend unit tests: `npm test`
- Frontend build: `npm run build`

All three commands must pass with no warnings before completing Phase 8.
