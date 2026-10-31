import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_the_builtin_development_secret():
    with pytest.raises(ValidationError):
        Settings(app_env="production", app_secret_key="local-development-secret-change-this-key")
    with pytest.raises(ValidationError):
        Settings(app_env="production", app_secret_key="replace-this-local-development-secret")
    assert Settings(app_env="production", app_secret_key="a-private-key-value-with-at-least-32-chars").app_env == "production"
