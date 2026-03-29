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

---

## ⚙️ Installation

```bash
git clone https://github.com/Zhelero/habitual_api
cd habitual_api

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

▶️ Run
uvicorn app.main:app --reload

🧪 Testing
pytest
65+ tests
~90% coverage

📊 API Docs
Swagger: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

📌 Example

POST /habits/

{
  "name": "Go to gym"
}