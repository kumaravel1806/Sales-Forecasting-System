from flask import Blueprint, jsonify, request
import requests
from utils.gemini import chat as gemini_chat

bp = Blueprint("connectors", __name__)


@bp.get("/sitemap")
def fetch_sitemap():
    url = request.args.get('url')
    if not url:
        return jsonify({"success": False, "data": None, "meta": {"error": "url_required"}}), 400
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return jsonify({"success": True, "data": {"content": r.text[:200000]}, "meta": {"truncated": len(r.text) > 200000}})
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "fetch_failed", "detail": str(e)}}), 400


@bp.post("/summarize")
def summarize_text():
    payload = request.get_json(silent=True) or {}
    text = (payload.get('text') or '').strip()
    if not text:
        return jsonify({"success": False, "data": None, "meta": {"error": "text_required"}}), 400
    prompt = f"Summarize the following content into 5 bullet points focusing on retail insights and anomalies.\n\n{text[:8000]}"
    try:
        resp = gemini_chat(prompt)
        return jsonify({"success": True, "data": {"summary": resp}, "meta": {"model": "gemini"}})
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "summarize_failed", "detail": str(e)}}), 400
