from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from db import get_conn
from flask_jwt_extended import jwt_required, get_jwt_identity
import numpy as np

bp = Blueprint("analytics", __name__)

# Import the predictive analytics
try:
    from .predictive import SalesPredictor
    predictor = SalesPredictor()
except ImportError:
    predictor = None


@bp.get("/predictive/dashboard")
def predictive_dashboard():
    """Get comprehensive real-time predictive analytics dashboard"""
    try:
        if not predictor:
            return _fallback_predictive_data()
        
        # Sales predictions
        sales_predictions = predictor.predict_future_sales(30)
        
        # Inventory health
        inventory_health = predictor.get_inventory_health_metrics()
        
        # Real-time alerts
        alerts = predictor.get_real_time_alerts()
        
        # Current performance metrics
        current_metrics = _get_current_performance()
        
        # Trend analysis
        trend_analysis = _analyze_trends()
        
        return jsonify({
            "success": True,
            "data": {
                "sales_predictions": sales_predictions,
                "inventory_health": inventory_health,
                "real_time_alerts": alerts,
                "current_metrics": current_metrics,
                "trend_analysis": trend_analysis,
                "last_updated": datetime.now().isoformat()
            },
            "meta": {
                "forecast_days": 30,
                "data_freshness": "real-time",
                "model_version": "v1.0"
            }
        })
        
    except Exception as e:
        print(f"Predictive dashboard error: {e}")
        return _fallback_predictive_data()

def _fallback_predictive_data():
    """Fallback data when predictor is not available"""
    return jsonify({
        "success": True,
        "data": {
            "sales_predictions": _generate_mock_predictions(30),
            "inventory_health": _get_mock_inventory_health(),
            "real_time_alerts": _get_mock_alerts(),
            "current_metrics": _get_current_performance(),
            "trend_analysis": {"trend": "stable", "insights": []},
            "last_updated": datetime.now().isoformat()
        },
        "meta": {
            "forecast_days": 30,
            "data_freshness": "demo",
            "model_version": "demo"
        }
    })

def _generate_mock_predictions(days):
    """Generate mock predictions for demo"""
    predictions = []
    base_date = datetime.now().date()
    
    for i in range(days):
        date = base_date + timedelta(days=i+1)
        # Add some variation and trend
        base_orders = 20 + i * 0.5
        variation = np.random.normal(0, 3)
        pred_orders = max(5, int(round(base_orders + variation)))
        pred_revenue = pred_orders * np.random.uniform(200, 600)
        
        predictions.append({
            'date': date.strftime('%Y-%m-%d'),
            'predicted_orders': pred_orders,
            'predicted_revenue': round(pred_revenue, 2),
            'predicted_avg_order': round(pred_revenue / pred_orders, 2),
            'confidence': max(0.4, 1.0 - (i / days) * 0.4)
        })
    
    return predictions

def _get_mock_inventory_health():
    """Get mock inventory health for demo"""
    return {
        'total_inventory_value': 250000,
        'stock_distribution': {
            'in_stock': {'count': 45, 'value': 200000},
            'low_stock': {'count': 8, 'value': 40000},
            'out_of_stock': {'count': 3, 'value': 10000}
        },
        'expiry_analytics': {
            'good': {'batches': 50, 'quantity': 1000, 'value': 200000},
            'expiring_this_month': {'batches': 5, 'quantity': 100, 'value': 40000},
            'expiring_soon': {'batches': 2, 'quantity': 50, 'value': 10000},
            'expired': {'batches': 1, 'quantity': 20, 'value': 5000}
        },
        'category_performance': [
            ('Electronics', 15, 200, 150000),
            ('Food', 20, 500, 60000),
            ('Sports', 10, 150, 25000),
            ('General', 11, 100, 15000)
        ],
        'health_score': 85.0,
        'at_risk_percentage': 22.0
    }

