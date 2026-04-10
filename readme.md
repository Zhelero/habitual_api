# Habitual API

> Production-ready REST API for habit tracking with JWT authentication, 
streak analytics, and a scalable layered architecture.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?style=flat-square)
![Tests](https://img.shields.io/badge/tests-65%20passed-brightgreen?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-~90%25-brightgreen?style=flat-square)

---

## Why this project

Habit tracking requires consistent state management and reliable statistics.

This project focuses on:
- correct streak calculation
- data consistency across habit logs
- secure authentication with token rotation and blacklist

It also demonstrates how a test suite evolves alongside the application 
and requires its own architecture.

---

## Features

- JWT authentication with token rotation and blacklist (logout support)
- Full habit CRUD with user data isolation
- Clear separation of concerns (Service / Repository architecture)
- Mark habits as done / undo
- Habit statistics — current streak, best streak, completion rate
- Heatmap data for the last 30 days
- Dashboard with aggregated stats
- Paginated habits list

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (Mapped / mapped_column) |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + token blacklist |
| Database | SQLite |
| Testing | pytest, pytest-mock, TestClient |
| Docs | Swagger UI / ReDoc (built-in) |

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
└── core/
    ├── config.py     # settings via pydantic-settings
    ├── security.py   # password hashing
    ├── jwt.py        # token creation & validation
    ├── exceptions.py # custom exceptions
    ├── handlers.py   # exception handlers
    └── middleware.py # request logging
```

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

See `.env.example` for reference.

### 3. Run

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
  "total_logs": 28,
  "completion_last_7_days": 0.86,
  "completion_last_30_days": 0.73,
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

## Testing

```bash
pytest
```

```
65 passed in 3.42s
```

Tests cover:
- 70+ automated tests
- ~90% code coverage
- Integration tests via FastAPI TestClient
- Isolated test database per test

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
