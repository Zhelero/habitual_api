# Habitual API

> Production-ready REST API for habit tracking
with JWT authentication, PostgreSQL, Alembic, logging middleware and full CI pipeline.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-layered-blue)
![Auth](https://img.shields.io/badge/auth-JWT%20rotation-green)
![Database](https://img.shields.io/badge/db-PostgreSQL-blue)
![Tests](https://img.shields.io/badge/tests-295%20passed-brightgreen?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-~98%25-brightgreen?style=flat-square)
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
- Habit statistics (current streak, best streak, completion rate)
- 30-day heatmap
- Dashboard with aggregated stats
- Paginated habits list
- Structured error handling
- Layered architecture (API / Service / Repository)
- 98% test coverage

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
│   ├── security.py   # password hashing
│   ├── jwt.py        # token creation & validation
│   ├── middleware.py
│   ├── exceptions.py # custom exceptions
│   └── handlers.py   # exception handlers
└── main.py

```
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

### Mark done
POST /habits/{id}/done

### Undo
DELETE /habits/{id}/done

### Heatmap
GET /habits/{id}/heatmap

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

The application uses PostgreSQL in production and SQLite for tests.

Migrations are managed with Alembic:

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

---
## CI

GitHub Actions pipeline:

- run PostgreSQL service
- apply Alembic migrations
- run pytest
- generate coverage

Runs on:
- push
- pull request


## Testing

```bash
pytest
```

```
295 passed in  91.72s
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

Total coverage: **98%**

The test suite verifies:
- full authentication flow (register → login → refresh → logout)
- token rotation and blacklist behavior
- business rules (duplicate actions, invalid states)
- user data isolation
- statistics correctness

The growing complexity of tests led to recognizing the need 
for test architecture refactoring to support further scaling.

---

## Key Design Decisions

**Token blacklist** — on logout, the JWT `jti` is stored in the database with its expiry time. Expired entries can be cleaned up periodically without affecting security.

**Token rotation** — on refresh, the old refresh token is immediately invalidated. Reusing a rotated token returns 401.

**User isolation** — all habit queries are scoped by `user_id`. Accessing another user's habit returns 404 (not 403) to avoid leaking resource existence.

**SQLAlchemy 2.0** — uses the modern `Mapped` / `mapped_column` syntax throughout.
