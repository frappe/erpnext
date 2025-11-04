"""
Gunicorn Configuration for ERPNext/Frappe
"""

import multiprocessing
import os

# ============================================================================
# Server Settings
# ============================================================================
bind = ["0.0.0.0:8000"]
backlog = 2048
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# ============================================================================
# Logging
# ============================================================================
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ============================================================================
# Process Settings
# ============================================================================
daemon = False
pidfile = None
umask = 0o022
user = None
group = None
tmp_upload_dir = "/tmp"

# ============================================================================
# Server Mechanics
# ============================================================================
preload_app = True
reload = os.environ.get("GUNICORN_RELOAD", "false").lower() == "true"
reload_extra_files = []
check_config = False

# ============================================================================
# SSL (if needed)
# ============================================================================
keyfile = None
certfile = None
ssl_version = "TLSv1_2"
cert_reqs = 0
ca_certs = None
suppress_ragged_eof = True

# ============================================================================
# Security
# ============================================================================
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# ============================================================================
# Application
# ============================================================================
paste = None
env = {}
raw_env = []
forwarded_allow_ips = "*"
secure_scheme_headers = {
    "X-FORWARDED-PROTOCOL": "ssl",
    "X-FORWARDED-PROTO": "https",
    "X-FORWARDED-SSL": "on",
}

# ============================================================================
# Server Hooks
# ============================================================================
def on_starting(server):
    print("[Gunicorn] Starting server...")

def when_ready(server):
    print("[Gunicorn] Server is ready. Spawning workers...")

def on_exit(server):
    print("[Gunicorn] Exiting...")