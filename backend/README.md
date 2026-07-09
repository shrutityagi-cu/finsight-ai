# FinSight AI Backend

Backend service built with FastAPI.

## Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- JWT Authentication
- Async SQLAlchemy

---

## Run

```bash
uv sync
uvicorn app.main:app --reload
```

---

## Testing

```bash
pytest
```

---

## Database

Generate migration

```bash
alembic revision --autogenerate -m "message"
```

Apply migration

```bash
alembic upgrade head
```