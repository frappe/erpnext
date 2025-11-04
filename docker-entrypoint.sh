#!/bin/bash
# ============================================================================
# ERPNext Docker Entry Point Script
# ============================================================================

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting ERPNext Kanaan ERP Application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ============================================================================
# CONFIGURATION
# ============================================================================
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-root}"
DB_NAME="${DB_NAME:-erpnext}"
REDIS_CACHE="${REDIS_CACHE:-localhost:6379}"
REDIS_QUEUE="${REDIS_QUEUE:-localhost:6380}"
SITE_NAME="${SITE_NAME:-localhost}"

echo ""
echo "📝 Configuration:"
echo "  🗄️  Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  💾 Redis Cache: $REDIS_CACHE"
echo "  ⚡ Redis Queue: $REDIS_QUEUE"
echo "  📍 Site Name: $SITE_NAME"
echo ""

# ============================================================================
# HEALTH CHECKS
# ============================================================================

# Wait for Database
echo "⏳ Waiting for MariaDB to be ready..."
MAX_RETRIES=30
RETRY=0
while ! mysqladmin ping -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" --silent 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "❌ Database failed to start after $MAX_RETRIES attempts"
        echo "   Make sure DB_HOST, DB_USER, DB_PASSWORD are set correctly"
        exit 1
    fi
    echo "   ⏳ Database is unavailable - sleeping... ($RETRY/$MAX_RETRIES)"
    sleep 2
done
echo "✅ Database is ready!"

# Wait for Redis Cache
echo "⏳ Waiting for Redis Cache to be ready..."
REDIS_HOST=$(echo "$REDIS_CACHE" | cut -d: -f1)
REDIS_PORT=$(echo "$REDIS_CACHE" | cut -d: -f2)
RETRY=0
while ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "❌ Redis Cache failed to start after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "   ⏳ Redis Cache is unavailable - sleeping... ($RETRY/$MAX_RETRIES)"
    sleep 2
done
echo "✅ Redis Cache is ready!"

# Wait for Redis Queue
echo "⏳ Waiting for Redis Queue to be ready..."
REDIS_QUEUE_HOST=$(echo "$REDIS_QUEUE" | cut -d: -f1)
REDIS_QUEUE_PORT=$(echo "$REDIS_QUEUE" | cut -d: -f2)
RETRY=0
while ! redis-cli -h "$REDIS_QUEUE_HOST" -p "$REDIS_QUEUE_PORT" ping > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "❌ Redis Queue failed to start after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "   ⏳ Redis Queue is unavailable - sleeping... ($RETRY/$MAX_RETRIES)"
    sleep 2
done
echo "✅ Redis Queue is ready!"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All dependencies are ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================================
echo "📁 Ensuring required directories exist..."
mkdir -p /app/sites/"$SITE_NAME"
mkdir -p /app/private/files
mkdir -p /app/logs
mkdir -p /app/public/files
chmod -R 755 /app/sites

# ============================================================================
# SITE CONFIGURATION
# ============================================================================
echo "⚙️  Setting up site configuration..."

if [ ! -f "/app/sites/$SITE_NAME/site_config.json" ]; then
    echo "   📝 Creating new site_config.json..."
    mkdir -p "/app/sites/$SITE_NAME"
    cat > "/app/sites/$SITE_NAME/site_config.json" <<EOF
{
  "db_type": "MariaDB",
  "db_name": "$DB_NAME",
  "db_host": "$DB_HOST",
  "db_port": $DB_PORT,
  "db_user": "$DB_USER",
  "redis_cache": "$REDIS_CACHE",
  "redis_queue": "$REDIS_QUEUE",
  "allow_on_submit": [],
  "encryption_key": "${ENCRYPTION_KEY:-}"
}
EOF
    echo "   ✅ site_config.json created"
else
    echo "   ✅ site_config.json already exists"
fi

# ============================================================================
# VALIDATE APPLICATION
# ============================================================================
echo ""
echo "🔍 Validating application..."

# Check if wsgi.py exists
if [ ! -f /app/wsgi.py ]; then
    echo "❌ ERROR: wsgi.py not found in /app"
    exit 1
fi
echo "   ✅ wsgi.py found"

# Check if gunicorn is installed
if ! python -c "import gunicorn" 2>/dev/null; then
    echo "❌ ERROR: gunicorn is not installed"
    exit 1
fi
echo "   ✅ gunicorn is installed"

# Check if frappe can be imported
echo "🔍 Checking if Frappe can be imported..."
if python -c "import frappe; print(f'   Frappe version: {frappe.__version__}')" 2>/dev/null; then
    echo "   ✅ Frappe framework found"
    if python -c "from frappe.app import application" 2>/dev/null; then
        echo "   ✅ Frappe WSGI application can be imported"
    else
        echo "   ⚠️  WARNING: Frappe app module cannot be imported (may initialize on first request)"
    fi
else
    echo "   ⚠️  WARNING: Frappe framework not found in Python path"
    echo "   This may cause issues. Continuing anyway..."
fi

# ============================================================================
# START APPLICATION
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Gunicorn Server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   📍 Host: 0.0.0.0"
echo "   🔌 Port: 8000"
echo "   👥 Workers: $(grep -c '^processor' /proc/cpuinfo || echo 2)"
echo "   📄 WSGI: wsgi:application"
echo ""
echo "✅ Ready to receive requests!"
echo ""

# Execute the main command (gunicorn)
exec "$@"
