"""
WSGI Configuration for Frappe Framework on Railway
"""

import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


os.environ.setdefault("FRAPPE_ENV", os.getenv("FRAPPE_ENV", "production"))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


try:
    import frappe
    from frappe.app import application as frappe_app

    print("✅ Frappe application loaded successfully")
    print(f"   Environment: {os.getenv('FRAPPE_ENV')}")
    print(f"   Site Name: {os.getenv('SITE_NAME', 'site1.local')}")

    application = frappe_app

except Exception as e:
    print("❌ Failed to load Frappe:", e)

    def application(environ, start_response):
        status = "500 Internal Server Error"
        headers = [("Content-Type", "text/html")]
        start_response(status, headers)
        return [b"<h1>Error loading Frappe application</h1>"]


if hasattr(application, "__call__"):
    original_app = application

    def app_with_health(environ, start_response):
        path = environ.get("PATH_INFO", "").lower()

        if path in ("/health", "/healthz", "/api/health"):
            status = "200 OK"
            response = b'{"status":"healthy"}'
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response))),
            ]
            start_response(status, headers)
            return [response]

        return original_app(environ, start_response)

    application = app_with_health


if __name__ == "__main__":
    print("This is a WSGI entrypoint. Use Gunicorn to run it:")
    print("  gunicorn --config gunicorn.conf.py wsgi:application")
