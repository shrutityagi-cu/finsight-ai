import os


def pytest_configure():
    # Ensure the app can import and DB URL parsing works during test runs.
    # This does not touch application business logic.
    os.environ.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://finsight:postgres@localhost:5432/finsight"
    )

