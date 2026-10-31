from collections.abc import Iterator
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argon2 import PasswordHasher

from app.deps import get_db
from app.main import app
from app.models import Base, Customer, User


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with test_sessions() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def create_user(db_session: Session):
    hasher = PasswordHasher()

    def create(
        email: str,
        role: str,
        password: str = "ValidPassword1!",
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email.lower(),
            name=email.split("@", 1)[0],
            password_hash=hasher.hash(password),
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.flush()
        if role == "customer":
            db_session.add(Customer(user_id=user.id, name=user.name or "Customer", email=user.email))
        db_session.commit()
        db_session.refresh(user)
        return user

    return create

