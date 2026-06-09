from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from db import get_conn
from utils.notifications import send_email, send_sms

bp = Blueprint("inventory", __name__)


def _parse_date(s: str) -> str:
    return datetime.fromisoformat(s).date().isoformat()


@bp.post('/products')
def create_product():
    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip()
    price = float(payload.get('price') or 0)
    if not name:
        return jsonify({"success": False, "data": None, "meta": {"error": "name_required"}}), 400
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO products(name, price) VALUES(?, ?)', (name, price))
        pid = cur.lastrowid
        conn.commit()
    return jsonify({"success": True, "data": {"id": pid, "name": name, "price": price}, "meta": {}})


@bp.post('/batches')
def add_batch():
    payload = request.get_json(silent=True) or {}
    product_id = payload.get('product_id')
    batch_no = (payload.get('batch_no') or '').strip()
    import_date = payload.get('import_date')
    expiry_date = payload.get('expiry_date')
    qty = int(payload.get('qty') or 0)
    if not all([product_id, batch_no, import_date, expiry_date]) or qty <= 0:
        return jsonify({"success": False, "data": None, "meta": {"error": "invalid_payload"}}), 400
    try:
        import_date = _parse_date(import_date)
        expiry_date = _parse_date(expiry_date)
    except Exception:
        return jsonify({"success": False, "data": None, "meta": {"error": "bad_dates"}}), 400

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO inventory_batches(product_id, batch_no, import_date, expiry_date, qty) VALUES(?,?,?,?,?)',
            (product_id, batch_no, import_date, expiry_date, qty)
        )
        bid = cur.lastrowid
        conn.commit()
    return jsonify({"success": True, "data": {"id": bid}, "meta": {}})


@bp.get('/fefo_picklist')
def fefo_picklist():
    product_id = request.args.get('product_id', type=int)
    limit = request.args.get('limit', default=100, type=int)
    q = 'SELECT id, product_id, batch_no, import_date, expiry_date, qty FROM inventory_batches WHERE qty>0 '
    params = []
    if product_id:
        q += 'AND product_id=? '
        params.append(product_id)
    q += 'ORDER BY date(expiry_date) ASC, id ASC LIMIT ?'
    params.append(limit)
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute(q, params).fetchall()
    items = [
        {"id": r[0], "product_id": r[1], "batch_no": r[2], "import_date": r[3], "expiry_date": r[4], "qty": r[5]}
        for r in rows
    ]
    return jsonify({"success": True, "data": items, "meta": {"sorted": "fefo"}})


@bp.get('/near_expiry')
def near_expiry():
    days = request.args.get('days', default=7, type=int)
    today = datetime.utcnow().date()
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, product_id, batch_no, import_date, expiry_date, qty FROM inventory_batches WHERE qty>0').fetchall()
    results = []
    for r in rows:
        expiry = datetime.fromisoformat(r[4]).date()
        delta = (expiry - today).days
        status = 'ok'
        if delta < 0:
            status = 'expired'
        elif 0 <= delta <= days:
            status = 'near_expiry'
        if status in ('expired', 'near_expiry'):
            results.append({
                "id": r[0], "product_id": r[1], "batch_no": r[2], "import_date": r[3], "expiry_date": r[4], "qty": r[5],
                "days_to_expiry": delta, "status": status
            })
    return jsonify({"success": True, "data": results, "meta": {"days": days}})


@bp.post('/dispatch')
def dispatch():
    payload = request.get_json(silent=True) or {}
    orders = payload.get('orders') or []
    allocations = []
    with get_conn() as conn:
        cur = conn.cursor()
        for order in orders:
            pid = int(order.get('product_id'))
            need = int(order.get('qty'))
            if need <= 0:
                continue
            # FEFO select
            rows = cur.execute('SELECT id, qty FROM inventory_batches WHERE product_id=? AND qty>0 ORDER BY date(expiry_date) ASC, id ASC', (pid,)).fetchall()
            for bid, have in rows:
                if need == 0:
                    break
                take = min(need, have)
                if take > 0:
                    cur.execute('UPDATE inventory_batches SET qty=qty-? WHERE id=?', (take, bid))
                    allocations.append({"product_id": pid, "batch_id": bid, "allocated": take})
                    need -= take
        conn.commit()
    return jsonify({"success": True, "data": {"allocations": allocations}, "meta": {"strategy": "FEFO"}})


