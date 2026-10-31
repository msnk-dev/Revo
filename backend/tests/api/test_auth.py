import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Customer, PasswordResetToken, User
from app.services import auth as auth_service


def _login(client, email: str, password: str = "ValidPassword1!"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _csrf_header(client) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}


def test_signup_ignores_role_and_creates_linked_customer(client, db_session):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Ada Lovelace",
            "email": " ADA@Example.COM ",
            "password": "ValidPassword1!",
            "role": "admin",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "customer"
    assert response.json()["email"] == "ada@example.com"
    user = db_session.scalar(select(User).where(User.email == "ada@example.com"))
    customer = db_session.scalar(select(Customer).where(Customer.user_id == user.id))
    assert user.role == "customer"
    assert customer.name == "Ada Lovelace"
    assert client.cookies.get("access_token")
    assert "HttpOnly" in response.headers.get("set-cookie", "")


@pytest.mark.parametrize(
    "password",
    ["Abcdef1!", "lowercase1!", "UPPERCASE1!", "NoSpecial123"],
)
def test_signup_rejects_each_password_rule(client, password):
    response = client.post(
        "/api/v1/auth/signup",
        json={"name": "Test User", "email": "test@example.com", "password": password},
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["password"]


@pytest.mark.parametrize("password", ["admin123", "Abcdef1!", "lowercase1!", "UPPERCASE1!", "NoSpecial123"])
def test_reset_rejects_passwords_that_break_the_password_rule(client, password):
    response = client.post(
        "/api/v1/auth/reset",
        json={"token": "a" * 32, "new_password": password},
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"]["new_password"]


def test_signup_rejects_unknown_fields(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "ValidPassword1!",
            "is_admin": True,
        },
    )
    assert response.status_code == 422
    assert "is_admin" in response.json()["error"]["details"]


def test_signup_email_is_case_insensitively_unique(client):
    first = client.post(
        "/api/v1/auth/signup",
        json={"name": "Test User", "email": "test@example.com", "password": "ValidPassword1!"},
    )
    second = client.post(
        "/api/v1/auth/signup",
        json={"name": "Other User", "email": "TEST@EXAMPLE.COM", "password": "ValidPassword1!"},
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


def test_login_and_me_work_for_each_role(client, create_user):
    for role in ("admin", "staff", "customer"):
        email = f"{role}@example.com"
        user = create_user(email, role)
        login_response = _login(client, email)
        assert login_response.status_code == 200
        me_response = client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["role"] == role
        assert me_response.json()["user_id"] == user.id
        if role == "customer":
            assert me_response.json()["customer_id"] is not None


def test_login_rejects_invalid_credentials_and_inactive_users(client, create_user):
    create_user("inactive@example.com", "staff", is_active=False)
    bad_password = _login(client, "missing@example.com", "WrongPassword1!")
    inactive = _login(client, "inactive@example.com", "ValidPassword1!")
    assert bad_password.status_code == inactive.status_code == 401
    assert bad_password.json()["error"]["message"] == inactive.json()["error"]["message"]


def test_login_rate_limits_after_five_failures(client, create_user):
    create_user("rate@example.com", "staff")
    auth_service._login_failures.clear()
    for _ in range(5):
        assert _login(client, "rate@example.com", "WrongPassword1!").status_code == 401
    blocked = _login(client, "rate@example.com", "WrongPassword1!")
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "900"
    auth_service._login_failures.clear()


def test_refresh_rotates_tokens_and_logout_invalidates_refresh(client, create_user):
    create_user("refresh@example.com", "staff")
    assert _login(client, "refresh@example.com").status_code == 200
    old_refresh = client.cookies.get("refresh_token")
    refreshed = client.post("/api/v1/auth/refresh", headers=_csrf_header(client))
    assert refreshed.status_code == 200
    assert client.cookies.get("refresh_token") != old_refresh

    old_refresh = client.cookies.get("refresh_token")
    logout = client.post("/api/v1/auth/logout", headers=_csrf_header(client))
    assert logout.status_code == 204
    client.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
    client.cookies.set("csrf_token", "test-csrf", path="/")
    blocked = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": "test-csrf"})
    assert blocked.status_code == 401


def test_cookie_mutations_require_csrf_token(client, create_user):
    create_user("csrf@example.com", "staff")
    assert _login(client, "csrf@example.com").status_code == 200
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_forgot_response_does_not_enumerate_accounts(client, create_user, db_session, monkeypatch):
    create_user("known@example.com", "customer")
    sent_messages: list[tuple[str, str, str]] = []
    monkeypatch.setattr(auth_service, "send_plain", lambda to, subject, body: sent_messages.append((to, subject, body)))

    known = client.post("/api/v1/auth/forgot", json={"email": "known@example.com"})
    unknown = client.post("/api/v1/auth/forgot", json={"email": "unknown@example.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(sent_messages) == 1
    raw_token = sent_messages[0][2].splitlines()[-1]
    stored = db_session.scalar(select(PasswordResetToken))
    assert stored.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert raw_token not in stored.token_hash


def test_reset_token_is_single_use_and_revokes_old_sessions(client, create_user, monkeypatch):
    create_user("reset@example.com", "customer")
    _login(client, "reset@example.com")
    old_refresh = client.cookies.get("refresh_token")
    sent_messages: list[str] = []
    monkeypatch.setattr(auth_service, "send_plain", lambda to, subject, body: sent_messages.append(body))
    assert client.post("/api/v1/auth/forgot", json={"email": "reset@example.com"}).status_code == 202
    raw_token = sent_messages[0].splitlines()[-1]

    reset = client.post(
        "/api/v1/auth/reset",
        json={"token": raw_token, "new_password": "NewPassword2!"},
    )
    reused = client.post(
        "/api/v1/auth/reset",
        json={"token": raw_token, "new_password": "AnotherPassword3!"},
    )
    assert reset.status_code == 200
    assert reused.status_code == 400
    client.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
    invalidated = client.post("/api/v1/auth/refresh", headers=_csrf_header(client))
    assert invalidated.status_code == 401


def test_expired_reset_token_is_rejected(client, create_user, db_session, monkeypatch):
    create_user("expired@example.com", "customer")
    sent_messages: list[str] = []
    monkeypatch.setattr(auth_service, "send_plain", lambda to, subject, body: sent_messages.append(body))
    client.post("/api/v1/auth/forgot", json={"email": "expired@example.com"})
    raw_token = sent_messages[0].splitlines()[-1]
    stored = db_session.scalar(select(PasswordResetToken))
    stored.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/reset",
        json={"token": raw_token, "new_password": "NewPassword2!"},
    )
    assert response.status_code == 400
    assert "token" in response.json()["error"]["details"]

