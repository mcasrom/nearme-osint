#!/bin/bash
# deploy.sh — Deploy NearMe OSINT to Hetzner server
# Usage: bash deploy.sh

set -e

SERVER="deploy@178.105.80.193"
REMOTE_DIR="/home/deploy/nearme-osint"
REPO="git@github.com:mcasrom/nearme-osint.git"

echo "=== NearMe OSINT Deploy ==="

# Step 1: Push to GitHub
echo "[1/5] Pushing to GitHub..."
git add -A
git commit -m "Deploy: $(date +%Y-%m-%d_%H:%M)" || echo "Nothing to commit"
git push origin main

# Step 2: Check if remote dir exists, if not provision
echo "[2/5] Checking server..."
ssh $SERVER "test -d $REMOTE_DIR" 2>/dev/null || {
    echo "    First deploy — provisioning server..."
    ssh $SERVER "bash -s" <<'PROVISION'
set -e
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv postgresql postgresql-contrib postgis postgresql-14-postgis-3 nginx certbot python3-certbot-nginx

# Create deploy user dir
mkdir -p /home/deploy/nearme-osint

# Setup PostgreSQL
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='nearme'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER nearme WITH PASSWORD 'nearme_pass_2026';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='nearme_osint'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE nearme_osint OWNER nearme;"
sudo -u postgres psql -d nearme_osint -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d nearme_osint -c "GRANT ALL PRIVILEGES ON DATABASE nearme_osint TO nearme;"
sudo -u postgres psql -d nearme_osint -c "GRANT ALL ON SCHEMA public TO nearme;"

# Clone repo
cd /home/deploy
git clone git@github.com:mcasrom/nearme-osint.git 2>/dev/null || true

# Python venv
cd nearme-osint
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# Create .env from template if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "    Archivo .env creado desde .env.example — edítalo con credenciales reales"
fi
echo "    Provisioning done."
PROVISION
}

# Step 3: Sync code
echo "[3/5] Syncing code..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude 'venv' \
    --exclude '*.pyc' \
    --exclude 'data/' \
    --exclude 'logs/' \
    --exclude '.env' \
    ./ $SERVER:$REMOTE_DIR/

# Step 4: Install deps + init DB
echo "[4/5] Installing dependencies..."
ssh $SERVER "cd $REMOTE_DIR && \
    test -d venv || python3 -m venv venv && \
    source venv/bin/activate && \
    pip install -q -r requirements.txt && \
    python -c 'from src.db import init_db; init_db()'"

# Step 5: Restart services
echo "[5/5] Restarting services..."
ssh $SERVER "
    cd $REMOTE_DIR && source venv/bin/activate

    # Kill old process on port 8100
    fuser -k 8100/tcp 2>/dev/null || true

    # Restart API via PM2
    pm2 delete nearme-api 2>/dev/null || true
    pm2 start \"\$(which uvicorn)\" --interpreter python3 --name nearme-api -- src.api.server:app --host 0.0.0.0 --port 8100
    pm2 save

    # Reload nginx
    sudo nginx -t && sudo systemctl reload nginx
"

echo "=== Deploy complete ==="
echo "    URL: https://nearme.viajeinteligencia.com"
