from flask import Blueprint, request, jsonify
from typing import Any, Dict

bp = Blueprint("assistant", __name__)


@bp.post('/chat')
def chat():
    try:
        prompt = None
        context: Dict[str, Any] | None = None
        if request.is_json:
            payload: Dict[str, Any] = request.get_json(silent=True) or {}
            prompt = payload.get('prompt')
            context = payload.get('context')
        else:
            prompt = request.form.get('prompt')
        if not prompt:
            return jsonify({"success": False, "data": None, "meta": {"error": "prompt_required"}}), 400

        try:
            from utils.gemini import chat_once
        except Exception:  # pragma: no cover
            from backend.utils.gemini import chat_once

        res = chat_once(prompt, context)
        return jsonify({"success": True, "data": res, "meta": {}})
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "assistant_failed", "detail": str(e)}}), 500
