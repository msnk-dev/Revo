import pytest

from app.models import User


def _csrf_header(client) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}


def _login(client, email: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "ValidPassword1!"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 201), ("staff", 403), ("customer", 403), (None, 401)],
)
def test_create_staff_is_admin_only(client, create_user, role, expected_status):
    if role is not None:
        user = create_user(f"{role}-create@example.com", role)
        _login(client, user.email)
    response = client.post(
        "/api/v1/admin/staff",
        headers=_csrf_header(client),
        json={"name": "New Staff", "email": "new.staff@example.com", "password": "ValidPassword1!"},
    )
    assert response.status_code == expected_status
    if role == "admin":
        assert response.json()["role"] == "staff"


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("staff", 403), ("customer", 403), (None, 401)],
)
def test_list_staff_is_admin_only(client, create_user, role, expected_status):
    if role is not None:
        user = create_user(f"{role}-list@example.com", role)
        _login(client, user.email)
    response = client.get("/api/v1/admin/staff")
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("staff", 403), ("customer", 403), (None, 401)],
)
def test_deactivate_staff_is_admin_only(client, create_user, role, expected_status, db_session):
    target = create_user("target.staff@example.com", "staff")
    if role is not None:
        user = create_user(f"{role}-deactivate@example.com", role)
        _login(client, user.email)
    response = client.patch(
        f"/api/v1/admin/staff/{target.id}",
        headers=_csrf_header(client),
        json={"is_active": False},
    )
    assert response.status_code == expected_status
    if role == "admin":
        db_session.refresh(target)
        assert target.is_active is False


def test_admin_staff_pagination_is_constrained(client, create_user):
    admin = create_user("paging-admin@example.com", "admin")
    _login(client, admin.email)
    response = client.get("/api/v1/admin/staff?page=0&page_size=101")
    assert response.status_code == 422
    assert set(response.json()["error"]["details"]) == {"page", "page_size"}


def test_non_admin_cannot_deactivate_even_with_admin_target(client, create_user):
    target = create_user("protected.staff@example.com", "staff")
    staff = create_user("operator@example.com", "staff")
    _login(client, staff.email)
    response = client.patch(
        f"/api/v1/admin/staff/{target.id}",
        headers=_csrf_header(client),
        json={"is_active": False},
    )
    assert response.status_code == 403