def _get_mock_alerts():
    """Get mock alerts for demo"""
    return [
        {
            'type': 'critical_stock',
            'severity': 'high',
            'message': 'Laptop Pro 15 (Electronics) is out of stock (0 units)',
            'timestamp': datetime.now().isoformat(),
            'product_id': 'Laptop Pro 15'
        },
        {
            'type': 'expiry_alert',
            'severity': 'medium',
            'message': 'Organic Honey (Food) batch HNY001 expires in 5 days (25 units)',
            'timestamp': (datetime.now() - timedelta(minutes=30)).isoformat(),
            'batch_no': 'HNY001'
        },
        {
            'type': 'high_value_risk',
            'severity': 'medium',
            'message': 'High-value item Premium Laptop (₹45,000) at risk of expiry',
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'value': 45000
        }
    ]

def _get_current_performance():
    """Get current performance metrics"""
    with get_conn() as conn:
        cur = conn.cursor()
        
        # Today's performance
        today = datetime.now().date()
        today_data = cur.execute('''
            SELECT 
                COUNT(*) as orders,
                COALESCE(SUM(total), 0) as revenue,
                COUNT(DISTINCT customer_name) as customers
            FROM orders 
            WHERE DATE(created_at) = ?
        ''', (today,)).fetchone()
        
        # Yesterday's performance for comparison
        yesterday = today - timedelta(days=1)
        yesterday_data = cur.execute('''
            SELECT 
                COUNT(*) as orders,
                COALESCE(SUM(total), 0) as revenue,
                COUNT(DISTINCT customer_name) as customers
            FROM orders 
            WHERE DATE(created_at) = ?
        ''', (yesterday,)).fetchone()
        
        # This week
        week_start = today - timedelta(days=today.weekday())
        week_data = cur.execute('''
            SELECT 
                COUNT(*) as orders,
                COALESCE(SUM(total), 0) as revenue,
                COUNT(DISTINCT customer_name) as customers
            FROM orders 
            WHERE DATE(created_at) >= ?
        ''', (week_start,)).fetchone()
        
        # This month
        month_start = today.replace(day=1)
        month_data = cur.execute('''
            SELECT 
                COUNT(*) as orders,
                COALESCE(SUM(total), 0) as revenue,
                COUNT(DISTINCT customer_name) as customers
            FROM orders 
            WHERE DATE(created_at) >= ?
        ''', (month_start,)).fetchone()
        
        # Inventory metrics
        inventory_data = cur.execute('''
            SELECT 
                COUNT(*) as total_products,
                COUNT(*) FILTER (WHERE stock_quantity = 0) as out_of_stock,
                COUNT(*) FILTER (WHERE stock_quantity > 0 AND stock_quantity < min_stock_level) as low_stock,
                COALESCE(SUM(price * stock_quantity), 0) as inventory_value
            FROM products
        ''').fetchone()
        
        return {
            "today": {
                "orders": today_data[0] or 0,
                "revenue": today_data[1] or 0,
                "customers": today_data[2] or 0
            },
            "yesterday": {
                "orders": yesterday_data[0] or 0,
                "revenue": yesterday_data[1] or 0,
                "customers": yesterday_data[2] or 0
            },
            "this_week": {
                "orders": week_data[0] or 0,
                "revenue": week_data[1] or 0,
                "customers": week_data[2] or 0
            },
            "this_month": {
                "orders": month_data[0] or 0,
                "revenue": month_data[1] or 0,
                "customers": month_data[2] or 0
            },
            "inventory": {
                "total_products": inventory_data[0] or 0,
                "out_of_stock": inventory_data[1] or 0,
                "low_stock": inventory_data[2] or 0,
                "total_value": inventory_data[3] or 0
            }
        }

def _analyze_trends():
    """Analyze business trends"""
    # Mock trend analysis for demo
    return {
        "trend": "increasing",
        "orders_trend_percent": 12.5,
        "revenue_trend_percent": 18.3,
        "insights": [
            {"type": "positive", "message": "Orders increased by 12.5% this week"},
            {"type": "positive", "message": "Revenue grew by 18.3% this week"},
            {"type": "info", "message": "Best performing day: Friday"}
        ],
        "best_day": "Friday"
    }


