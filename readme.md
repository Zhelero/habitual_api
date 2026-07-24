# Habitual API

> Production-ready REST API for habit tracking
with JWT authentication, PostgreSQL, Alembic, logging middleware and full CI pipeline.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-layered-blue)
![Auth](https://img.shields.io/badge/auth-JWT%20rotation-green)
![Database](https://img.shields.io/badge/db-PostgreSQL-blue)
![Tests](https://img.shields.io/badge/tests-424%20passed-brightgreen?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-~98%25-brightgreen?style=flat-square)
![Security](https://img.shields.io/badge/security-rate%20limited%20%2B%20audited-blue?style=flat-square)
![CI](https://github.com/Zhelero/habitual_api/actions/workflows/ci.yml/badge.svg)

---

## Why this project

Habit tracking requires consistent state management and reliable statistics.

This project focuses on:

- correct streak calculation
- data consistency across habit logs
- secure authentication with token rotation and blacklist
- clean service/repository architecture
- high test coverage

It also demonstrates how a test suite evolves alongside the application
and requires its own architecture.

---

## Features

- JWT authentication (access + refresh tokens)
- Refresh token rotation with reuse detection
- Token blacklist with expiration cleanup
- Request logging middleware
- Full habit CRUD with user data isolation
- Mark habits as done / undo
- Archive / restore habits, with filtering by status
- Habit statistics (current streak, best streak, completion rate)
- 30-day heatmap
- Optional notes on habit completions — attached when marking a habit done, editable only for today's entry
- Dashboard with aggregated stats
- Paginated habits list
- Structured error handling
- Layered architecture (API / Service / Repository)
- 98% test coverage
- Startup/shutdown handled via a `lifespan` context manager (not the deprecated `on_event`)
- Rate limiting on auth endpoints (`slowapi`) — 5/min login, 10/min register, brute-force protection
- CORS restricted to an explicit allow-list (`CORS_ORIGINS` env var), not `*`
- Password policy: 8–128 characters, enforced in both the schema and the service layer
- Dependency vulnerability scanning (`pip-audit`) as a CI gate, alongside GitHub Dependabot
- React UI — [habitual_ui](https://github.com/Zhelero/habitual_ui)

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Framework  | FastAPI                                 |
| ORM        | SQLAlchemy 2.0 (Mapped / mapped_column) |
| Validation | Pydantic v2                             |
| Auth       | JWT (python-jose) + token blacklist     |
| Database   | PostgreSQL                              |
| Migrations | Alembic                                 |
| Rate limiting | slowapi                              |
| CI         | GitHub Actions                          |
| Testing    | pytest, pytest-mock, TestClient         |
| Logging    | structured request middleware           |
| Docs       | Swagger UI / ReDoc (built-in)           |

---

## Architecture

The project follows a layered architecture:

- API layer — request handling (FastAPI routers)
- Service layer — business logic (streaks, stats, rules)
- Repository layer — database interaction
- Core layer — auth, security, configuration

This separation allows independent testing of each layer
and keeps business logic isolated from the framework.

---

## Project Structure

```
app/
├── api/
│   ├── routers/      # habits, auth, dashboard
│   └── schemas.py    # Pydantic request/response models
├── services/         # business logic
├── repositories/     # database access layer
├── db/
│   ├── models.py     # SQLAlchemy models
│   ├── session.py    # engine & SessionLocal
│   └── deps.py       # get_db dependency
├── core/
│   ├── config.py     # settings via pydantic-settings
│   ├── enums.py       # HabitFilter and other shared enums
│   ├── security.py   # password hashing
│   ├── jwt.py        # token creation & validation
│   ├── rate_limit.py # shared slowapi Limiter instance
│   ├── middleware.py
│   ├── exceptions.py # custom exceptions
│   └── handlers.py   # exception handlers
└── main.py
```

```
tests/
├── security/         # IDOR, JWT tampering, injection payloads, rate limits
├── api/ / services/ / repositories/ / core/
└── conftest.py       # fixtures, DB isolation, rate-limit reset between tests
```

---

## Frontend

A React UI for this API is available at [habitual_ui](https://github.com/Zhelero/habitual_ui).

Built with React + Vite + Tailwind CSS. Features login, registration, habit management, streak tracking, a 30-day heatmap, and notes on completions. Connects to this API running on `http://localhost:8000`.

To run the full stack locally, start the API first, then the UI:

```bash
# Terminal 1 — API
uvicorn app.main:app --reload

# Terminal 2 — UI
cd habitual_ui
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`.

---

## Authentication Flow

### Register

POST /auth/register

Returns:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user_id": 1
}
```

### Login
POST /auth/login

### Refresh (token rotation)
POST /auth/refresh
- old refresh token is blacklisted
- new access + refresh returned
- token reuse blocked

### Logout
POST /auth/logout
- token added to blacklist
- reuse prevented

---

## Habit Flow

### Create habit
POST /habits

### List habits
GET /habits?filter=active|archived|all

By default, only active habits are returned. Use the `filter` query parameter to view archived habits or all of them.

### Mark done
POST /habits/{id}/done

Optional body: `{"note": "..."}` (max 500 chars). Omitted or blank note is stored as `null`.

### Update today's note
PATCH /habits/{id}/done

Body: `{"note": "..."}` — replaces the note on **today's** log entry, or clears it if blank/omitted. Only today's log can be edited this way: `409` (`LogNotEditableError`) for any other date, `409` (`HabitNotMarkedError`) if the habit hasn't been marked done today at all.

### Undo
DELETE /habits/{id}/done

### Archive
PATCH /habits/{id}/archive

### Restore
PATCH /habits/{id}/restore

Archived habits are excluded from the default habit list and dashboard totals, but remain accessible by ID. They cannot be marked done or undone while archived — `mark_done` and `undo_done` return `409` for an archived habit.

### Heatmap
GET /habits/{id}/heatmap

Returns the last 30 days as `{"date", "done", "note"}` per day — `note` is `null` for days without one.

### Dashboard
GET /dashboard

Returns:
```json
{
  "total_habits": 5,
  "completed_today": 3,
  "best_streak": 12
}
```

Archived habits are excluded from `total_habits` and `best_streak`. A habit log created before archiving still counts toward `completed_today` for that day.

---

## Request Logging

### Middleware logs:

```
127.0.0.1 GET /habits -> 200 (12ms) [curl/8.14.1]
127.0.0.1 POST /auth/login -> 401 (3ms) [Mozilla/...]
127.0.0.1 POST /auth/refresh -> 500 (2ms) [pytest]
```

Logged fields:

- client IP
- HTTP method
- path
- status
- duration
- user-agent

---

### Logs

By default logs are written to:

- stdout (console)
- Docker logs (when running in container)

Example:
```
docker compose logs -f app
```

Logs include:

- request logs
- errors
- auth events
- blacklist operations
- startup info

---

## Getting Started

### 1. Clone and install

```bash
git clone https://github.com/Zhelero/habitual_api
cd habitual_api

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
DATABASE_URL=postgresql://user:password@localhost:5432/habitual
CORS_ORIGINS=http://localhost:5173
```

### 3. Run migrations

```bash
alembic upgrade head
```

### 4. Run server

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`

---

## API Docs

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## API Examples

### Register

```bash
curl -X POST http://localhost:8000/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret123"}'
```

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user_id": 1
}
```

### Create a habit

```bash
curl -X POST http://localhost:8000/habits/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Go to gym", "description": "3 times a week"}'
```

```json
{
  "id": 1,
  "name": "go to gym",
  "description": "3 times a week",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Archive a habit

```bash
curl -X PATCH http://localhost:8000/habits/1/archive/ \
  -H "Authorization: Bearer <access_token>"
```

Returns `204 No Content`. The habit is excluded from the default list and dashboard totals, but remains accessible by ID.

### Mark a habit done with a note

```bash
curl -X POST http://localhost:8000/habits/1/done/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"note": "Felt great today"}'
```

Returns `204 No Content`. `note` is optional — omit it (or send `null`) to mark done without one.

### Edit today's note

```bash
curl -X PATCH http://localhost:8000/habits/1/done/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"note": "Actually, felt amazing"}'
```

Returns `409` if the habit wasn't marked done today, or if today's log has already rolled into a past day — only today's note can be edited.

### List habits including archived

```bash
curl "http://localhost:8000/habits/?filter=all" \
  -H "Authorization: Bearer <access_token>"
```

### Get habit statistics

```bash
curl http://localhost:8000/habits/1/stats/ \
  -H "Authorization: Bearer <access_token>"
```

```json
{
  "current_streak": 5,
  "best_streak": 12,
  "completion_last_7_days": 85.71,
  "completion_last_30_days": 73.33,
  "last_7_days": [
    {"date": "2024-01-15", "done": true},
    {"date": "2024-01-14", "done": true}
  ]
}
```

### Refresh token

```bash
curl -X POST http://localhost:8000/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

---

### Database

The application uses PostgreSQL for both dev and tests — but as **two separate databases on the same server**: `habitual` for the app, `habitual_test` for the test suite (created automatically via `docker/init-test-db.sql`). This matters because `tests/conftest.py` runs `Base.metadata.drop_all()` at the end of every test session; sharing one database with the dev app used to wipe real data every time the suite ran.

Within a single test, the `db` fixture wraps everything in a SAVEPOINT (`join_transaction_mode="create_savepoint"`), so even a `commit()`/`rollback()` inside application code (e.g. fixtures, or `TokenBlacklistRepository.add()` on a duplicate key) can't leak data into the next test.

Migrations are managed with Alembic:

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

---

## CI

GitHub Actions pipeline — four jobs:

1. **lint** — Ruff + Black
2. **dependency-audit** — `pip-audit` against all three requirements files, runs in parallel with lint. Complements GitHub Dependabot (which watches passively and opens update PRs); this gates the PR itself if a known-vulnerable dependency is present.
3. **migrations** (needs lint + dependency-audit) — validates the Alembic state before running anything else:
   - fails if there is more than one Alembic head (an unmerged migration branch)
   - runs `alembic upgrade head` then `alembic check` to confirm the SQLAlchemy models match the latest migration exactly — catches a model change that was never turned into a migration
4. **test** — runs the full pytest suite with coverage, against the isolated `habitual_test` database

Runs on:
- push
- pull request

---

## Testing

```bash
pytest
```

```
424 passed in 163.01s
```

## Test Coverage

Coverage includes:

- authentication flow
- token rotation
- blacklist behavior
- middleware logging
- repository layer
- service layer
- edge cases and error handling
- race conditions
- duplicate actions
- habit archiving and restoration
- archive status filtering across repository, service, and API layers
- broken access control (IDOR) regression tests — a user can never read, update, archive, or complete another user's habit
- JWT tampering: invalid signature, wrong secret, `alg=none` forgery
- SQL/script injection payloads in user-controlled fields
- rate limiting on login/register endpoints

Total coverage: **98%**

The test suite verifies:
- full authentication flow (register → login → refresh → logout)
- token rotation and blacklist behavior
- business rules (duplicate actions, invalid states)
- user data isolation
- statistics correctness
- archived habits are excluded from default lists and dashboard stats, but remain accessible by ID
- archived habits cannot be marked done or undone

The growing complexity of tests led to recognizing the need
for test architecture refactoring to support further scaling.

---

## Key Design Decisions

**Token blacklist** — on logout, the JWT `jti` is stored in the database with its expiry time. Expired entries can be cleaned up periodically without affecting security.

**Token rotation** — on refresh, the old refresh token is immediately invalidated. Reusing a rotated token returns 401.

**User isolation** — all habit queries are scoped by `user_id`. Accessing another user's habit returns 404 (not 403) to avoid leaking resource existence.

**Habit archiving** — archiving is a soft state change (`is_archived` flag), not a delete. Archived habits keep their full history and remain retrievable by ID, but are excluded from default listings and dashboard aggregates. They cannot be marked done or undone while archived, which keeps the "completed today" count consistent with what the user can still act on.

**Note editing restricted to today** — `update_habit_log_note` only ever targets `datetime.now(timezone.utc).date()`; there's no date parameter to pass a past day in, by design. Past log entries are historical record, not a draft — allowing edits to them would let a user quietly rewrite what "actually happened" on a given day, which undermines the heatmap and stats as a trustworthy log. `HabitNotMarkedError` (no log for today yet) and `LogNotEditableError` (trying to touch anything but today) both return `409`, not `404`, since the habit itself exists — it's the *action* that's invalid for the current state, not the resource that's missing.

**SQLAlchemy 2.0** — uses the modern `Mapped` / `mapped_column` syntax throughout.

**Test isolation** — the test suite runs against its own `habitual_test` database and wraps each test in a SAVEPOINT, so `commit()`/`rollback()` calls inside application code can't leak state across tests or into the dev database.

**Timezone-aware timestamps** — all `created_at`/`updated_at`/`expires_at` columns are `TIMESTAMP WITH TIME ZONE`. The application always writes UTC-aware datetimes; storing them without timezone info would silently strip that and invite subtle comparison bugs later.

**Rate limiting** — `slowapi` limits `/auth/login/` (5/min) and `/auth/register/` (10/min) per IP. The test suite resets the limiter's in-memory storage before every test (`tests/conftest.py`); otherwise counters would accumulate across the whole run the same way the DB used to before it got its own isolated test database.

**CORS as an explicit allow-list** — `allow_origins=["*"]` combined with `allow_credentials=True` lets any site make requests to the API. Origins are now read from `CORS_ORIGINS` (comma-separated env var), defaulting to `http://localhost:5173`.

**Password policy** — 8–128 characters, checked in both the Pydantic schema (`RegisterRequest`) and `AuthService.register()`, so the rule holds even for direct service-layer calls that bypass the API.