#!/bin/bash
# setup-server.sh — Run ONCE on Hetzner to provision everything
# Usage: ssh deploy@178.105.80.193 'bash -s' < setup-server.sh

set -e

REMOTE_DIR="/home/deploy/nearme-osint"

echo "=== Provisioning NearMe OSINT server ==="

# System deps
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv postgresql postgresql-contrib postgresql-14-postgis-3 nginx certbot python3-certbot-nginx

# PostgreSQL setup
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
cd $REMOTE_DIR

# Python venv
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# Init DB
python -c "from src.db import init_db; init_db()"

# Run collector once
python run.py

# PM2 for API
pm2 delete nearme-api 2>/dev/null || true
pm2 start 'venv/bin/uvicorn src.api.server:app --host 0.0.0.0 --port 8089' --name nearme-api
pm2 save

# Cron for collector every 15 min
CRON_CMD="*/15 * * * * cd $REMOTE_DIR && /home/deploy/nearme-osint/venv/bin/python run.py >> /home/deploy/nearme-osint/logs/collect.log 2>&1"
(crontab -l 2>/dev/null | grep -v "nearme-osint"; echo "$CRON_CMD") | crontab -

# Log dir
mkdir -p $REMOTE_DIR/logs

# Nginx
sudo tee /etc/nginx/sites-available/nearme > /dev/null <<'NGINX'
server {
    listen 80;
    server_name nearme.viajeinteligencia.com;

    location / {
        proxy_pass http://127.0.0.1:8089;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/deploy/nearme-osint/frontend/;
        expires 1h;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/nearme /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# SSL
sudo certbot --nginx -d nearme.viajeinteligencia.com --non-interactive --agree-tos --email news@viajeinteligencia.com 2>/dev/null || echo "SSL already configured"

# UFW
sudo ufw allow 80/tcp 2>/dev/null || true
sudo ufw allow 443/tcp 2>/dev/null || true

echo "=== Server provisioned ==="
echo "    API: http://localhost:8089"
echo "    URL: https://nearme.viajeinteligencia.com"
