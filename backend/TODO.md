# TODO - Alembic initial migration

- [x] Inspect database-layer files: `backend/app/database/session.py`, `backend/app/database/base.py`
- [x] Inspect Alembic config: `backend/alembic/env.py`
- [x] Fix Alembic env wiring so `alembic revision --autogenerate` can run in this environment
- [x] Ensure Alembic template exists to allow revision generation (`alembic/script.py.mako`)
- [x] Install missing DB driver dependency needed by SQLAlchemy/Alembic: `psycopg2-binary`
- [x] Generate initial Alembic migration with autogenerate: `initial_schema`
- [x] (Optional) Verify migration file is present and syntactically valid

- [ ] (Optional) Run `alembic upgrade head` against the configured database

