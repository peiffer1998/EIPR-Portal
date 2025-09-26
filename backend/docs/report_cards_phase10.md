# Report Cards Phase 10 Guide

## Staff Workflow

1. Authenticate as a staff user and call `POST /api/v1/report-cards` with the owner, pet, and visit date to draft a new card.
2. `PATCH /api/v1/report-cards/{id}` updates the title, summary, rating, or linked reservation.
3. Upload photos through the documents API, then attach them with `POST /api/v1/report-cards/{id}/media`.
4. Use `POST /api/v1/report-cards/{id}/friends` to list playmates to highlight.
5. When ready, send the report with `POST /api/v1/report-cards/{id}/send`. This records the send timestamp and emails the owner using the configured SMTP server.
6. Retrieve sent cards with `GET /api/v1/report-cards` or `GET /api/v1/report-cards/{id}` for auditing.

## Owner Portal Steps

1. Sign in at `/login` on the portal and open the new **Report Cards** section in the navigation bar.
2. Filter by pet (when multiple pets are on file) to browse summaries.
3. Open a card to view detailed notes, ratings, highlighted photos, and listed playmates.
4. Cards remain available in the portal after email delivery for future reference.

## Testing Notes

- Backend end-to-end coverage is provided in `tests/test_report_cards_api.py` and `tests/test_portal_report_cards_api.py`.
- Portal unit coverage lives in `portal/src/__tests__/report-cards.test.tsx`.
- Run the full suite before releasing:
  ```bash
  .venv/bin/python -m pytest -q
  npm run build
  npm test -- --run
  ```
