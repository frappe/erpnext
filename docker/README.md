# ZirakERP - Local Docker Setup

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- At least **4 GB RAM** allocated to Docker

## Quick Start

Open a terminal, navigate to this folder, and run:

```bash
cd path/to/ZirakERP/docker
docker compose up -d
```

The first run takes **3-5 minutes** as it:
1. Pulls all required images (MariaDB, Redis, ZirakERP)
2. Starts the database and Redis
3. Configures the bench
4. Creates your first site with ZirakERP installed

## Access the ERP

Once all services are running, open your browser:

- **URL:** http://localhost:8080
- **Username:** `Administrator`
- **Password:** `admin`

## Useful Commands

```bash
# Check status of all services
docker compose ps

# View logs (follow mode)
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend

# Stop everything (data is preserved)
docker compose down

# Stop and DELETE all data (fresh start)
docker compose down -v

# Restart everything
docker compose restart
```

## Troubleshooting

### Site not loading?
The `create-site` service may still be running. Check with:
```bash
docker compose logs -f create-site
```
Wait until you see the site creation complete.

### Port 8080 already in use?
Edit the `.env` file and change `HTTP_PORT` to another port (e.g., 9090).

### Reset everything?
```bash
docker compose down -v
docker compose up -d
```
This deletes all data and starts fresh.

## Architecture

| Service       | Purpose                          | Port  |
|---------------|----------------------------------|-------|
| frontend      | Nginx reverse proxy              | 8080  |
| backend       | ZirakERP application server      | 8000* |
| websocket     | Real-time updates (Socket.IO)    | 9000* |
| db            | MariaDB database                 | 3306* |
| redis-cache   | Caching layer                    | 6379* |
| redis-queue   | Background job queue             | 6379* |
| scheduler     | Cron-like scheduled tasks        | -     |
| queue-short   | Short-running background jobs    | -     |
| queue-long    | Long-running background jobs     | -     |
| configurator  | One-time setup (exits after)     | -     |
| create-site   | One-time site creation (exits)   | -     |

*Internal ports only — not exposed to host
