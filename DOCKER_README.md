# ERPNext Docker Setup

This directory contains Docker configuration files to run ERPSubaga (ERPNext fork) using Docker and Docker Compose.

## 📋 Prerequisites

- Docker Engine 20.10 or higher
- Docker Compose 2.0 or higher
- Minimum 4GB RAM available for Docker
- Minimum 20GB disk space

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd erpnext-subaga
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your preferred settings
nano .env
```

**Important**: Change the default passwords in `.env` file before running in production!

### 3. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f erpnext-backend
```

### 4. Access ERPNext

For local development, add this line to your `/etc/hosts` file:
```
127.0.0.1 erp.localhost
```

Then access ERPNext at:
- **URL**: http://erp.localhost:8000
- **Username**: Administrator
- **Password**: (the one you set in `.env` as `ADMIN_PASSWORD`, default: `admin`)

## 📦 Services Overview

The Docker Compose setup includes the following services:

| Service | Description | Port |
|---------|-------------|------|
| `mariadb` | MariaDB 10.6 database | 3306 (internal) |
| `redis-cache` | Redis for caching | 6379 (internal) |
| `redis-queue` | Redis for background jobs | 6379 (internal) |
| `redis-socketio` | Redis for real-time updates | 6379 (internal) |
| `erpnext-backend` | Main ERPNext web application | 8000, 9000 |
| `erpnext-worker-long` | Worker for long-running tasks | - |
| `erpnext-worker-short` | Worker for short-running tasks | - |
| `erpnext-worker-default` | Worker for default queue | - |
| `erpnext-scheduler` | Scheduler for cron jobs | - |
| `nginx` | Nginx reverse proxy (production) | 80, 443 |

## 🔧 Common Operations

### Start Services

```bash
docker-compose up -d
```

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f erpnext-backend
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart erpnext-backend
```

### Execute Commands in Container

```bash
# Access bench console
docker-compose exec erpnext-backend bench --site erp.localhost console

# Run migrations
docker-compose exec erpnext-backend bench --site erp.localhost migrate

# Clear cache
docker-compose exec erpnext-backend bench --site erp.localhost clear-cache

# Rebuild assets
docker-compose exec erpnext-backend bench --site erp.localhost build
```

### Backup and Restore

#### Create Backup

```bash
# Backup with files
docker-compose exec erpnext-backend bench --site erp.localhost backup --with-files

# Backups are stored in: sites/erp.localhost/private/backups/
```

#### Restore Backup

```bash
# Copy backup files to container if needed
docker cp backup.sql erpnext_backend:/tmp/

# Restore
docker-compose exec erpnext-backend bench --site erp.localhost restore \
  --with-public-files /path/to/public.tar \
  --with-private-files /path/to/private.tar \
  /path/to/database.sql
```

### Database Access

```bash
# Access MariaDB
docker-compose exec mariadb mysql -u root -p

# Export database
docker-compose exec mariadb mysqldump -u root -p erpnext > backup.sql
```

## 🔐 Security Considerations

### For Production Deployment:

1. **Change Default Passwords**: Update all passwords in `.env` file
2. **Use HTTPS**: Configure SSL certificates for Nginx
3. **Firewall Rules**: Restrict access to database and Redis ports
4. **Regular Backups**: Set up automated backup schedule
5. **Update Regularly**: Keep Docker images and application updated
6. **Secure Site Name**: Use your actual domain instead of `erp.localhost`

### Recommended .env values for production:

```bash
SITE_NAME=your-domain.com
ADMIN_PASSWORD=<strong-random-password>
DB_ROOT_PASSWORD=<strong-random-password>
DB_PASSWORD=<strong-random-password>
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check service status
docker-compose ps

# Check logs for errors
docker-compose logs erpnext-backend

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Issues

```bash
# Check if MariaDB is running
docker-compose ps mariadb

# Check MariaDB logs
docker-compose logs mariadb

# Test connection
docker-compose exec mariadb mysqladmin ping -h localhost -u root -p
```

### Site Not Found Error

```bash
# List all sites
docker-compose exec erpnext-backend ls sites/

# Create new site manually
docker-compose exec erpnext-backend bench new-site your-site-name \
  --mariadb-root-password your-db-root-password \
  --admin-password your-admin-password
```

### Performance Issues

1. **Increase Memory**: Adjust Docker Desktop memory allocation (recommended: 4GB+)
2. **Clear Cache**: Run `bench clear-cache`
3. **Rebuild Assets**: Run `bench build`
4. **Check Worker Status**: Ensure all worker containers are running

### Permission Issues

```bash
# Fix permissions (run from host)
docker-compose exec erpnext-backend sudo chown -R frappe:frappe /home/frappe/frappe-bench/sites
```

## 🏗️ Development Setup

For development with live code reloading:

1. Mount your code as a volume in `docker-compose.yml`:

```yaml
volumes:
  - ./erpnext:/home/frappe/frappe-bench/apps/erpnext
  - sites_data:/home/frappe/frappe-bench/sites
```

2. Enable developer mode:

```bash
docker-compose exec erpnext-backend bench --site erp.localhost set-config developer_mode 1
docker-compose exec erpnext-backend bench --site erp.localhost clear-cache
```

3. Restart services:

```bash
docker-compose restart
```

## 📊 Monitoring

### Resource Usage

```bash
# Check container resource usage
docker stats

# Check specific container
docker stats erpnext_backend
```

### Health Checks

```bash
# Check service health
docker-compose ps

# Manual health check
curl http://localhost:8000/api/method/ping
```

## 🔄 Updates

### Update ERPNext Application

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose build --no-cache erpnext-backend

# Restart services
docker-compose down
docker-compose up -d

# Run migrations
docker-compose exec erpnext-backend bench --site erp.localhost migrate
```

## 🗂️ Volume Management

### List Volumes

```bash
docker volume ls | grep erpnext
```

### Backup Volumes

```bash
# Backup sites data
docker run --rm \
  -v erpnext-subaga_sites_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/sites-backup.tar.gz -C /data .
```

### Remove Volumes (Caution: Data Loss!)

```bash
# Stop services first
docker-compose down

# Remove volumes
docker-compose down -v
```

## 📚 Additional Resources

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [ERPNext Documentation](https://docs.erpnext.com)
- [Frappe Bench Commands](https://frappeframework.com/docs/user/en/bench)
- [Docker Documentation](https://docs.docker.com)

## 🆘 Support

For issues related to:
- **Docker Setup**: Check this README and troubleshooting section
- **ERPNext Application**: Visit [ERPNext Forum](https://discuss.erpnext.com)
- **Frappe Framework**: Visit [Frappe Forum](https://discuss.frappe.io)

## 📝 License

This Docker setup is provided as-is. ERPNext is licensed under GNU GPL v3.
