import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_the_builtin_development_secret():
    with pytest.raises(ValidationError):
        Settings(app_env="production", app_secret_key="local-development-secret-change-this-key")
    with pytest.raises(ValidationError):
        Settings(app_env="production", app_secret_key="replace-this-local-development-secret")
    assert Settings(app_env="production", app_secret_key="a-private-key-value-with-at-least-32-chars").app_env == "production"


def test_cors_rejects_wildcard_origins():
    with pytest.raises(ValidationError):
        Settings(cors_origins="*")


def test_security_headers_and_restricted_cors(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    rejected = client.get("/health", headers={"Origin": "https://attacker.example"})
    assert "access-control-allow-origin" not in rejected.headers
