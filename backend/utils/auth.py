from __future__ import annotations
import functools
from typing import Callable, Iterable
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt
import hashlib
import os


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.getenv('PWD_SALT', 'static_salt_dev_only')
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def roles_required(roles: Iterable[str]) -> Callable:
    roles = set(roles)

    def decorator(fn: Callable):
        @jwt_required()
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt() or {}
            role = claims.get('role') or (claims.get('sub', {}) or {}).get('role')
            if role not in roles:
                return jsonify({"success": False, "data": None, "meta": {"error": "forbidden", "required": list(roles)}}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Alias for admin_required
def admin_required(fn: Callable):
    return roles_required(['admin'])(fn)