@bp.post('/notify')
def notify():
    payload = request.get_json(silent=True) or {}
    email = payload.get('email')
    phone = payload.get('phone')
    days = int(payload.get('days') or 7)

    # Compute low_stock and near/expired
    from datetime import datetime
    today = datetime.utcnow().date()
    low_stock = []
    near_or_expired = []
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT product_id, SUM(qty) FROM inventory_batches GROUP BY product_id').fetchall()
        for pid, total in rows:
            if (total or 0) < 5:
                low_stock.append({"product_id": pid, "total": int(total or 0)})
        rows = cur.execute('SELECT product_id, batch_no, expiry_date, qty FROM inventory_batches WHERE qty>0').fetchall()
        for pid, batch, ed, qty in rows:
            try:
                d = datetime.fromisoformat(ed).date()
            except Exception:
                continue
            delta = (d - today).days
            if delta < 0 or delta <= days:
                near_or_expired.append({"product_id": pid, "batch_no": batch, "expiry_date": ed, "days_to_expiry": delta, "qty": qty})

    subject = 'Inventory Alerts'
    body = f"Low stock items: {len(low_stock)}; Near/expired batches: {len(near_or_expired)}"
    email_ok = send_email(subject, body, email) if email else False
    sms_ok = send_sms(body, phone) if phone else False

    return jsonify({
        "success": True,
        "data": {
            "low_stock": low_stock,
            "batches": near_or_expired,
            "email_sent": bool(email_ok),
            "sms_sent": bool(sms_ok)
        },
        "meta": {"days": days}
    })


@bp.get('/expired_performance')
def expired_performance():
    """
    List expired batches/products and label their recent sales performance as bad/good/excellent.
    Query params:
      - days: window to look back at orders (default 30)
      - good_threshold: average daily qty >= this -> 'good' (default 5)
      - excellent_threshold: average daily qty >= this -> 'excellent' (default 10)
      - include_zero: if true, include products with zero recent sales (default true)
    Labeling: excellent > good > bad.
    """
    days = request.args.get('days', default=30, type=int)
    good_th = request.args.get('good_threshold', default=5, type=float)
    exc_th = request.args.get('excellent_threshold', default=10, type=float)
    include_zero = str(request.args.get('include_zero', 'true')).lower() != 'false'

    today = datetime.utcnow().date()
    since = today - timedelta(days=days)

    with get_conn() as conn:
        cur = conn.cursor()
        # Expired batches
        batches = cur.execute('SELECT id, product_id, batch_no, import_date, expiry_date, qty FROM inventory_batches').fetchall()
        expired = []
        prod_ids = set()
        for r in batches:
            try:
                ed = datetime.fromisoformat(r[4]).date()
            except Exception:
                continue
            if (ed - today).days < 0:
                expired.append({
                    "id": r[0], "product_id": r[1], "batch_no": r[2], "import_date": r[3], "expiry_date": r[4], "qty": r[5]
                })
                prod_ids.add(r[1])

        if not expired:
            return jsonify({"success": True, "data": [], "meta": {"days": days, "good_threshold": good_th, "excellent_threshold": exc_th}})

        # Sales aggregation last N days
        # Sum order_items.qty joined with orders by created_at
        try:
            rows = cur.execute(
                """
                SELECT oi.product_id, COALESCE(SUM(oi.qty),0) as total_qty
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE date(o.created_at) >= date(?)
                GROUP BY oi.product_id
                """,
                (since.isoformat(),)
            ).fetchall()
        except Exception:
            rows = []
        sales_map = {pid: (qty or 0) for pid, qty in rows}

        # Product names
        names = cur.execute('SELECT id, name FROM products').fetchall()
        name_map = {pid: n for pid, n in names}

    out = []
    for b in expired:
        pid = b["product_id"]
        total = float(sales_map.get(pid, 0))
        avg_daily = total / float(days) if days > 0 else total
        label = 'bad'
        if avg_daily >= exc_th:
            label = 'excellent'
        elif avg_daily >= good_th:
            label = 'good'
        if not include_zero and total == 0:
            continue
        out.append({
            "product_id": pid,
            "product_name": name_map.get(pid),
            "batch_no": b["batch_no"],
            "expiry_date": b["expiry_date"],
            "qty_remaining": b["qty"],
            "sales_last_days": int(total),
            "avg_daily": avg_daily,
            "performance": label
        })

    # Sort by performance then sales desc
    rank = {"excellent": 0, "good": 1, "bad": 2}
    out.sort(key=lambda x: (rank.get(x["performance"], 3), -x["sales_last_days"]))

    return jsonify({"success": True, "data": out, "meta": {"days": days, "good_threshold": good_th, "excellent_threshold": exc_th}})
