import functools

from flask import redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from . import config

_password_hash = None


def _configured_password_hash():
    global _password_hash
    if _password_hash is None and config.ADMIN_PASSWORD:
        _password_hash = generate_password_hash(config.ADMIN_PASSWORD)
    return _password_hash


def is_auth_configured():
    return bool(config.ADMIN_PASSWORD)


def check_password(password):
    password_hash = _configured_password_hash()
    return password_hash is not None and check_password_hash(password_hash, password)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if is_auth_configured() and not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped
