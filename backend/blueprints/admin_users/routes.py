from flask import Blueprint, jsonify, request
from db import get_conn
from utils.auth import roles_required
from datetime import datetime

bp = Blueprint("admin_users", __name__)


@bp.get("/")
@roles_required(["admin"])
def list_users():
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, email, username, role, created_at FROM users ORDER BY id ASC').fetchall()
    data = [{"id": r[0], "email": r[1], "username": r[2], "role": r[3], "created_at": r[4]} for r in rows]
    return jsonify({"success": True, "data": data, "meta": {}})


@bp.post("/")
@roles_required(["admin"])
def create_user():
    payload = request.get_json(silent=True) or {}
    email = (payload.get('email') or '').strip().lower()
    username = (payload.get('username') or '').strip() or None
    role = (payload.get('role') or 'user').strip()
    password_hash = payload.get('password_hash')  # Expect hashed from admin tool or generate server-side if plaintext provided as 'password'
    password = payload.get('password')
    if not email or (not password_hash and not password):
        return jsonify({"success": False, "data": None, "meta": {"error": "email_password_required"}}), 400
    if not password_hash:
        from utils.auth import hash_password
        password_hash = hash_password(password)
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users(email, username, password_hash, role, created_at) VALUES(?,?,?,?,?)',
                        (email, username, password_hash, role, datetime.utcnow().isoformat()))
            uid = cur.lastrowid
            conn.commit()
        except Exception as e:
            return jsonify({"success": False, "data": None, "meta": {"error": "conflict", "detail": str(e)}}), 400
    return jsonify({"success": True, "data": {"id": uid}, "meta": {}})


@bp.delete("/<int:user_id>")
@roles_required(["admin"])
def delete_user(user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
    return jsonify({"success": True, "data": {"id": user_id}, "meta": {}})
