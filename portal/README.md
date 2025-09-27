# Eastern Iowa Pet Resort Portal UI

This package hosts both the pet-parent portal and the internal staff console for the EIPR platform. It is a Vite/React + TypeScript single-page application that talks to the FastAPI backend.

## Getting started

```bash
npm install
npm run dev
```

By default the app proxied requests to `/api/v1`. Set `VITE_API_BASE_URL` in `.env.local` if the backend is exposed elsewhere.

## Available npm scripts

- `npm run dev` – start Vite in development mode
- `npm run build` – type-check and build the production bundle
- `npm run preview` – preview the production build locally
- `npm run lint` – run ESLint
- `npm run test` – run unit tests with Vitest

## Staff console (/staff)

The staff UI now lives alongside the owner portal inside this application.

| Path | Description |
| --- | --- |
| `/staff/login` | Dedicated staff sign-in screen using `/api/v1/auth/token` |
| `/staff` | Staff shell with navigation, dashboard tiles, and toast notifications |
| `/staff/reservations/new` | Create reservations using the `ReservationCreate` schema |
| `/staff/grooming/new` | Book grooming appointments and preview live slot availability |
| `/staff/reports` | Download CSV exports; prefers `/reports-max/*.csv` and falls back to JSON |
| `/staff/admin/users` | List staff users for the active account |
| `/staff/waitlist`/`/staff/timeclock`/`/staff/tips`/`/staff/payroll` | Feature stubs reserved for future phases |

### Session handling

Staff authentication is isolated from the pet-parent portal. Tokens are stored under the `eipr.staff.session` key and applied via a dedicated Axios client. Background refreshes keep `/api/v1/users/me` in sync and session errors surface through toast notifications.

### Notifications

The staff experience includes a lightweight toast system. Actions such as booking reservations, pulling availability, or downloading reports trigger contextual success/error banners that dismiss automatically or on click.

## Development tips

- Ensure the backend is running with the latest migrations before hitting staff routes.
- Grooming availability queries require valid UUIDs for location, service, and optionally specialist/add-ons.
- CSV downloads fall back to JSON aggregation if the `/reports-max` endpoints are unavailable, so backend-only environments still work.
