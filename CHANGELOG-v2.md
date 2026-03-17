# CHANGELOG v2 — AbotKamay WiFi SaaS Platform

**Release Date:** 2026-03-17
**Test suite:** 108 tests, all passing (original 54 + 54 new)
**Frontend:** 21 pages build successfully (npm run build)

---

## Part 1: Super Admin Panel

### Backend (`server/routers/superadmin.py`) — NEW FILE

Full platform management API protected by Basic Auth (same `admin_username`/`admin_password` as existing `/admin`).

| Endpoint | Method | Description |
|---|---|---|
| `/api/superadmin/stats` | GET | Platform-wide totals: users, orgs, hotspots, revenue, connections |
| `/api/superadmin/users` | GET | All SaaS users (paginated, searchable by email/name) |
| `/api/superadmin/users/:id` | GET | User detail with org + subscription info |
| `/api/superadmin/users/:id` | PATCH | Update user (is_active, full_name, role) |
| `/api/superadmin/organizations` | GET | All organizations (paginated) with user/hotspot counts |
| `/api/superadmin/hotspots` | GET | All hotspots platform-wide (paginated, searchable) |
| `/api/superadmin/revenue` | GET | Revenue report — daily/weekly/monthly, configurable limit |
| `/api/superadmin/plans` | GET | All subscription plans with active subscriber counts |
| `/api/superadmin/plans` | POST | Create/update plan definition |

Auth: HTTP Basic (`admin:admin_password`) — same as existing admin panel.

### Frontend (`web/app/superadmin/`) — NEW DIRECTORY

Dark-theme control panel (distinguishable from user dashboard):

- **`/superadmin`** — Platform overview: 6 metric cards (users, orgs, hotspots, connections, total/monthly revenue) + quick links
- **`/superadmin/users`** — User table with search, pagination, activate/deactivate toggle
- **`/superadmin/hotspots`** — Hotspot table with search, pagination, 30-day stats
- **`/superadmin/revenue`** — Revenue report with daily/weekly/monthly switcher, totals row
- **`/superadmin/plans`** — Plan cards with subscriber counts + create/update plan form

All superadmin pages behind Basic Auth login screen (credentials stored in `localStorage` as Base64).

---

## Part 2: Member System Enhancement

### Backend — `server/routers/saas_auth.py` extensions

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/forgot-password` | POST | Generate password reset token (stored in Redis, 30min TTL). Dev mode returns token in response. |
| `/api/auth/reset-password` | POST | Consume token from Redis, update hashed password |
| `/api/auth/me` | GET | Already existed — confirmed working |
| `/api/auth/profile` | PATCH | Update full_name, email (duplicate check), or change password (requires current_password) |
| `/api/auth/upgrade` | POST | Upgrade subscription: free → starter → pro → enterprise. Cancels previous active sub. |

### Backend — `server/routers/dashboard.py` extensions

| Endpoint | Method | Description |
|---|---|---|
| `/api/dashboard/subscription` | GET | Current subscription details (plan, fee, share%, hotspot limit, dates) |
| `/api/dashboard/billing` | GET | Payment history (based on subscription records) |
| `/api/dashboard/hotspots/:id` | DELETE | Soft-delete hotspot (set is_active=False). Org-scoped — can't delete other orgs' hotspots. |

### Frontend — New Pages

| Page | Description |
|---|---|
| `/dashboard/settings` | Profile editor (name, email) + change password form. Toast notifications. |
| `/dashboard/billing` | Current plan banner + 4 plan upgrade cards (Free/Starter/Pro/Enterprise) + payment history table |
| `/forgot-password` | Email input → returns reset token (dev mode shows token + link to reset page) |
| `/reset-password` | Token + new password form. Reads `?token=` from URL params. |

---

## Part 3: Shared Components & Integration

### `web/app/components/Toast.tsx` — NEW

Global toast notification system with success/error variants. Glassmorphism style. Auto-dismiss after 4 seconds. Used across all dashboard pages.

### Dashboard Layout (`web/app/dashboard/layout.tsx`) — UPDATED

- Added Billing and Settings nav items
- Updated to use CSS variables (`--color-brand-green`, `--color-warm-white`)
- Toast container included
- Glass card style for mobile header

### Login Page — UPDATED

- Added "Forgot password?" link
- Updated to use CSS variables and `glass-card` style
- Consistent with overall brand design

---

## Technical Notes

### bcrypt Fix
Downgraded `bcrypt` from 5.0 → 4.2.1 to fix passlib compatibility (`ValueError: password cannot be longer than 72 bytes`). This was a pre-existing issue in the repo.

### Security
- All superadmin endpoints require Basic Auth; empty password → 401
- JWT token expiry handled in `get_current_saas_user()`
- Password reset tokens expire after 30 minutes (Redis TTL)
- Profile email change checks for duplicates (409 Conflict)
- Hotspot DELETE is org-scoped (users can't delete other orgs' hotspots)

### Test Coverage

New test files:
- `server/tests/test_superadmin.py` — 18 tests covering all superadmin endpoints
- `server/tests/test_auth_extended.py` — 19 tests covering forgot-password, reset, profile update, upgrade, billing

**Total: 108 tests (54 original + 54 new), 0 failures**

---

## File Index

### New/Modified Server Files
```
server/routers/superadmin.py        NEW  — Super admin API
server/routers/saas_auth.py         MOD  — +forgot-password, reset, profile, upgrade
server/routers/dashboard.py         MOD  — +subscription, billing, DELETE hotspot
server/main.py                      MOD  — include superadmin router
server/tests/test_superadmin.py     NEW  — 18 tests
server/tests/test_auth_extended.py  NEW  — 19 tests
```

### New/Modified Frontend Files
```
web/app/components/Toast.tsx               NEW  — Toast notification component
web/app/dashboard/layout.tsx               MOD  — Added billing/settings nav
web/app/dashboard/settings/page.tsx        NEW  — Account settings page
web/app/dashboard/billing/page.tsx         NEW  — Billing & subscription page
web/app/forgot-password/page.tsx           NEW  — Forgot password page
web/app/reset-password/page.tsx            NEW  — Reset password page
web/app/login/page.tsx                     MOD  — Forgot password link, glass style
web/app/superadmin/layout.tsx              NEW  — Dark theme layout + Basic Auth gate
web/app/superadmin/page.tsx                NEW  — Platform overview dashboard
web/app/superadmin/users/page.tsx          NEW  — User management table
web/app/superadmin/hotspots/page.tsx       NEW  — Hotspot overview table
web/app/superadmin/revenue/page.tsx        NEW  — Revenue report
web/app/superadmin/plans/page.tsx          NEW  — Plan management
```
