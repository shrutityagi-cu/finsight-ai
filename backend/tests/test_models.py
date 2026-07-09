from app.models import Base, User


def test_model_metadata_is_registered() -> None:
    assert "users" in Base.metadata.tables
    assert User.__tablename__ == "users"
