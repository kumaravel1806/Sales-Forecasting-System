import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from db import get_conn

bp = Blueprint("reviews", __name__)

ALLOWED_IMG = {".png", ".jpg", ".jpeg", ".webp"}


def _photo_dir():
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads", "photos")
    path = os.path.abspath(base)
    os.makedirs(path, exist_ok=True)
    return path


@bp.post("/submit")
def submit_review():
    product_id = request.form.get("product_id", type=int)
    rating = request.form.get("rating", type=int)
    text = request.form.get("text", type=str)
    username = request.form.get("username", type=str)
    if not product_id or not rating or rating < 1 or rating > 5:
        return jsonify({"success": False, "data": None, "meta": {"error": "invalid_payload"}}), 400

    photo_path = None
    if "photo" in request.files and request.files["photo"].filename:
        f = request.files["photo"]
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ALLOWED_IMG:
            fname = f"{int(datetime.utcnow().timestamp())}_{secure_filename(f.filename)}"
            out = os.path.join(_photo_dir(), fname)
            f.save(out)
            photo_path = out

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO reviews(product_id, username, rating, text, photo_path, created_at) VALUES(?,?,?,?,?,?)',
            (product_id, username, rating, text, photo_path, datetime.utcnow().isoformat())
        )
        rid = cur.lastrowid
        conn.commit()
    return jsonify({"success": True, "data": {"id": rid, "photo_path": photo_path}, "meta": {}})


@bp.get("/list")
def list_reviews():
    product_id = request.args.get("product_id", type=int)
    if not product_id:
        return jsonify({"success": False, "data": None, "meta": {"error": "product_id_required"}}), 400
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, username, rating, text, photo_path, created_at FROM reviews WHERE product_id=? ORDER BY id DESC', (product_id,)).fetchall()
    data = []
    for r in rows:
        data.append({
            "id": r[0], "username": r[1], "rating": r[2], "text": r[3], "photo_path": r[4], "created_at": r[5]
        })
    return jsonify({"success": True, "data": data, "meta": {}})
