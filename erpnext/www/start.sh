#!/usr/bin/env bash
set -e

cd frappe-bench

# نحصل على المنفذ من Render
PORT=${PORT:-10000}

echo "🚀 Starting ERPNext web server on port $PORT ..."
bench set-nginx-port $PORT

# نبدأ الخدمة باستخدام Gunicorn
bench serve --port $PORT
