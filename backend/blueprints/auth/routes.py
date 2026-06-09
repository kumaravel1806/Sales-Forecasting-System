from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
from db import get_conn
from utils.auth import hash_password, verify_password

bp = Blueprint("auth", __name__)


@bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not email or not password:
        return jsonify({"success": False, "data": None, "meta": {"error": "email_password_required"}}), 400
    pwdh = hash_password(password)
    with get_conn() as conn:
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users(email, username, password_hash, role, created_at) VALUES(?,?,?,?,?)',
                        (email, username or None, pwdh, 'user', datetime.utcnow().isoformat()))
            uid = cur.lastrowid
            conn.commit()
        except Exception as e:
            return jsonify({"success": False, "data": None, "meta": {"error": "conflict", "detail": str(e)}}), 400
    return jsonify({"success": True, "data": {"id": uid, "email": email}, "meta": {}})


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    if not email or not password:
        return jsonify({"success": False, "data": None, "meta": {"error": "email_password_required"}}), 400
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute('SELECT id, email, username, password_hash, role FROM users WHERE email=?', (email,)).fetchone()
    if not row or not verify_password(password, row[3]):
        return jsonify({"success": False, "data": None, "meta": {"error": "invalid_credentials"}}), 401
    # Use email as the JWT identity (must be a string) and expose role/user info via claims
    user_identity = {"id": row[0], "email": row[1], "username": row[2], "role": row[4]}
    token = create_access_token(
        identity=row[1],  # email string to avoid 'Subject must be a string' errors
        additional_claims={
            "role": row[4],
            "user_id": row[0],
            "username": row[2],
        },
    )
    return jsonify({"success": True, "data": {"token": token, "user": user_identity}, "meta": {}})


@bp.get("/me")
@jwt_required()
def me():
    user = get_jwt_identity() or {}
    return jsonify({"success": True, "data": {"user": user}, "meta": {}})
