from vclone import auth, config


def test_auth_disabled_when_no_password(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_PASSWORD", None)
    monkeypatch.setattr(auth, "_password_hash", None)
    assert auth.is_auth_configured() is False


def test_check_password_accepts_correct_and_rejects_wrong(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "correct-horse-battery-staple")
    monkeypatch.setattr(auth, "_password_hash", None)

    assert auth.is_auth_configured() is True
    assert auth.check_password("correct-horse-battery-staple") is True
    assert auth.check_password("wrong-password") is False
