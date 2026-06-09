from flask import Blueprint, jsonify, request
from datetime import datetime
from db import get_conn
import socketio

# Import the socketio instance from realtime_server
try:
    from realtime_server import socketio
except ImportError:
    # Fallback if realtime_server not available
    socketio = None

bp = Blueprint("orders", __name__)


@bp.get("/")
def list_orders():
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, customer_name, customer_phone, customer_address, created_at, total FROM orders ORDER BY id DESC').fetchall()
    data = [
        {
            "id": r[0],
            "customer_name": r[1],
            "customer_phone": r[2],
            "customer_address": r[3],
            "created_at": r[4],
            "total": float(r[5]),
        }
        for r in rows
    ]
    return jsonify({"success": True, "data": data, "meta": {}})


@bp.post("/create")
def create_order():
    try:
        payload = request.get_json(silent=True) or {}
        items = payload.get('items') or []  # [{product_id, qty or quantity}]
        customer = payload.get('customer') or {}
        if not isinstance(items, list) or not items:
            return jsonify({"success": False, "data": None, "meta": {"error": "empty_cart"}}), 400
        name = (customer.get('name') or '').strip()
        phone = (customer.get('phone') or '').strip()
        address = (customer.get('address') or '').strip()

        # Fetch product prices and normalize quantities
        pids = []
        qmap = {}
        for item in items:
            pid = item.get('product_id')
            if not pid:
                continue
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                continue

            raw_qty = item.get('qty')
            if raw_qty is None:
                raw_qty = item.get('quantity')
            try:
                qty = int(raw_qty) if raw_qty is not None else 1
            except (TypeError, ValueError):
                qty = 1

            pids.append(pid_int)
            qmap[pid_int] = max(1, qty)

        if not pids:
            return jsonify({"success": False, "data": None, "meta": {"error": "invalid_items"}}), 400

        with get_conn() as conn:
            cur = conn.cursor()
            ph = ','.join(['?'] * len(pids))
            rows = cur.execute(f'SELECT id, price FROM products WHERE id IN ({ph})', pids).fetchall()
            price_map = {r[0]: float(r[1]) for r in rows}

            # Compute total
            total = 0.0
            for pid, qty in qmap.items():
                price = price_map.get(pid)
                if price is None:
                    return jsonify({"success": False, "data": None, "meta": {"error": "product_not_found", "product_id": pid}}), 400
                total += price * qty

            # Create order (supports older databases without a status column)
            status = 'completed'  # All purchases marked as completed
            now_iso = datetime.utcnow().isoformat()
            try:
                cur.execute(
                    'INSERT INTO orders(customer_name, customer_phone, customer_address, created_at, total, status) VALUES(?,?,?,?,?,?)',
                    (name, phone, address, now_iso, total, status),
                )
            except Exception as e:
                print(f"Order insert with status failed, falling back: {e}")
                cur.execute(
                    'INSERT INTO orders(customer_name, customer_phone, customer_address, created_at, total) VALUES(?,?,?,?,?)',
                    (name, phone, address, now_iso, total),
                )

            oid = cur.lastrowid
            for pid, qty in qmap.items():
                try:
                    cur.execute(
                        'INSERT INTO order_items(order_id, product_id, qty, price) VALUES(?,?,?,?)',
                        (oid, pid, qty, price_map[pid]),
                    )
                except Exception as e:
                    print(f"Order item insert with price failed, falling back: {e}")
                    cur.execute(
                        'INSERT INTO order_items(order_id, product_id, qty) VALUES(?,?,?)',
                        (oid, pid, qty),
                    )

            conn.commit()

            # Emit real-time sales update (optional)
            if socketio:
                try:
                    socketio.emit('sales_update', {
                        'type': 'sales_update',
                        'timestamp': datetime.utcnow().isoformat(),
                        'new_order': {
                            'order_id': oid,
                            'total': total,
                            'customer_name': name
                        }
                    })
                except Exception as e:
                    print(f"Error emitting sales update: {e}")

        return jsonify({"success": True, "data": {"order_id": oid, "total": total}, "meta": {}})
    except Exception as e:
        print(f"Order creation error: {e}")
        return jsonify({"success": False, "data": None, "meta": {"error": "server_error", "detail": str(e)}}), 500
