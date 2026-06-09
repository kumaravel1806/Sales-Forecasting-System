from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from db import get_conn
from .predictive import SalesPredictor
import json

bp = Blueprint("realtime_analytics", __name__)
predictor = SalesPredictor()

@bp.get("/dashboard/simple")
def simple_dashboard():
    """Get simple dashboard data without complex predictions"""
    try:
        metrics = _get_current_performance()
        sales_trend = _get_sales_trend_today()
        recent_activity = _get_recent_activity()
        top_products = _get_top_products()
        store_performance, top_store = _get_store_performance()
        
        return jsonify({
            "success": True,
            "data": {
                "current_metrics": metrics,
                "sales_trend": sales_trend,
                "recent_activity": recent_activity,
                "top_products": top_products,
                "store_performance": store_performance,
                "top_store": top_store
            },
            "meta": {
                "type": "simple_dashboard",
                "timestamp": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        print(f"Simple dashboard error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "data": None
        }), 500

@bp.get("/predictive/dashboard")
def predictive_dashboard():
    """Get comprehensive real-time predictive analytics dashboard"""
    try:
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
        return jsonify({
            "success": False,
            "error": str(e),
            "data": None
        }), 500

@bp.get("/sales/forecast")
def sales_forecast():
    """Get detailed sales forecast"""
    try:
        days = request.args.get('days', 30, type=int)
        predictions = predictor.predict_future_sales(days)
        
        # Calculate forecast summary
        total_predicted_orders = sum(p['predicted_orders'] for p in predictions)
        total_predicted_revenue = sum(p['predicted_revenue'] for p in predictions)
        avg_confidence = sum(p['confidence'] for p in predictions) / len(predictions) if predictions else 0
        
        return jsonify({
            "success": True,
            "data": {
                "forecast": predictions,
                "summary": {
                    "total_predicted_orders": total_predicted_orders,
                    "total_predicted_revenue": total_predicted_revenue,
                    "average_confidence": round(avg_confidence, 2),
                    "forecast_period_days": days
                }
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.get("/inventory/health")
def inventory_health():
    """Get real-time inventory health analytics"""
    try:
        health_data = predictor.get_inventory_health_metrics()
        
        # Calculate health score
        total_value = health_data['total_inventory_value']
        at_risk_value = 0
        
        if 'expiry_analytics' in health_data:
            for status, data in health_data['expiry_analytics'].items():
                if status in ['expired', 'expiring_soon']:
                    at_risk_value += data.get('value', 0)
        
        health_score = max(0, 100 - (at_risk_value / total_value * 100)) if total_value > 0 else 100
        
        return jsonify({
            "success": True,
            "data": {
                **health_data,
                "health_score": round(health_score, 1),
                "at_risk_percentage": round((at_risk_value / total_value * 100) if total_value > 0 else 0, 1)
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.get("/alerts/live")
def live_alerts():
    """Get real-time alerts"""
    try:
        alerts = predictor.get_real_time_alerts()
        
        # Categorize alerts
        alert_summary = {
            "critical": len([a for a in alerts if a['severity'] == 'high']),
            "warning": len([a for a in alerts if a['severity'] == 'medium']),
            "total": len(alerts)
        }
        
        return jsonify({
            "success": True,
            "data": {
                "alerts": alerts[:20],  # Limit to last 20 alerts
                "summary": alert_summary,
                "last_updated": datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.get("/trends/analysis")
def trends_analysis():
    """Get comprehensive trend analysis"""
    try:
        trend_data = _analyze_trends()
        
        return jsonify({
            "success": True,
            "data": trend_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@bp.get("/performance/realtime")
def realtime_performance():
    """Get real-time performance metrics"""
    try:
        metrics = _get_current_performance()
        
        return jsonify({
            "success": True,
            "data": metrics,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def _get_sales_trend_today():
    """Get hourly sales trend for the last 7 days to ensure data is always visible"""
    with get_conn() as conn:
        cur = conn.cursor()
        seven_days_ago = datetime.now().date() - timedelta(days=7)
        rows = cur.execute('''
            SELECT strftime('%Y-%m-%d %H', created_at) as hour_bucket, COUNT(*) as orders, COALESCE(SUM(total),0) as revenue
            FROM orders
            WHERE DATE(created_at) >= ?
            GROUP BY hour_bucket
            ORDER BY hour_bucket DESC
            LIMIT 48
        ''', (seven_days_ago,)).fetchall()
        return [{"hour": r[0], "orders": r[1], "revenue": r[2], "date": r[0]} for r in rows]

def _get_recent_activity():
    """Get recent activity including orders and feedback from the last 7 days"""
    with get_conn() as conn:
        cur = conn.cursor()
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        # Recent orders - simple query without status complications
        orders = cur.execute('''
            SELECT id, customer_name, total, created_at, 'order' as type
            FROM orders
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT 5
        ''', (seven_days_ago,)).fetchall()
        
        # Recent feedback
        feedback = cur.execute('''
            SELECT id, user_id, rating, text, created_at, admin_reply, 'feedback' as type
            FROM feedback
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT 5
        ''', (seven_days_ago,)).fetchall()
        
        activity = []
        
        # Process orders
        for o in orders:
            activity.append({
                "id": o[0], 
                "customer_name": o[1], 
                "total": o[2], 
                "timestamp": o[3], 
                "type": o[4],
                "action": "purchase"
            })
        
        # Process feedback
        for f in feedback:
            responded = "responded" if f[5] and f[5].strip() else "not_responded"
            activity.append({
                "id": f[0], 
                "customer_name": f"User {f[1]}", 
                "rating": f[2], 
                "comment": f[3], 
                "timestamp": f[4], 
                "status": responded,
                "type": f[6],
                "action": "feedback"
            })
        
        # Add some mock product views for demonstration
        import random
        products = cur.execute('SELECT id, name FROM products ORDER BY id LIMIT 3').fetchall()
        for i, p in enumerate(products):
            activity.append({
                "id": p[0],
                "product_name": p[1],
                "timestamp": (datetime.now() - timedelta(hours=i+1)).isoformat(),
                "type": "view",
                "action": "view",
                "view_count": random.randint(1, 10)
            })
        
        activity.sort(key=lambda x: x["timestamp"], reverse=True)
        return activity[:10]

def _get_top_products():
    """Get top products by quantity sold (all time)"""
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('''
            SELECT p.id, p.name, COALESCE(SUM(oi.qty),0) as total_qty, COALESCE(SUM(oi.qty * oi.price),0) as revenue
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            GROUP BY p.id, p.name
            ORDER BY total_qty DESC, p.name
            LIMIT 5
        ''').fetchall()
        # If no sales, still return products with zero qty
        if not rows or all(r[2] == 0 for r in rows):
            rows = cur.execute('''
                SELECT id, name, 0, 0.0
                FROM products
                ORDER BY name
                LIMIT 5
            ''').fetchall()
        return [{"product_id": r[0], "name": r[1], "quantity": r[2], "revenue": r[3]} for r in rows]

def _get_store_performance():
    """Store performance using all-time data to ensure metrics are always visible"""
    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute('''
            SELECT COUNT(*) as orders, COALESCE(SUM(total),0) as revenue
            FROM orders
        ''').fetchone()
        perf = [{"store_name": "Main Store", "orders": row[0], "revenue": row[1]}]
        top_store = {"name": "Main Store", "orders": row[0], "revenue": row[1]} if row and row[0] > 0 else {"name": "Main Store", "orders": 0, "revenue": 0.0}
        return perf, top_store

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
        
        # Get detailed inventory alerts
        expired_products = cur.execute('''
            SELECT id, name, expiry_date, stock_quantity
            FROM products 
            WHERE expiry_date IS NOT NULL AND date(expiry_date) < date('now')
            ORDER BY expiry_date ASC
            LIMIT 10
        ''').fetchall()
        
        near_expiry_products = cur.execute('''
            SELECT id, name, expiry_date, stock_quantity
            FROM products 
            WHERE expiry_date IS NOT NULL 
            AND date(expiry_date) BETWEEN date('now') AND date('now', '+7 days')
            ORDER BY expiry_date ASC
            LIMIT 10
        ''').fetchall()
        
        low_stock_products = cur.execute('''
            SELECT id, name, stock_quantity, min_stock_level
            FROM products 
            WHERE stock_quantity > 0 AND stock_quantity < min_stock_level
            ORDER BY stock_quantity ASC
            LIMIT 10
        ''').fetchall()
        
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
                "total_value": inventory_data[3] or 0,
                "alerts": {
                    "expired_products": {
                        "count": len(expired_products),
                        "items": [{"id": p[0], "name": p[1], "expiry_date": p[2], "stock": p[3]} for p in expired_products]
                    },
                    "near_expiry_products": {
                        "count": len(near_expiry_products),
                        "items": [{"id": p[0], "name": p[1], "expiry_date": p[2], "stock": p[3]} for p in near_expiry_products]
                    },
                    "low_stock_products": {
                        "count": len(low_stock_products),
                        "items": [{"id": p[0], "name": p[1], "stock": p[2], "min_stock": p[3]} for p in low_stock_products]
                    }
                }
            }
        }

def _analyze_trends():
    """Analyze business trends"""
    try:
        df = predictor.get_historical_sales_data(30)
        
        if len(df) < 7:
            return {"trend": "insufficient_data", "insights": []}
        
        # Calculate trends
        recent_week = df.tail(7)
        previous_week = df.iloc[-14:-7] if len(df) >= 14 else df.head(min(7, len(df)-7))
        
        orders_trend = ((recent_week['orders'].mean() - previous_week['orders'].mean()) / previous_week['orders'].mean() * 100) if previous_week['orders'].mean() > 0 else 0
        revenue_trend = ((recent_week['revenue'].mean() - previous_week['revenue'].mean()) / previous_week['revenue'].mean() * 100) if previous_week['revenue'].mean() > 0 else 0
        
        # Generate insights
        insights = []
        
        if orders_trend > 10:
            insights.append({"type": "positive", "message": f"Orders increased by {orders_trend:.1f}% this week"})
        elif orders_trend < -10:
            insights.append({"type": "negative", "message": f"Orders decreased by {abs(orders_trend):.1f}% this week"})
        
        if revenue_trend > 15:
            insights.append({"type": "positive", "message": f"Revenue grew by {revenue_trend:.1f}% this week"})
        elif revenue_trend < -15:
            insights.append({"type": "negative", "message": f"Revenue declined by {abs(revenue_trend):.1f}% this week"})
        
        # Day of week analysis
        dow_performance = df.groupby(df['date'].dt.day_name())['orders'].mean().sort_values(ascending=False)
        best_day = dow_performance.index[0] if len(dow_performance) > 0 else "Monday"
        
        insights.append({"type": "info", "message": f"Best performing day: {best_day}"})
        
        return {
            "trend": "increasing" if orders_trend > 5 else "decreasing" if orders_trend < -5 else "stable",
            "orders_trend_percent": round(orders_trend, 1),
            "revenue_trend_percent": round(revenue_trend, 1),
            "insights": insights,
            "best_day": best_day
        }
        
    except Exception as e:
        print(f"Trend analysis error: {e}")
        return {"trend": "error", "insights": []}
