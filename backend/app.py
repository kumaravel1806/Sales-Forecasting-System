import os
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from db import init_db


def create_app():
    app = Flask(__name__)

    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "dev_secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600")))
    app.config["JWT_ALGORITHM"] = "HS256"

    CORS(app, resources={r"/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*")}})
    JWTManager(app)
    init_db()

    # Blueprints
    from blueprints.auth.routes import bp as auth_bp
    from blueprints.products.routes import bp as products_bp
    from blueprints.orders.routes import bp as orders_bp
    from blueprints.analytics.routes import bp as analytics_bp
    from blueprints.analytics.realtime_routes import bp as realtime_analytics_bp
    from blueprints.ml.routes import bp as ml_bp
    from blueprints.admin.routes import bp as admin_bp
    from blueprints.inventory.routes import bp as inventory_bp
    from blueprints.reviews.routes import bp as reviews_bp
    from blueprints.qa.routes import bp as qa_bp
    from blueprints.assistant.routes import bp as assistant_bp
    from blueprints.admin_users.routes import bp as admin_users_bp
    from blueprints.feedback.routes import bp as feedback_bp
    from blueprints.connectors.routes import bp as connectors_bp
    from flask import send_from_directory
    from datetime import datetime
    try:
        from db import get_conn
    except Exception:
        from backend.db import get_conn
    try:
        from utils.auth import hash_password
    except Exception:
        from backend.utils.auth import hash_password

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(realtime_analytics_bp, url_prefix="/api/analytics/realtime")
    app.register_blueprint(ml_bp, url_prefix="/api/ml")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    app.register_blueprint(reviews_bp, url_prefix="/api/reviews")
    app.register_blueprint(qa_bp, url_prefix="/api/qa")
    app.register_blueprint(assistant_bp, url_prefix="/api/assistant")
    app.register_blueprint(admin_users_bp, url_prefix="/api/admin/users")
    app.register_blueprint(feedback_bp, url_prefix="/api/feedback")
    app.register_blueprint(connectors_bp, url_prefix="/api/connectors")

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "data": {"status": "ok"}, "meta": {"service": "api"}})

    @app.get("/api/metrics")
    def metrics():
        # Placeholder Prometheus metrics exposition format
        return (
            "# HELP app_info Application info\n"
            "# TYPE app_info gauge\n"
            "app_info{service=\"api\",version=\"0.1.0\"} 1\n",
            200,
            {"Content-Type": "text/plain; version=0.0.4"},
        )

    @app.get("/api/routes")
    def list_routes():
        import re
        routes = []
        for rule in app.url_map.iter_rules():
            if re.match(r"^/(static|favicon)", str(rule)):
                continue
            routes.append({
                "endpoint": rule.endpoint,
                "methods": sorted([m for m in rule.methods if m not in ("HEAD", "OPTIONS")]),
                "rule": str(rule)
            })
        routes = sorted(routes, key=lambda r: r["rule"])  # stable order
        return jsonify({"success": True, "data": routes, "meta": {}})

    @app.get("/api/dashboard-simple")
    def dashboard_simple():
        """Simple dashboard endpoint for testing"""
        print("DEBUG: Simple dashboard called!")
        with get_conn() as conn:
            cur = conn.cursor()
            total_products = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
            print(f"DEBUG: Total products: {total_products}")
        
        return jsonify({
            "success": True, 
            "data": {
                "total_products": total_products,
                "low_stock": 0,
                "near_expiry": 0,
                "expired": 0
            }, 
            "meta": {}
        })

    @app.get("/api/analytics/dashboard")
    def dashboard():
        """Get dashboard metrics for low stock, near expiry, and expired items"""
        print("DEBUG: Dashboard endpoint called!")
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        
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
            near_expiry = cur.execute('''
                SELECT COUNT(*) FROM inventory_batches 
                WHERE qty > 0 AND date(expiry_date) BETWEEN date('now') AND date('now', '+7 days')
            ''').fetchone()[0]
            
            # Expired: count unique batches that have expired
            expired = cur.execute('''
                SELECT COUNT(*) FROM inventory_batches 
                WHERE qty > 0 AND date(expiry_date) < date('now')
            ''').fetchone()[0]
            
            # Get total orders and revenue
            orders_data = cur.execute('SELECT COUNT(*), COALESCE(SUM(total), 0) FROM orders WHERE created_at >= ?', 
                                    (today - timedelta(days=30),)).fetchone()
            total_orders = orders_data[0] or 0
            total_revenue = orders_data[1] or 0
        
        metrics = {
            "low_stock": low_stock,
            "critical_stock": critical_stock,
            "near_expiry": near_expiry,
            "expired": expired,
            "total_products": total_products,
            "total_revenue": total_revenue,
            "total_orders": total_orders
        }
        print(f"DEBUG: Returning metrics: {metrics}")
        return jsonify({"success": True, "data": metrics, "meta": {"window_days": 7}})

    # Seed default admin; fall back to admin@example.com / password if env not set
    admin_email = (os.getenv('ADMIN_EMAIL') or 'admin@example.com').strip().lower()
    admin_pwd = os.getenv('ADMIN_PASSWORD') or 'password'
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            row = cur.execute('SELECT id FROM users WHERE email=?', (admin_email,)).fetchone()
            if not row:
                cur.execute('INSERT INTO users(email, username, password_hash, role, created_at) VALUES(?,?,?,?,?)',
                            (admin_email, None, hash_password(admin_pwd), 'admin', datetime.utcnow().isoformat()))
                conn.commit()
    except Exception:
        pass

    # Serve frontend files from ../frontend so a single port (8000) serves UI+API
    FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

    @app.get('/')
    def root_index():
        from flask import redirect
        return redirect('/login.html')

    @app.get('/<path:path>')
    def static_proxy(path: str):
        # Only serve files that exist; otherwise fall back to 404
        fpath = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(fpath):
            return send_from_directory(FRONTEND_DIR, path)
        # If requesting a known html page without extension, try adding .html
        if not os.path.splitext(path)[1] and os.path.isfile(fpath + '.html'):
            return send_from_directory(FRONTEND_DIR, path + '.html')
        return ("Not Found", 404)

    return app

if __name__ == "__main__":
    app = create_app()
    print("Starting Retail Forecasting Website...")
    print("Open: http://localhost:8000/")
    print("Admin: admin@example.com / password")
    app.run(host="0.0.0.0", port=8000, debug=False)
