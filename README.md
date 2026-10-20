# Okemzhub Inventory & Business Management

A full-stack inventory and business management platform for **OKEMZ HUB** and **TechNext360**, two sister laptop & electronics retail businesses that share a single store/database but keep separate books.

Built with **FastAPI**, **SQLAlchemy 2.0**, and a lightweight vanilla-JavaScript frontend.

---

## Features

- **Multi-business support** — one shared inventory, separate financials per business (OKEMZ HUB & TechNext360).
- **JWT authentication** with role-based access control (`admin` / `staff`).
- **Inventory management** — products, individual inventory items, and stock batches with cost tracking.
- **Inventory requests** — staff request stock; admins approve/reject.
- **Sales tracking** — record sales, attribute them to staff, and monitor monthly sales targets.
- **Expense management** — submit and approve business expenses.
- **Login auditing** — every login attempt (success or failure) is logged with IP address.
- **Auto-migration & seeding** — missing columns are backfilled and default businesses are created on first run.
- **Served frontend** — the API also serves a static single-page frontend.

---

## Tech Stack

| Layer      | Technology                                   |
|------------|----------------------------------------------|
| Backend    | FastAPI, Uvicorn                             |
| ORM        | SQLAlchemy 2.0 (typed `Mapped` models)       |
| Validation | Pydantic v2 / pydantic-settings              |
| Auth       | python-jose (JWT), bcrypt password hashing   |
| Database   | SQLite (default) — PostgreSQL-ready          |
| Frontend   | HTML, CSS, vanilla JavaScript                |

---

## Project Structure

```
.
├── app/
│   ├── main.py               # App entry point, lifespan, router registration
│   ├── database.py           # Engine, session, declarative Base
│   ├── dependencies.py       # Shared FastAPI dependencies (get_db, auth)
│   ├── core/
│   │   ├── config.py         # Settings (env-driven)
│   │   └── security.py       # Password hashing & JWT helpers
│   ├── models/               # SQLAlchemy ORM models
│   ├── routers/              # API route handlers
│   └── schemas/              # Pydantic request/response schemas
├── frontend/
│   ├── index.html
│   └── static/               # css / js / images
├── create_admin.py           # CLI to create an owner (admin) account
├── seed_data.py              # Populate the DB with realistic mock data
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+

### 1. Clone the repository

```bash
git clone https://github.com/NKASG/okemzhub-technext360.git
cd okemzhub-technext360
```

### 2. Create a virtual environment & install dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment (optional)

Create a `.env` file in the project root to override defaults:

```env
SECRET_KEY=your-strong-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=480
DATABASE_URL=sqlite:///./okemzhub.db
```

> **Important:** Always set a strong `SECRET_KEY` in production. For PostgreSQL, use
> `DATABASE_URL=postgresql+psycopg2://user:pass@host/dbname`.

### 4. Create an admin account

```bash
python create_admin.py
```

### 5. (Optional) Seed mock data

```bash
python seed_data.py
```

### 6. Run the application

```bash
uvicorn app.main:app --reload
```

The app is now available at:

- **Frontend:** http://127.0.0.1:8000/
- **Interactive API docs (Swagger):** http://127.0.0.1:8000/docs
- **Alternative docs (ReDoc):** http://127.0.0.1:8000/redoc

---

## API Overview

All routes are prefixed and grouped by tag. Authenticate via `POST /auth/token` to obtain a bearer token, then include it as `Authorization: Bearer <token>`.

| Prefix                 | Tag                 | Purpose                                      |
|------------------------|---------------------|----------------------------------------------|
| `/auth`                | Authentication      | Login and JWT token issuance                 |
| `/users`               | Users               | Manage user accounts                         |
| `/products`            | Products            | Product catalog                              |
| `/inventory`           | Inventory           | Individual inventory items                   |
| `/inventory-requests`  | Inventory Requests  | Stock requests and approvals                 |
| `/stock-batches`       | Stock Batches       | Batch stock intake with cost tracking        |
| `/sales`               | Sales               | Record and query sales                       |
| `/expenses`            | Expenses            | Submit and approve expenses                  |
| `/login-logs`          | Login Logs          | Audit log of login attempts                  |

---

## Configuration Reference

| Setting                       | Default                     | Description                              |
|-------------------------------|-----------------------------|------------------------------------------|
| `SECRET_KEY`                  | *(change in production)*    | Signing key for JWT tokens               |
| `ALGORITHM`                   | `HS256`                     | JWT signing algorithm                    |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 hours)             | Token lifetime                           |
| `DATABASE_URL`                | `sqlite:///./okemzhub.db`   | Database connection string               |

---

## Security Notes

- Passwords are hashed with **bcrypt** — never stored in plaintext.
- All login attempts are recorded in the login log for auditing.
- Do **not** commit `.env`, database files, or SSH keys — these are excluded via `.gitignore`.

---

## License

This project is proprietary to OKEMZ HUB / TechNext360. All rights reserved.
