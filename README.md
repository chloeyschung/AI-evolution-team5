# Briefly

Swipe-based knowledge management app. Save content from anywhere, keep what matters, discard the rest.

**Stack:** Python 3.13 (FastAPI) · React 18 · Chrome MV3 Extension · SQLite

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [One-Time Setup](#one-time-setup)
3. [Running the Stack](#running-the-stack)
4. [Browser Extension Setup](#browser-extension-setup)
5. [End-to-End Test Checklist](#end-to-end-test-checklist)
6. [iOS / macOS Xcode Integration Guide](#ios--macos-xcode-integration-guide)
7. [Known Issues & Bugs](#known-issues--bugs)

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.13 | [python.org](https://python.org) |
| `uv` | latest | `curl -Lsf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| Chrome / Chromium | any | For extension testing |

---

## One-Time Setup

### 1. Clone and enter the repo

```bash
git clone <repo-url> Briefly
cd Briefly
```

### 2. Backend environment

Copy the example and fill in real values:

```bash
cp .env.example .env   # or use the existing .env if it's already populated
```

Open `.env` and set these **required** variables (the server will refuse to start if any are missing):

| Variable | Where to get it |
|---|---|
| `JWT_SECRET_KEY` | Any 32+ character random string, e.g. `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | 44-char Fernet key, e.g. `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `GOOGLE_CLIENT_ID` | Google Cloud Console → OAuth 2.0 Client ID |
| `GOOGLE_CLIENT_SECRET` | Same OAuth client |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/google/callback` |

Optional variables (leave as-is for local dev):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./briefly.db` | SQLite file location |
| `ANTHROPIC_API_KEY` | — | Enables AI summarisation and tag generation |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com/v1/messages` | Anthropic-compatible summary endpoint override |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20240620` | Summary model override |
| `YOUTUBE_CLIENT_ID` | — | YouTube integration |
| `YOUTUBE_CLIENT_SECRET` | — | YouTube integration |
| `VLLM_SERVER_URL` | `http://localhost:8000` | Local vLLM server (optional) |

### 3. Install Python dependencies

```bash
uv sync
```

### 4. Web dashboard environment

```bash
cd web-dashboard
cp .env.example .env
```

Edit `web-dashboard/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=<your-google-client-id>
VITE_ENABLE_TEST_LOGIN=true   # set to bypass Google OAuth in dev
```

Install JS dependencies:

```bash
npm install
cd ..
```

### 5. Browser extension environment

```bash
cd browser-extension
cp .env.example .env
```

Edit `browser-extension/.env`:

```env
VITE_GOOGLE_CLIENT_ID=<your-google-client-id>
VITE_API_BASE_URL=http://localhost:8000
```

Install JS dependencies:

```bash
npm install
cd ..
```

---

## Running the Stack

### Recommended: one command launcher

```bash
./scripts/run-stack.sh start
```

Useful controls:

```bash
./scripts/run-stack.sh status
./scripts/run-stack.sh stop
./scripts/run-stack.sh restart
```

The script will:
- auto-fill missing local `.env` defaults,
- install missing deps (`uv sync`, web/extension `npm install`),
- start backend + dashboard + extension watch (tmux when available, background otherwise).

### Manual mode (three terminals)

Start all three services manually if you prefer:

### Terminal 1 — Backend API

```bash
cd /path/to/Briefly
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

- URL: `http://localhost:8000`
- API docs (Swagger UI): `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/`
- **Database:** `briefly.db` is created automatically in the repo root on first start.

### Terminal 2 — Web Dashboard

```bash
cd web-dashboard
npm run dev
```

- URL: `http://localhost:3001`
- All `/api/*` requests are proxied automatically to `http://localhost:8000`.

### Terminal 3 — Browser Extension (dev watch)

```bash
cd browser-extension
npm run dev    # rebuilds on file change; reload extension manually in Chrome after each rebuild
```

Or build once for a stable test:

```bash
npm run build  # outputs to browser-extension/dist/
```

### Extension health checks (recommended before manual testing)

```bash
cd browser-extension
npx vitest run src/__tests__/web-guidelines-extension.test.ts
npm run test -- --run src/__tests__/extractor.test.ts
npm run typecheck
npm run build
```

---

## Browser Extension Setup

1. Build the extension: `cd browser-extension && npm run build`
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable **Developer mode** (toggle, top right)
4. Click **Load unpacked** → select the `browser-extension/dist/` folder
5. Note the **Extension ID** shown under the extension card (looks like `abcdefghijklmnopabcdefghijklmnop`)
6. In [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → your OAuth Client → Authorized redirect URIs, add:
   ```
   chrome-extension://<your-extension-id>/login/login.html
   ```
7. Rebuild the extension after updating `.env` with your Google Client ID.
8. After loading, click the extension icon → a login popup appears.

> **Tip:** After any `npm run build`, click the refresh icon on the extension card in `chrome://extensions/` to pick up changes.

---

## End-to-End Test Checklist

Use this to verify the full stack is working before handing off:

### Auth
- [ ] Open `http://localhost:3001` — redirected to login page
- [ ] Sign in with Google → redirected to dashboard
- [ ] Refresh page → still logged in (token persisted)
- [ ] Click logout → redirected to login, tokens cleared

### Content from Browser Extension
- [ ] Navigate to any article or YouTube video in Chrome
- [ ] Click extension icon → popup shows page title and URL
- [ ] Click "Save" → item appears in web dashboard inbox

### Web Dashboard Swipe Flow
- [ ] Open `http://localhost:3001/inbox`
- [ ] Swipe / click Keep on an item → moves to Kept list
- [ ] Swipe / click Discard on an item → moves to Discarded list
- [ ] `GET http://localhost:8000/api/v1/stats` in browser → counts match

### Profile & Preferences
- [ ] `http://localhost:3001/settings` → update display name → saved
- [ ] `GET http://localhost:8000/api/v1/profile` returns your user data

### Database
- [ ] `sqlite3 briefly.db "SELECT email, display_name FROM users;"` → your account exists
- [ ] `sqlite3 briefly.db "SELECT COUNT(*) FROM content WHERE user_id=(SELECT id FROM users LIMIT 1);"` → matches dashboard count

### API Docs
- [ ] `http://localhost:8000/docs` loads Swagger UI with all endpoints visible

---

## iOS / macOS Xcode Integration Guide

### Authentication Flow (recommended for native apps)

Use the **Google ID Token flow** — obtain a Google ID token using the Google Sign-In SDK on-device, then POST it to the Briefly backend:

```
POST /api/v1/auth/google
Content-Type: application/json

{
  "google_id_token": "<google-id-token-from-sdk>",
  "google_user_info": {
    "id": "1234567890",
    "email": "user@example.com",
    "name": "Jane Doe",
    "picture": "https://..."
  }
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "abc123...",
  "expires_at": "2026-04-17T14:00:00",
  "user": { "id": 1, "email": "...", "display_name": "...", "avatar_url": "..." },
  "is_new_user": true
}
```

Store both tokens securely (Keychain). The access token expires in 60 minutes.

### Token Refresh

```
POST /api/v1/auth/refresh
Content-Type: application/json

{ "refresh_token": "<stored-refresh-token>" }
```

Response: `{ "access_token": "...", "expires_at": "..." }`

> Note: The current implementation does **not** rotate the refresh token. The same refresh token remains valid for 7 days.

### All Authenticated Requests

Include the access token in every request:

```
Authorization: Bearer <access_token>
```

### CORS

CORS middleware is **not configured** on the backend. This is intentional for native clients (iOS/URLSession does not enforce CORS). Web-based clients making cross-origin XHR/fetch calls will be blocked by the browser — CORS must be added before any web deployment.

### Date / Datetime Fields

> **Critical for Swift Codable:** All datetime strings from the API are ISO 8601 without a timezone suffix (e.g. `"2026-04-16T14:00:00"`). Swift's default `ISO8601DateFormatter` requires a `Z` suffix. Use a custom `DateFormatter` or decoder strategy:

```swift
let decoder = JSONDecoder()
let formatter = DateFormatter()
formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
formatter.locale = Locale(identifier: "en_US_posix")
decoder.dateDecodingStrategy = .formatted(formatter)
```

### Key Enums (StrEnum, all lowercase)

| Enum | Values |
|---|---|
| Swipe action | `keep`, `discard` |
| Content type | `article`, `video`, `image`, `social_post`, `profile`, `deep_link` |
| Content status | `inbox`, `archived` |
| Theme | `light`, `dark`, `system` |
| Default sort | `recency`, `platform` |
| Sync frequency | `hourly`, `daily`, `weekly` |

### Complete API Endpoint Reference

All routes are prefixed with `/api/v1`.

#### Auth
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/auth/status` | Optional | Check token validity |
| POST | `/auth/google` | No | **Native app login** — send Google ID token |
| POST | `/auth/google/code` | No | Web OAuth code exchange |
| POST | `/auth/refresh` | No | Renew access token |
| POST | `/auth/logout` | Required | Revoke current session |
| POST | `/auth/account/delete` | Required | Two-step deletion (⚠ see Known Issues) |

#### Content
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/content` | Required | Manual add |
| GET | `/content` | Required | All content, `?limit=50` |
| GET | `/content/pending` | Required | Inbox (unread), `?limit&platform&tags[]` ⚠ filters currently silently ignored |
| GET | `/content/kept` | Required | Kept, `?limit&offset&platform&tags[]` |
| GET | `/content/discarded` | Required | Discarded, `?limit&offset&platform` |
| GET | `/content/trend-feed` | Required | Ranked feed, `?limit&offset&time_range&min_score` |
| GET | `/content/{id}` | Required | Detail + last swipe |
| PATCH | `/content/{id}/status` | Required | Update status |
| DELETE | `/content/{id}` | Required | Permanent delete |
| POST | `/content/{id}/categorize` | Required | AI tag generation (requires `ANTHROPIC_API_KEY`) |

#### Swipe
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/swipe` | Required | Single: `{content_id, action}` or batch: `{actions: [...]}` |

#### Stats / Search
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/stats` | Required | `{pending, kept, discarded}` counts |
| GET | `/platforms` | Required | Platform breakdown |
| GET | `/search` | Required | `?q=&limit&offset` |

#### User
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/profile` | Required | User profile |
| PATCH | `/profile` | Required | Update display_name, avatar_url, bio |
| GET | `/preferences` | Required | App preferences |
| PATCH | `/preferences` | Required | Update theme, notifications, daily_goal |
| GET | `/user/statistics` | Required | Swipe stats + streak ⚠ see Known Issues |
| GET | `/interests` | Required | Interest tags list |
| POST | `/interests` | Required | Add tag `{tag: "..."}` |
| DELETE | `/interests/{tag}` | Required | Remove tag |

#### Achievements / Reminders
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/achievements` | Required | All with progress |
| GET | `/achievements/stats` | Required | Summary stats |
| POST | `/achievements/check` | Required | Award newly earned |
| GET | `/reminders/preferences` | Required | Reminder settings |
| PUT | `/reminders/preferences` | Required | Update settings |
| GET | `/reminders/suggest` | Required | Current suggestion |
| POST | `/reminders/respond` | Required | acted / dismissed |

#### Integrations — YouTube
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/integrations/youtube/status` | Required | Connection status |
| POST | `/integrations/youtube/connect` | Required | Get OAuth URL |
| GET | `/integrations/youtube/callback` | No | OAuth callback (browser redirect) |
| POST | `/integrations/youtube/disconnect` | Required | Revoke + delete configs |
| GET | `/integrations/youtube/playlists` | Required | User's playlists |
| GET | `/integrations/youtube/configs` | Required | Sync configs |
| POST | `/integrations/youtube/configs` | Required | Create config |
| PATCH | `/integrations/youtube/configs/{id}` | Required | Update config |
| DELETE | `/integrations/youtube/configs/{id}` | Required | Delete config |
| GET | `/integrations/youtube/logs` | Required | Sync logs |
| POST | `/integrations/youtube/sync` | Required | Trigger manual sync |

#### Integrations — LinkedIn
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/integrations/linkedin/status` | Required | Always returns `is_connected: false` (no OAuth flow yet) |
| POST | `/integrations/linkedin/disconnect` | Required | Clear any stored tokens |
| GET | `/integrations/linkedin/sync/logs` | Required | Sync history |
| POST | `/integrations/linkedin/import` | Required | Import single post by URL |

---

## Known Issues & Bugs

These are confirmed bugs found during pre-handoff review. Severity labels reflect impact on a multi-user deployment.

### CRITICAL — `GET /user/statistics` leaks cross-user data

**File:** `src/data/repository.py` — `get_statistics()` method  
**Bug:** The database query has no `WHERE user_id = ?` filter. Every user receives the platform's aggregate swipe totals and a streak calculated from all users combined.  
**Impact:** Data privacy violation in any multi-user environment.  
**Workaround:** Not usable safely in production until fixed. iOS clients should avoid this endpoint.

---

### CRITICAL — `POST /auth/account/delete` crashes on confirmation step

**File:** `src/api/routes.py` — `delete_account` route  
**Bug:** Step 2 (submitting the confirmation token) references `auth_repo` which is never defined in the function scope. This raises a `NameError` and returns HTTP 500, leaving the account in an inconsistent state.  
**Impact:** Account deletion is completely non-functional.

---

### CRITICAL — `GET /content/pending` filter params silently ignored

**File:** `src/api/routes.py` — `list_pending_content` route  
**Bug:** The route accepts `?platform=` and `?tags[]=` query parameters but does not forward them to the service layer. All pending content is returned regardless of filter values.  
**Impact:** iOS filter UI will appear to work but return wrong results.

---

### HIGH — Account deletion confirmation token never returned to client

**File:** `src/api/routes.py` — `delete_account` Step 1  
**Bug:** The server generates and stores a confirmation token, but `AccountDeleteResponse` has no field to carry it back to the client. The token is unreachable; Step 2 can never be completed by a client that doesn't have server-side DB access.  
**Impact:** The entire two-step deletion flow is non-functional for API clients.

---

### HIGH — YouTube OAuth callback is vulnerable to CSRF

**File:** `src/api/routes.py` — `GET /integrations/youtube/callback`  
**Bug:** The `state` parameter carries a raw integer user ID with no CSRF token. An attacker who knows any user's ID can link their own YouTube account to a victim's Briefly account.  
**Impact:** Account hijacking via YouTube OAuth flow.  
**Workaround:** Don't expose YouTube connect flow to end users until fixed.

---

### MEDIUM — No CORS middleware

**File:** `src/api/app.py`  
**State:** `CORSMiddleware` is not registered. Native iOS clients are unaffected (URLSession doesn't enforce CORS). The web dashboard and browser extension work in development only because the Vite dev server proxies `/api/*` requests locally.  
**Impact:** Any direct browser-to-API call from a different origin will be blocked. Required before production web deployment.

---

### LOW (but blocking for iOS) — Datetime strings lack timezone suffix

**File:** All schemas in `src/api/schemas.py`  
**State:** Dates are serialised as `"2026-04-16T14:00:00"` (no `Z` or `+00:00`). Swift `Codable` with default date decoding will throw a parse error on every date field.  
**Fix needed before iOS integration:** Use a custom `DateFormatter` as shown in the [iOS guide above](#date--datetime-fields), or request that the backend append `Z` to all datetime strings.

---

## Running Tests

```bash
# Backend unit tests
uv run pytest

# Web dashboard unit tests
cd web-dashboard && npm run test

# Web dashboard E2E (requires both backend and dashboard running)
cd web-dashboard && npm run test:e2e

# Three-circle integration test (frontend → backend → DB)
cd web-dashboard && npm run test:e2e:circles
```
