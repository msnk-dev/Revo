from app.seed.demo import _compliant_password, _new_demo_password


def test_generated_demo_passwords_always_meet_the_auth_rule():
    for _ in range(20):
        assert _compliant_password(_new_demo_password())


def test_legacy_demo_passwords_do_not_meet_the_auth_rule():
    assert not _compliant_password("admin123")
    assert not _compliant_password("user123")
import pytest

from app.config import settings
from app.seed.demo import _compliant_password, _new_demo_password, seed_demo_data


def test_weak_legacy_seed_flag_is_rejected_outside_demo_environment(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    with pytest.raises(RuntimeError, match="APP_ENV=demo"):
        seed_demo_data(use_legacy_demo_passwords=True)
