# Deployment Guide (Single VPS)

## Prerequisites
- Ubuntu 22.04 (or similar) with Docker Engine and docker compose plugin installed
- SSH access as a sudo-enabled user
- Ports 80 and 443 open in the firewall
- DNS record ready to point to the VPS (HTTPS enabled after DNS cut-over)

## One-Time Server Setup
```bash
# Install system dependencies if needed
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"
# Log out/in if you adjust group membership

# Clone source
git clone <YOUR_REPO_URL> eipr-portal
cd eipr-portal

# Copy env template and edit secrets
cp .env.example .env
# Edit .env with strong values for:
#   SECRET_KEY, APP_ENCRYPTION_KEY, POSTGRES_PASSWORD, RATE_LIMIT_* etc.

# Bring up the production stack
docker compose -f docker-compose.prod.yml up -d --build

# Apply database migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## Verifications
```bash
curl -sf http://localhost:8080/health
curl -sf http://localhost:8080/api/v1/health

# Inspect service health
docker compose -f docker-compose.prod.yml ps
```

## Nightly Backups
Backups run inside the `backups` service (nightly `pg_dump`). To list archives:
```bash
docker compose -f docker-compose.prod.yml run --rm backups ls -l /backups
```
Backups are stored under the `pg_backups` volume (retention: 7 most recent files).

## Updating
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## Enabling HTTPS (after DNS points to the VPS)
1. Edit `Caddyfile`, replace `:80` with your domain (e.g. `example.com`), remove the `auto_https off` global option, and optionally point portal traffic to HTTPS origins.
2. Reload Caddy:
   ```bash
   docker compose -f docker-compose.prod.yml restart caddy
   ```
   Caddy will request certificates automatically from Let's Encrypt.

## Restoring From Backup
```bash
LATEST=$(docker compose -f docker-compose.prod.yml run --rm backups sh -lc 'ls -1 /backups | tail -n1')

docker compose -f docker-compose.prod.yml stop api

# Reset database schema (destructive!)
docker compose -f docker-compose.prod.yml exec -T db psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-eipr} \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Restore data
docker compose -f docker-compose.prod.yml run --rm backups sh -lc "cat /backups/$LATEST" | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-eipr}

docker compose -f docker-compose.prod.yml up -d api

# Re-run migrations to ensure schema parity
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## Logs & Maintenance
```bash
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f caddy
```

For operational hardening (metrics, alerting, HTTPS redirect rules), extend the stack as needed once production is stable.
