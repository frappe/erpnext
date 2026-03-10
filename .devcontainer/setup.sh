#!/bin/bash
set -e

echo "=== ZirakERP Codespace Setup ==="

# Build and start
cd /workspaces/zirakerp
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d

echo ""
echo "=== ZirakERP is starting! ==="
echo "Wait 2-3 minutes for the site to initialize."
echo "Check progress: docker compose -f docker/docker-compose.yml logs create-site -f"
echo "Login: Administrator / admin"
