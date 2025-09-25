# OPS P5 – Feeding & Medication Boards

## Overview
This track adds daily operational views for feeding, medication, and printable run cards. All endpoints require an authenticated staff, manager, admin, or superadmin account. Data is scoped to the caller’s account and location.

## Feeding Board
```
GET /api/v1/feeding/today?location_id=<UUID>&service=boarding|daycare
```
Returns grouped feeding rows per reservation with schedule items. Each item includes the scheduled time (UTC-normalised), food, quantity, and notes. Use the `service` query to filter between boarding and daycare bookings.

Example:
```
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/feeding/today?location_id=$LOCATION_ID&service=boarding"
```

## Medication Board
```
GET /api/v1/medication/today?location_id=<UUID>
```
Provides medication rows with dosage/timing. Results include every reservation that has medication schedules today for the selected location.

Example:
```
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/medication/today?location_id=$LOCATION_ID"
```

## Printable Run Cards
```
GET /api/v1/run-cards/print?date=YYYY-MM-DD&location_id=<UUID>
```
Renders an HTML sheet suitable for printing. Feedings and medications are displayed in tables, grouped by pet and owner. Requests are logged with account, location, and date metadata for traceability.

Example:
```
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/run-cards/print?date=2025-09-25&location_id=$LOCATION_ID" \
  -o run-cards.html
```

## Notes
- All time filtering respects the location’s timezone before converting to UTC for storage queries.
- These endpoints do not alter invoices, payments, pricing, or reservation schemas as required by the track scope.
- To preview locally within the ops P5 stack, supply the `COMPOSE_PROJECT_NAME=eipr-ops-p5` overrides when starting Docker compose.
