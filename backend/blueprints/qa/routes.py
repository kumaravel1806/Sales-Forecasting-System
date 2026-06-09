from datetime import datetime
from flask import Blueprint, request, jsonify
from db import get_conn

bp = Blueprint("qa", __name__)


@bp.post('/ask')
def ask():
    payload = request.get_json(silent=True) or {}
    product_id = payload.get('product_id')
    question = (payload.get('question') or '').strip()
    username = (payload.get('username') or '').strip() or None
    if not product_id or not question:
        return jsonify({"success": False, "data": None, "meta": {"error": "invalid_payload"}}), 400
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO qa(product_id, username, question, answer, created_at) VALUES(?,?,?,?,?)',
                    (product_id, username, question, None, datetime.utcnow().isoformat()))
        qid = cur.lastrowid
        conn.commit()
    return jsonify({"success": True, "data": {"id": qid}, "meta": {}})


@bp.post('/answer')
def answer():
    payload = request.get_json(silent=True) or {}
    qid = payload.get('id')
    answer = (payload.get('answer') or '').strip()
    if not qid or not answer:
        return jsonify({"success": False, "data": None, "meta": {"error": "invalid_payload"}}), 400
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('UPDATE qa SET answer=? WHERE id=?', (answer, qid))
        conn.commit()
    return jsonify({"success": True, "data": {"id": qid}, "meta": {}})


@bp.get('/list')
def list_qa():
    product_id = request.args.get('product_id', type=int)
    if not product_id:
        return jsonify({"success": False, "data": None, "meta": {"error": "product_id_required"}}), 400
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, username, question, answer, created_at FROM qa WHERE product_id=? ORDER BY id DESC', (product_id,)).fetchall()
    data = []
    for r in rows:
        data.append({
            "id": r[0], "username": r[1], "question": r[2], "answer": r[3], "created_at": r[4]
        })
    return jsonify({"success": True, "data": data, "meta": {}})
