import traceback

from app import create_app
from blueprints.analytics.routes import dashboard_realtime
from flask import Response


def main():
    app = create_app()
    app.testing = True

    print("[DEBUG] Created app, calling dashboard_realtime() inside test request context...")

    try:
        with app.test_request_context("/api/analytics/dashboard/realtime"):
            rv = dashboard_realtime()
            print("[DEBUG] Call returned without raising.")
            print("[DEBUG] Return type:", type(rv))

            if isinstance(rv, Response):
                print("[DEBUG] Response status:", rv.status_code)
                body = rv.get_data(as_text=True)
                print("[DEBUG] Response body (first 2000 chars):\n", body[:2000])
            else:
                # Could be (response, status) tuple etc.
                print("[DEBUG] Raw return value:", rv)
    except Exception as e:
        print("[ERROR] Exception while executing dashboard_realtime():", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
