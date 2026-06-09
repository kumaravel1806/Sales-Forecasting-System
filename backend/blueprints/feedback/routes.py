from flask import Blueprint, jsonify, request, Response
from datetime import datetime
from db import get_conn
from utils.auth import roles_required
from flask_jwt_extended import jwt_required, get_jwt_identity
import csv
import io

bp = Blueprint("feedback", __name__)


@bp.post('/submit')
def submit_feedback():
    try:
        print("[FEEDBACK] Received feedback submission request")
        payload = request.get_json(silent=True) or {}
        print(f"[FEEDBACK] Payload: {payload}")
        
        rating = payload.get('rating')
        message = (payload.get('message') or payload.get('text') or '').strip()
        category = (payload.get('category') or 'general').strip()
        store_id = (payload.get('store_id') or '1')
        
        # Convert store_id to string if it's an integer
        if isinstance(store_id, int):
            store_id = str(store_id)
        
        print(f"[FEEDBACK] Parsed - rating: {rating}, category: {category}, message: {message}, store_id: {store_id}")
        
        if rating is None and not message:
            print("[FEEDBACK] ERROR: Missing rating and message")
            return jsonify({"success": False, "data": None, "meta": {"error": "Rating and message required"}}), 400
        
        try:
            rating = int(rating) if rating is not None else None
            if rating is not None and (rating < 1 or rating > 5):
                print(f"[FEEDBACK] ERROR: Rating out of range: {rating}")
                return jsonify({"success": False, "data": None, "meta": {"error": "Rating must be between 1-5"}}), 400
        except (ValueError, TypeError) as e:
            print(f"[FEEDBACK] ERROR: Invalid rating format: {e}")
            return jsonify({"success": False, "data": None, "meta": {"error": "Invalid rating format"}}), 400
        
        # For now, allow anonymous feedback
        user_id = None

        print(f"[FEEDBACK] Inserting into database...")
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO feedback(user_id, store_id, rating, text, category, status, created_at) VALUES(?,?,?,?,?,?,?)',
                        (user_id, store_id, rating, message, category, 'open', datetime.utcnow().isoformat()))
            fid = cur.lastrowid
            conn.commit()
            print(f"[FEEDBACK] SUCCESS: Feedback saved with ID: {fid}")
        
        return jsonify({"success": True, "data": {"id": fid, "rating": rating, "message": message}, "meta": {}})
    
    except Exception as e:
        print(f"[FEEDBACK] EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "data": None, "meta": {"error": f"Server error: {str(e)}"}}), 500


@bp.get('/')
def get_feedback():
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, user_id, store_id, rating, text, category, status, admin_reply, created_at FROM feedback ORDER BY id DESC').fetchall()
    items = [{
        "id": r[0],
        "user_id": r[1],
        "store_id": r[2],
        "rating": r[3],
        "text": r[4],
        "category": r[5],
        "status": r[6],
        "admin_reply": r[7],
        "created_at": r[8]
    } for r in rows]
    return jsonify({"success": True, "data": items, "meta": {}})


@bp.get('/list')
@roles_required(["admin"])
def list_feedback():
    store_id = request.args.get('store_id')
    with get_conn() as conn:
        cur = conn.cursor()
        if store_id:
            rows = cur.execute('SELECT id, user_id, store_id, rating, text, status, admin_reply, created_at FROM feedback WHERE store_id=? ORDER BY id DESC', (store_id,)).fetchall()
        else:
            rows = cur.execute('SELECT id, user_id, store_id, rating, text, status, admin_reply, created_at FROM feedback ORDER BY id DESC').fetchall()
    data = []
    for r in rows:
        data.append({
            "id": r[0], "user_id": r[1], "store_id": r[2], "rating": r[3], "message": r[4],
            "category": 'general', "status": r[5], "admin_reply": r[6], "created_at": r[7]
        })
    return jsonify({"success": True, "data": data, "meta": {}})


@bp.post('/<int:feedback_id>/reply')
@roles_required(["admin"])
def reply_feedback(feedback_id):
    payload = request.get_json(silent=True) or {}
    reply = (payload.get('admin_reply') or payload.get('reply') or '').strip()
    status = (payload.get('status') or 'resolved').strip()
    
    if not reply:
        return jsonify({"success": False, "data": None, "meta": {"error": "Reply message required"}}), 400
    
    with get_conn() as conn:
        cur = conn.cursor()
        # Check if feedback exists
        existing = cur.execute('SELECT id FROM feedback WHERE id=?', (feedback_id,)).fetchone()
        if not existing:
            return jsonify({"success": False, "data": None, "meta": {"error": "Feedback not found"}}), 404
            
        cur.execute('UPDATE feedback SET admin_reply=?, status=? WHERE id=?', (reply, status, feedback_id))
        conn.commit()
    return jsonify({"success": True, "data": {"id": feedback_id, "status": status}, "meta": {}})


@bp.get('/export.csv')
@roles_required(["admin"])
def export_csv():
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, user_id, store_id, rating, text, status, admin_reply, created_at FROM feedback ORDER BY id ASC').fetchall()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(['id', 'user_id', 'store_id', 'rating', 'text', 'status', 'admin_reply', 'created_at'])
    for r in rows:
        w.writerow(r)
    output.seek(0)
    return Response(output.read(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="feedback.csv"'})


@bp.get('/trends')
@roles_required(["admin"])
def trends():
    """
    Returns daily average rating and status counts. Optional filter by store_id.
    Output: { ratings: [{date, avg_rating, count}], status: [{date, open, answered, closed}] }
    """
    store_id = request.args.get('store_id')
    with get_conn() as conn:
        cur = conn.cursor()
        if store_id:
            rows = cur.execute('SELECT date(created_at), rating, status FROM feedback WHERE store_id=? ORDER BY date(created_at) ASC', (store_id,)).fetchall()
        else:
            rows = cur.execute('SELECT date(created_at), rating, status FROM feedback ORDER BY date(created_at) ASC').fetchall()
    # aggregate per date
    from collections import defaultdict
    rating_sum = defaultdict(float)
    rating_cnt = defaultdict(int)
    status_cnt = defaultdict(lambda: {"open": 0, "answered": 0, "closed": 0})
    for d, r, s in rows:
        if r is not None:
            rating_sum[d] += float(r)
            rating_cnt[d] += 1
        skey = (s or 'open').lower()
        if skey not in status_cnt[d]:
            status_cnt[d][skey] = 0
        status_cnt[d][skey] += 1
    ratings = []
    for d in sorted(rating_cnt.keys()):
        cnt = rating_cnt[d]
        avg = (rating_sum[d] / cnt) if cnt else None
        ratings.append({"date": d, "avg_rating": avg, "count": cnt})
    status = []
    for d in sorted(status_cnt.keys()):
        ent = status_cnt[d]
        status.append({"date": d, "open": ent.get("open", 0), "answered": ent.get("answered", 0), "closed": ent.get("closed", 0)})
    return jsonify({"success": True, "data": {"ratings": ratings, "status": status}, "meta": {"store_id": store_id}})


@bp.get('/my-feedback')
@jwt_required()
def my_feedback():
    """Get feedback submitted by the current user (for customer portal)"""
    try:
        user_email = get_jwt_identity()
        
        with get_conn() as conn:
            cur = conn.cursor()
            # Get user_id from email
            user = cur.execute('SELECT id FROM users WHERE email=?', (user_email,)).fetchone()
            if not user:
                return jsonify({"success": False, "meta": {"error": "User not found"}}), 404
            
            user_id = user[0]
            
            # Get all feedback by this user
            rows = cur.execute('''
                SELECT id, store_id, rating, text, category, status, admin_reply, created_at 
                FROM feedback 
                WHERE user_id=? 
                ORDER BY created_at DESC
            ''', (user_id,)).fetchall()
        
        feedback_list = []
        for r in rows:
            feedback_list.append({
                "id": r[0],
                "store_id": r[1],
                "rating": r[2],
                "message": r[3],
                "category": r[4],
                "status": r[5],
                "admin_reply": r[6],
                "created_at": r[7]
            })
        
        return jsonify({
            "success": True,
            "data": feedback_list,
            "meta": {"count": len(feedback_list)}
        })
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500

@bp.get('/analytics')
def analytics():
    """
    Comprehensive feedback analytics with ratings breakdown, category analysis, and sentiment
    """
    store_id = request.args.get('store_id')
    
    with get_conn() as conn:
        cur = conn.cursor()
        
        # Get all feedback (including category for analytics)
        if store_id:
            rows = cur.execute('SELECT rating, category, status, created_at, text FROM feedback WHERE store_id=?', (store_id,)).fetchall()
        else:
            rows = cur.execute('SELECT rating, category, status, created_at, text FROM feedback').fetchall()
        
        # Overall statistics
        total_feedback = len(rows)
        ratings = [r[0] for r in rows if r[0] is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Rating distribution (1-5 stars)
        rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in ratings:
            if r in rating_dist:
                rating_dist[r] += 1
        
        # Category breakdown
        from collections import defaultdict
        category_stats = defaultdict(lambda: {"count": 0, "ratings": []})
        for rating, category, status, created, text in rows:
            cat = category or 'general'
            category_stats[cat]["count"] += 1
            if rating:
                category_stats[cat]["ratings"].append(rating)
        
        categories = []
        for cat, stats in category_stats.items():
            avg_cat_rating = sum(stats["ratings"]) / len(stats["ratings"]) if stats["ratings"] else 0
            categories.append({
                "category": cat,
                "count": stats["count"],
                "avg_rating": round(avg_cat_rating, 2)
            })
        
        # Status breakdown
        status_stats = {"open": 0, "answered": 0, "resolved": 0, "closed": 0}
        for _, _, status, _, _ in rows:
            skey = (status or 'open').lower()
            if skey in status_stats:
                status_stats[skey] += 1
            else:
                status_stats["open"] += 1
        
        # Recent trend (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        recent_feedback = [r for r in rows if r[3] and r[3] >= thirty_days_ago]
        recent_ratings = [r[0] for r in recent_feedback if r[0] is not None]
        recent_avg = sum(recent_ratings) / len(recent_ratings) if recent_ratings else 0
        
        # Sentiment categories based on rating
        sentiment = {
            "positive": sum(1 for r in ratings if r >= 4),
            "neutral": sum(1 for r in ratings if r == 3),
            "negative": sum(1 for r in ratings if r <= 2)
        }
        
    return jsonify({
        "success": True,
        "data": {
            "overview": {
                "total_feedback": total_feedback,
                "avg_rating": round(avg_rating, 2),
                "recent_avg_rating": round(recent_avg, 2),
                "response_rate": round((status_stats.get("answered", 0) + status_stats.get("resolved", 0)) / total_feedback * 100, 1) if total_feedback > 0 else 0
            },
            "rating_distribution": rating_dist,
            "category_breakdown": categories,
            "status_breakdown": status_stats,
            "sentiment": sentiment
        },
        "meta": {}
    })