@bp.get("/dashboard")
def dashboard():
    print("DEBUG: Dashboard function called!")
    today = datetime.utcnow().date()
    low_stock = 0
    near_expiry_count = 0
    expired_count = 0
    total_products = 0
    total_revenue = 0
    total_orders = 0
    
    with get_conn() as conn:
        cur = conn.cursor()
        
        # Get total products
        total_products = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        print(f"DEBUG: Total products from DB: {total_products}")
        
        # Low stock: count products where stock is below minimum
        low_stock = cur.execute('''
            SELECT COUNT(*) FROM products 
            WHERE stock_quantity > 0 AND stock_quantity < min_stock_level
        ''').fetchone()[0]
        
        # Critical stock (out of stock)
        critical_stock = cur.execute('''
            SELECT COUNT(*) FROM products WHERE stock_quantity = 0
        ''').fetchone()[0]
        
        # Near expiry: count unique batches expiring in next 7 days
        near_expiry_count = cur.execute('''
            SELECT COUNT(*)
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) BETWEEN date('now') AND date('now', '+7 days')
        ''').fetchone()[0]
        
        # Expired: count unique batches that have expired
        expired_count = cur.execute('''
            SELECT COUNT(*)
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) < date('now')
        ''').fetchone()[0]
        
        # Get total orders and revenue
        orders_data = cur.execute('SELECT COUNT(*), COALESCE(SUM(total), 0) FROM orders WHERE created_at >= ?', 
                                (today - timedelta(days=30),)).fetchone()
        total_orders = orders_data[0] or 0
        total_revenue = orders_data[1] or 0
    
    metrics = {
        "low_stock": low_stock,
        "critical_stock": critical_stock,
        "near_expiry": near_expiry_count,
        "expired": expired_count,
        "total_products": total_products,
        "total_revenue": total_revenue,
        "total_orders": total_orders
    }
    print(f"DEBUG: Returning metrics: {metrics}")
    return jsonify({"success": True, "data": metrics, "meta": {"window_days": 7}})


