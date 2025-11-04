#!/bin/bash
# ============================================================================
# ERPNext Docker Entry Point Script
# ============================================================================

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting ERPNext Kanaan ERP Application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for Database to be ready
echo "⏳ Waiting for database to be ready..."
while ! mysqladmin ping -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" --silent; do
    echo "📦 Database is unavailable - sleeping..."
    sleep 2
done
echo "✅ Database is ready!"

# Wait for Redis Cache to be ready
echo "⏳ Waiting for Redis Cache to be ready..."
while ! redis-cli -h "$REDIS_CACHE" ping > /dev/null 2>&1; do
    echo "📦 Redis Cache is unavailable - sleeping..."
    sleep 2
done
echo "✅ Redis Cache is ready!"

# Wait for Redis Queue to be ready
echo "⏳ Waiting for Redis Queue to be ready..."
while ! redis-cli -h $(echo "$REDIS_QUEUE" | cut -d: -f1) -p $(echo "$REDIS_QUEUE" | cut -d: -f2) ping > /dev/null 2>&1; do
    echo "📦 Redis Queue is unavailable - sleeping..."
    sleep 2
done
echo "✅ Redis Queue is ready!"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Application Configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📍 Site Name: $SITE_NAME"
echo "  🗄️  Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo "  💾 Redis Cache: $REDIS_CACHE"
echo "  ⚡ Redis Queue: $REDIS_QUEUE"
echo "  🏗️  Environment: $FRAPPE_ENV"
echo ""

# Install/Update Python Dependencies if needed
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install --no-cache-dir -r requirements.txt || echo "⚠️  Some dependencies may have failed"
fi

# Install/Update Node Dependencies if needed
echo "📦 Installing Node dependencies..."
npm ci --omit=dev 2>/dev/null || echo "⚠️  Node install may have failed"

# Create required directories
echo "📁 Creating required directories..."
mkdir -p sites/$SITE_NAME
mkdir -p private/files
mkdir -p logs
mkdir -p public/files

# Create site configuration if it doesn't exist
if [ ! -f "sites/$SITE_NAME/site_config.json" ]; then
    echo "⚙️  Creating site configuration..."
    cat > sites/$SITE_NAME/site_config.json <<EOF
{
  "domain": "$SITE_NAME",
  "db_name": "$DB_NAME",
  "db_type": "mariadb",
  "db_host": "$DB_HOST",
  "db_port": $DB_PORT,
  "cache_servers": ["$REDIS_CACHE"],
  "redis_cache": "$REDIS_CACHE",
  "redis_queue": "$REDIS_QUEUE",
  "encryption_key": "$ENCRYPTION_KEY"
}
EOF
fi

# Build Frontend Assets if Frappe
echo "🎨 Building frontend assets..."
npm run build 2>/dev/null || echo "⚠️  Frontend build skipped"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete! Starting application..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Execute the command
exec "$@"