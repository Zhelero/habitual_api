# Habitual

Habitual is a REST API for habit tracking with authentication, statistics, and progress tracking.

Built with FastAPI, SQLite, and pytest.

---

## 🚀 Features

- User authentication (JWT)
- Create, update, delete habits
- Mark habits as done / undo
- Habit statistics (streaks, completion rate)
- Dashboard with aggregated stats
- Pagination for habits list
- Token blacklist (logout support)

---

## 🛠 Tech Stack

- FastAPI
- SQLAlchemy
- SQLite
- Pytest
- Postman

---

## 📦 Project Structure

app/
- api/            # routers
- services/       # business logic
- repositories/   # database access
- db/             # models, session
- core/           # config, security, jwt