@bp.get("/dashboard/realtime")
def dashboard_realtime():
    """Get comprehensive real-time dashboard data for e-commerce"""
    try:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)
        
        # Manually manage DB context so the connection stays open
        # for the whole function while we run all queries.
        conn_ctx = get_conn()
        conn = conn_ctx.__enter__()
        cur = conn.cursor()
        
        # === KPI METRICS ===
        # Total products
        total_products = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        
        # Low stock products (critical and warning levels)
        critical_stock = cur.execute('''
            SELECT COUNT(*) FROM products 
            WHERE stock_quantity = 0
        ''').fetchone()[0]
        
        low_stock = cur.execute('''
            SELECT COUNT(*) FROM products 
            WHERE stock_quantity > 0 AND stock_quantity < min_stock_level
        ''').fetchone()[0]
        
        # Near expiry items (next 7 days) from inventory batches
        near_expiry_batch_count = cur.execute('''
            SELECT COUNT(*)
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) BETWEEN date('now') AND date('now', '+7 days')
        ''').fetchone()[0]
        
        near_expiry_qty = cur.execute('''
            SELECT COALESCE(SUM(ib.qty), 0)
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) BETWEEN date('now') AND date('now', '+7 days')
        ''').fetchone()[0]
        
        # Expired items from inventory batches
        expired_batch_count = cur.execute('''
            SELECT COUNT(*)
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) < date('now')
        ''').fetchone()[0]
        
        expired_qty = cur.execute('''
            SELECT COALESCE(SUM(ib.qty), 0)
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) < date('now')
        ''').fetchone()[0]

        # Product-level expiry counts (from products table)
        near_expiry_product_count = cur.execute('''
            SELECT COUNT(*) FROM products
            WHERE expiry_date IS NOT NULL
              AND date(expiry_date) BETWEEN date('now') AND date('now', '+7 days')
        ''').fetchone()[0]

        expired_product_count = cur.execute('''
            SELECT COUNT(*) FROM products
            WHERE expiry_date IS NOT NULL
              AND date(expiry_date) < date('now')
        ''').fetchone()[0]

        # Combine batch-level and product-level counts for KPIs
        near_expiry_count = (near_expiry_batch_count or 0) + (near_expiry_product_count or 0)
        expired_count = (expired_batch_count or 0) + (expired_product_count or 0)
        
        # Sales metrics
        today_sales = cur.execute('''
            SELECT COALESCE(COUNT(*), 0), COALESCE(SUM(total), 0) 
            FROM orders 
            WHERE date(created_at) = date('now')
        ''').fetchone()
        
        yesterday_sales = cur.execute('''
            SELECT COALESCE(COUNT(*), 0), COALESCE(SUM(total), 0) 
            FROM orders 
            WHERE date(created_at) = date('now', '-1 day')
        ''').fetchone()
        
        week_sales = cur.execute('''
            SELECT COALESCE(COUNT(*), 0), COALESCE(SUM(total), 0) 
            FROM orders 
            WHERE created_at >= date('now', '-7 days')
        ''').fetchone()
        
        month_sales = cur.execute('''
            SELECT COALESCE(COUNT(*), 0), COALESCE(SUM(total), 0) 
            FROM orders 
            WHERE created_at >= date('now', '-30 days')
        ''').fetchone()
        
        # Total inventory value
        inventory_value = cur.execute('''
            SELECT COALESCE(SUM(p.price * p.stock_quantity), 0)
            FROM products p
            WHERE p.stock_quantity > 0
        ''').fetchone()[0]
        
        # === DETAILED DATA ===
        # Low stock products with details
        low_stock_products = cur.execute('''
            SELECT p.id, p.name, p.stock_quantity, p.min_stock_level, p.price, p.category
            FROM products p
            WHERE p.stock_quantity < p.min_stock_level
            ORDER BY p.stock_quantity ASC
            LIMIT 10
        ''').fetchall()
        
        # Near expiry batches with product details
        near_expiry_batch_rows = cur.execute('''
            SELECT 
                ib.id, 
                p.name as product_name, 
                p.category,
                ib.batch_no, 
                ib.expiry_date, 
                ib.qty,
                p.price,
                (p.price * ib.qty) as value
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) BETWEEN date('now') AND date('now', '+7 days')
            ORDER BY ib.expiry_date ASC
            LIMIT 15
        ''').fetchall()
        
        if near_expiry_batch_rows:
            near_expiry_batches = near_expiry_batch_rows
        else:
            product_near_expiry_rows = cur.execute('''
                SELECT 
                    p.id,
                    p.name,
                    p.category,
                    p.expiry_date,
                    COALESCE(p.stock_quantity, 0) as qty,
                    COALESCE(p.price, 0) as price,
                    COALESCE(p.price * p.stock_quantity, 0) as value
                FROM products p
                WHERE p.expiry_date IS NOT NULL
                  AND date(p.expiry_date) BETWEEN date('now') AND date('now', '+7 days')
                ORDER BY p.expiry_date ASC
                LIMIT 15
            ''').fetchall()
            
            near_expiry_batches = [
                (row[0], row[1], row[2], 'PRODUCT', row[3], row[4], row[5], row[6])
                for row in product_near_expiry_rows
            ]
        
        # Expired batches from inventory; if none, fall back to product-level expiry
        expired_batches_rows = cur.execute('''
            SELECT 
                ib.id, 
                p.name as product_name, 
                p.category,
                ib.batch_no, 
                ib.expiry_date, 
                ib.qty,
                p.price,
                (p.price * ib.qty) as value
            FROM inventory_batches ib
            JOIN products p ON ib.product_id = p.id
            WHERE ib.qty > 0 AND date(ib.expiry_date) < date('now')
            ORDER BY ib.expiry_date DESC
            LIMIT 10
        ''').fetchall()

        if expired_batches_rows:
            expired_batches = expired_batches_rows
        else:
            # Fallback: use products with expired expiry_date as pseudo-batches
            product_expired_rows = cur.execute('''
                SELECT 
                    p.id,
                    p.name,
                    p.category,
                    p.expiry_date,
                    COALESCE(p.stock_quantity, 0) as qty,
                    COALESCE(p.price, 0) as price,
                    COALESCE(p.price * p.stock_quantity, 0) as value
                FROM products p
                WHERE p.expiry_date IS NOT NULL
                  AND date(p.expiry_date) < date('now')
                ORDER BY p.expiry_date DESC
                LIMIT 10
            ''').fetchall()

            # Shape: id, product_name, category, batch_no, expiry_date, qty, price, value
            expired_batches = [
                (row[0], row[1], row[2], 'PRODUCT', row[3], row[4], row[5], row[6])
                for row in product_expired_rows
            ]
        
        # Sales trend data for TODAY only, aggregated hourly (real-time view)
        sales_trend = cur.execute('''
            SELECT 
                strftime('%Y-%m-%dT%H:00:00', created_at) as sale_hour,
                COUNT(*) as orders,
                COALESCE(SUM(total), 0) as revenue,
                COALESCE(AVG(total), 0) as avg_order_value
            FROM orders 
            WHERE date(created_at) = date('now')
            GROUP BY sale_hour
            ORDER BY sale_hour ASC
        ''').fetchall()
        
        # Top selling products
        top_products = cur.execute('''
            SELECT 
                p.name,
                p.category,
                COALESCE(SUM(oi.qty), 0) as total_sold,
                COALESCE(SUM(oi.price * oi.qty), 0) as revenue,
                p.stock_quantity
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id 
                AND o.created_at >= date('now', '-30 days')
            GROUP BY p.id, p.name, p.category, p.stock_quantity
            ORDER BY total_sold DESC
            LIMIT 10
        ''').fetchall()
        
        # Category performance
        category_performance = cur.execute('''
            SELECT 
                p.category,
                COUNT(*) as product_count,
                COALESCE(SUM(p.stock_quantity), 0) as total_stock,
                COALESCE(SUM(p.price * p.stock_quantity), 0) as stock_value,
                COALESCE(SUM(oi.qty), 0) as sold_units,
                COALESCE(SUM(oi.price * oi.qty), 0) as revenue
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id 
                AND o.created_at >= date('now', '-30 days')
            GROUP BY p.category
            ORDER BY revenue DESC
        ''').fetchall()
        
        # Recent activities
        try:
            # Prefer query that reads real order status if column exists
            recent_orders = cur.execute('''
                SELECT 
                    o.id,
                    o.customer_name,
                    o.total,
                    o.created_at,
                    o.status,
                    'order' as type,
                    COUNT(oi.product_id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.created_at >= date('now', '-7 days')
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT 5
            ''').fetchall()
        except Exception:
            # Fallback for older databases without a status column on orders
            recent_orders = cur.execute('''
                SELECT 
                    o.id,
                    o.customer_name,
                    o.total,
                    o.created_at,
                    'completed' as status,
                    'order' as type,
                    COUNT(oi.product_id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.created_at >= date('now', '-7 days')
                GROUP BY o.id
                ORDER BY o.created_at DESC
                LIMIT 5
            ''').fetchall()
        
        recent_feedback = cur.execute('''
            SELECT 
                f.id,
                f.rating,
                SUBSTR(f.text, 1, 100) as text_preview,
                f.created_at,
                'feedback' as type
            FROM feedback f
            ORDER BY f.created_at DESC
            LIMIT 3
        ''').fetchall()
        
        # Inventory health summary
        total_stock = cur.execute('''
            SELECT COALESCE(SUM(stock_quantity), 0) FROM products WHERE stock_quantity > 0
        ''').fetchone()[0]
        
        out_of_stock_products = cur.execute('''
            SELECT COUNT(*) FROM products WHERE stock_quantity = 0
        ''').fetchone()[0]
        
        overstock_products = cur.execute('''
            SELECT COUNT(*) FROM products 
            WHERE stock_quantity > (min_stock_level * 3)
        ''').fetchone()[0]

        # Store performance by product count and revenue
        store_rows = cur.execute('''
            SELECT id, name, location, manager, created_at
            FROM stores
            ORDER BY name
        ''').fetchall()

        store_performance = []
        for store in store_rows:
            store_id, name, location, manager, created_at = store

            # Total revenue per store from sales_data (all time)
            try:
                revenue = cur.execute('''
                    SELECT COALESCE(SUM(revenue), 0)
                    FROM sales_data
                    WHERE store_id = ?
                ''', (store_id,)).fetchone()[0]
            except Exception:
                revenue = 0

            # Total orders per store if column exists
            try:
                orders = cur.execute('''
                    SELECT COUNT(*)
                    FROM orders
                    WHERE store_id = ?
                ''', (store_id,)).fetchone()[0]
            except Exception:
                orders = 0

            # Number of products assigned to this store
            try:
                product_count = cur.execute('''
                    SELECT COUNT(*)
                    FROM products
                    WHERE store_id = ?
                ''', (store_id,)).fetchone()[0]
            except Exception:
                product_count = 0

            status = "active" if (orders or revenue) else "idle"

            store_performance.append({
                "id": store_id,
                "name": name,
                "location": location,
                "manager": manager,
                "revenue": float(revenue or 0),
                "orders": orders or 0,
                "status": status,
                "created_at": created_at,
                "product_count": product_count,
            })

        # Derive performance scores so we can show percentages even if only a few stores exist
        active_stores = sum(1 for s in store_performance if s.get("status") == "active")
        store_scores = []
        if store_performance:
            max_products = max((s.get("product_count") or 0) for s in store_performance) or 0
            max_orders = max((s.get("orders") or 0) for s in store_performance) or 0
            max_revenue = max((s.get("revenue") or 0) for s in store_performance) or 0.0

            for store in store_performance:
                product_ratio = ((store.get("product_count") or 0) / max_products) if max_products else 0
                orders_ratio = ((store.get("orders") or 0) / max_orders) if max_orders else 0
                revenue_ratio = ((store.get("revenue") or 0) / max_revenue) if max_revenue else 0
                score = round(((product_ratio * 0.3) + (orders_ratio * 0.3) + (revenue_ratio * 0.4)) * 100, 2)
                store["performance_percent"] = score
                store_scores.append(score)

        # Calculate performance percentage based on today's revenue
        today_revenue = today_sales[1] or 0
        if today_revenue > 100000:  # > 1 lakh
            overall_store_percent = 80
        elif today_revenue > 80000:  # > 80 thousand
            overall_store_percent = 70
        elif today_revenue > 50000:  # > 50 thousand
            overall_store_percent = 40
        else:  # <= 50 thousand
            overall_store_percent = 20
        
        # Top 5 average same as overall for revenue-based calculation
        top5_store_percent = overall_store_percent

        # Inventory health based fallback for overall system performance
        unhealthy_products = min(
            total_products,
            (critical_stock or 0) + (low_stock or 0) + (expired_product_count or 0),
        )
        healthy_products = max(total_products - unhealthy_products, 0)
        inventory_health_percent = round(
            (healthy_products / total_products) * 100, 2
        ) if total_products else 0.0

        overall_system_percent = overall_store_percent if store_scores else inventory_health_percent

        store_performance_summary = {
            "total_stores": len(store_performance),
            "active_stores": active_stores,
            "has_store_data": bool(store_performance),
            "overall_store_percent": overall_store_percent,
            "top5_store_percent": top5_store_percent,
            "overall_system_percent": overall_system_percent,
            "inventory_health_percent": inventory_health_percent,
        }

        top_store = None
        if store_performance:
            # Sort stores by performance (product_count, then revenue)
            sorted_stores = sorted(
                store_performance,
                key=lambda s: ((s.get("product_count") or 0), (s.get("revenue") or 0)),
                reverse=True,
            )

            best_store = sorted_stores[0]
            top_store = {
                "id": best_store["id"],
                "name": best_store["name"],
                "product_count": best_store.get("product_count") or 0,
                "revenue": best_store.get("revenue") or 0.0,
                "performance_percent": best_store.get("performance_percent") or 0.0,
            }

        # Get current user info if authenticated
        current_user = None
        try:
            from flask_jwt_extended import get_jwt_identity
            user_id = get_jwt_identity()
            if user_id:
                user_info = cur.execute('SELECT username, email, role FROM users WHERE id = ?', (user_id,)).fetchone()
                if user_info:
                    current_user = {
                        'username': user_info[0],
                        'email': user_info[1],
                        'role': user_info[2]
                    }
        except:
            pass

        # Explicitly close the DB context now that all queries are done
        conn_ctx.__exit__(None, None, None)

        # Format data for frontend
        dashboard_data = {
        'kpi': {
            'total_products': total_products,
            'critical_stock': critical_stock,
            'low_stock': low_stock,
            'near_expiry_count': near_expiry_count,
            'near_expiry_qty': near_expiry_qty,
            'near_expiry_batch_count': near_expiry_batch_count,
            'near_expiry_product_count': near_expiry_product_count,
            'expired_count': expired_count,
            'expired_qty': expired_qty,
            'expired_batch_count': expired_batch_count,
            'expired_product_count': expired_product_count,
            'today_orders': today_sales[0],
            'today_revenue': today_sales[1] or 0,
            'yesterday_orders': yesterday_sales[0],
            'yesterday_revenue': yesterday_sales[1] or 0,
            'week_orders': week_sales[0],
            'week_revenue': week_sales[1] or 0,
            'month_orders': month_sales[0],
            'month_revenue': month_sales[1] or 0,
            'inventory_value': inventory_value,
            'total_stock': total_stock,
            'out_of_stock': out_of_stock_products,
            'overstock': overstock_products
        },
        'low_stock_products': [
            {
                'id': p[0],
                'name': p[1],
                'current_stock': p[2],
                'min_stock': p[3],
                'price': p[4],
                'category': p[5],
                'status': 'critical' if p[2] == 0 else 'low',
                'shortage': p[3] - p[2] if p[2] < p[3] else 0
            } for p in low_stock_products
        ],
        'near_expiry_batches': [
            {
                'id': b[0],
                'product_name': b[1],
                'category': b[2],
                'batch_no': b[3],
                'expiry_date': b[4],
                'quantity': b[5],
                'price': b[6],
                'value': b[7],
                'days_until_expiry': (datetime.fromisoformat(b[4]).date() - today).days
            } for b in near_expiry_batches
        ],
        'expired_batches': [
            {
                'id': b[0],
                'product_name': b[1],
                'category': b[2],
                'batch_no': b[3],
                'expiry_date': b[4],
                'quantity': b[5],
                'price': b[6],
                'value': b[7],
                'days_expired': (today - datetime.fromisoformat(b[4]).date()).days
            } for b in expired_batches
        ],
        'sales_trend': [
            {
                'date': s[0],  # ISO-like timestamp per hour (today)
                'orders': s[1],
                'revenue': s[2],
                'avg_order_value': s[3]
            } for s in sales_trend
        ],
        'top_products': [
            {
                'name': p[0],
                'category': p[1],
                'sold_units': p[2],
                'revenue': p[3],
                'current_stock': p[4]
            } for p in top_products
        ],
        'category_performance': [
            {
                'category': c[0] or 'Uncategorized',
                'product_count': c[1],
                'total_stock': c[2],
                'stock_value': c[3],
                'sold_units': c[4],
                'revenue': c[5]
            } for c in category_performance
        ],
        'recent_activity': [
            {
                'id': o[0],
                'description': f"Order #{o[0]} by {o[1] or 'Anonymous'} ({o[6]} items)",
                'amount': o[2],
                'timestamp': o[3],
                'status': o[4],
                'type': o[5],
                'icon': 'fa-shopping-cart',
                'color': 'blue'
            } for o in recent_orders
        ] + [
            {
                'id': f[0],
                'description': f"New feedback ({f[1]}/5 stars): {f[2]}...",
                'amount': None,
                'timestamp': f[3],
                'status': None,
                'type': 'feedback',
                'icon': 'fa-comment',
                'color': 'green'
            } for f in recent_feedback
        ],
        'inventory_health': {
            'total_products': total_products,
            'in_stock': total_products - out_of_stock_products,
            'out_of_stock': out_of_stock_products,
            'low_stock': low_stock,
            'overstock': overstock_products,
            'total_stock_units': total_stock,
            'total_stock_value': inventory_value
        },
        'store_performance': store_performance,
        'store_performance_summary': store_performance_summary,
        'top_store': top_store,
        'current_user': current_user
    }
        
        return jsonify({"success": True, "data": dashboard_data, "meta": {}})
    except Exception as e:
        import traceback
        print("ERROR in /api/analytics/dashboard/realtime:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.post("/track-activity")
def track_activity():
    """Track user activities for real-time updates"""
    try:
        activity_data = request.get_json()
        
        # Store activity in notifications table for admin dashboard
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO notifications (type, title, message, data, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                activity_data.get('action', 'user_activity'),
                f"Activity: {activity_data.get('action', 'Unknown')}",
                activity_data.get('product_name', 'User activity detected'),
                str(activity_data),
                datetime.utcnow().isoformat()
            ))
            conn.commit()
        
        return jsonify({"success": True, "data": {"tracked": True}, "meta": {}})
    
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": str(e)}}), 500
