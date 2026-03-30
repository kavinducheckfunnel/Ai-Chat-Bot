#!/usr/bin/env bash
# =============================================================================
# Checkfunnel — Full VPS Deployment Script
# Ubuntu 24.04 LTS | Run as root on a fresh server
# Usage: bash deploy.sh
# =============================================================================
set -e

# ── Config ────────────────────────────────────────────────────────────────────
DOMAIN="app.checkfunnels.com"
APP_DIR="/var/www/checkfunnel"
APP_USER="checkfunnel"
REPO_URL="https://github.com/kavinducheckfunnel/Ai-Chat-Bot.git"
PYTHON="python3.12"
PG_DB="checkfunnel_db"
PG_USER="checkfunnel_user"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✔] $1${NC}"; }
warn()  { echo -e "${YELLOW}[!] $1${NC}"; }

# =============================================================================
# 1. SYSTEM UPDATE
# =============================================================================
info "Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq

apt-get install -y -qq \
    curl wget gnupg2 ca-certificates lsb-release \
    software-properties-common apt-transport-https \
    git build-essential libssl-dev libffi-dev \
    python3.12 python3.12-venv python3.12-dev python3-pip \
    nginx certbot python3-certbot-nginx \
    redis-server \
    supervisor \
    ufw

# =============================================================================
# 2. POSTGRESQL 16 + PGVECTOR
# =============================================================================
info "Installing PostgreSQL 16..."
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] \
    https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list
apt-get update -qq
apt-get install -y -qq postgresql-16 postgresql-client-16 postgresql-server-dev-16

info "Installing pgvector..."
apt-get install -y -qq postgresql-16-pgvector

systemctl enable --now postgresql redis-server
info "PostgreSQL and Redis started."

# =============================================================================
# 3. NODE.JS 20 LTS
# =============================================================================
info "Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y -qq nodejs
info "Node $(node -v) installed."

# =============================================================================
# 4. APP USER + DIRECTORY
# =============================================================================
info "Creating app user and directory..."
id -u $APP_USER &>/dev/null || useradd --system --shell /bin/bash --create-home $APP_USER
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

# =============================================================================
# 5. CLONE REPOSITORY
# =============================================================================
info "Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    warn "Repo already exists — pulling latest changes."
    sudo -u $APP_USER git -C $APP_DIR pull
else
    warn "Enter your GitHub Personal Access Token when prompted."
    read -rsp "GitHub PAT: " GH_TOKEN; echo
    CLONE_URL="https://${GH_TOKEN}@github.com/kavinducheckfunnel/Ai-Chat-Bot.git"
    sudo -u $APP_USER git clone "$CLONE_URL" "$APP_DIR"
fi

# =============================================================================
# 6. PYTHON VIRTUALENV + DEPENDENCIES
# =============================================================================
info "Setting up Python virtual environment..."
sudo -u $APP_USER $PYTHON -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt -q

info "Installing Playwright browsers..."
sudo -u $APP_USER $APP_DIR/venv/bin/playwright install chromium --with-deps

# =============================================================================
# 7. ENVIRONMENT FILE
# =============================================================================
if [ ! -f "$APP_DIR/.env" ]; then
    info "Creating .env from example — EDIT THIS FILE before continuing!"
    cp $APP_DIR/.env.example $APP_DIR/.env
    chown $APP_USER:$APP_USER $APP_DIR/.env
    chmod 600 $APP_DIR/.env

    # Generate a random Django secret key
    SECRET=$(openssl rand -hex 50)
    sed -i "s|change-me-to-a-long-random-string|$SECRET|g" $APP_DIR/.env
    sed -i "s|your_secure_password|$(openssl rand -hex 16)|g" $APP_DIR/.env

    warn "────────────────────────────────────────────────────────────"
    warn "IMPORTANT: Edit $APP_DIR/.env and fill in:"
    warn "  - FRIEND_AWS_ACCESS_KEY_ID"
    warn "  - FRIEND_AWS_SECRET_ACCESS_KEY"
    warn "  - EMAIL_HOST_USER / EMAIL_HOST_PASSWORD"
    warn "Then re-run: bash $APP_DIR/deploy.sh"
    warn "────────────────────────────────────────────────────────────"
    exit 0
fi

# Load env vars for setup steps
set -a; source $APP_DIR/.env; set +a

# =============================================================================
# 8. POSTGRESQL DATABASE SETUP
# =============================================================================
info "Setting up PostgreSQL database..."
PG_PASS=$(grep POSTGRES_PASSWORD $APP_DIR/.env | cut -d= -f2)

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'" \
    | grep -q 1 || sudo -u postgres psql -c \
    "CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$PG_DB'" \
    | grep -q 1 || sudo -u postgres psql -c \
    "CREATE DATABASE $PG_DB OWNER $PG_USER;"

sudo -u postgres psql -d $PG_DB -c "CREATE EXTENSION IF NOT EXISTS vector;"
info "Database and pgvector extension ready."

# =============================================================================
# 9. DJANGO SETUP
# =============================================================================
info "Running Django migrations..."
cd $APP_DIR
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py migrate --noinput

info "Collecting static files..."
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py collectstatic --noinput

info "Creating superadmin (if not exists)..."
sudo -u $APP_USER $APP_DIR/venv/bin/python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@checkfunnels.com', 'changeme123!')
    print('Superuser created: admin / changeme123!')
else:
    print('Superuser already exists.')
"

# =============================================================================
# 10. VUE FRONTEND BUILD
# =============================================================================
info "Building Vue frontend..."
cd $APP_DIR/widget-vue
npm ci --silent
npm run build
cd $APP_DIR
info "Vue build complete."

# =============================================================================
# 11. SYSTEMD SERVICES
# =============================================================================
info "Creating systemd services..."

# ── Daphne (ASGI) ─────────────────────────────────────────────────────────────
cat > /etc/systemd/system/checkfunnel-daphne.service << EOF
[Unit]
Description=Checkfunnel Daphne ASGI Server
After=network.target postgresql.service redis.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/daphne \\
    -u /run/checkfunnel/daphne.sock \\
    checkfunnel.asgi:application
ExecStartPre=/bin/mkdir -p /run/checkfunnel
ExecStartPre=/bin/chown $APP_USER:www-data /run/checkfunnel
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ── Celery Worker ─────────────────────────────────────────────────────────────
cat > /etc/systemd/system/checkfunnel-celery.service << EOF
[Unit]
Description=Checkfunnel Celery Worker
After=network.target redis.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/celery -A checkfunnel worker \\
    --loglevel=info --concurrency=2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ── Celery Beat ───────────────────────────────────────────────────────────────
cat > /etc/systemd/system/checkfunnel-celerybeat.service << EOF
[Unit]
Description=Checkfunnel Celery Beat Scheduler
After=network.target redis.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/celery -A checkfunnel beat \\
    --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat
systemctl restart checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat
info "All services started."

# =============================================================================
# 12. NGINX CONFIG
# =============================================================================
info "Configuring Nginx..."

cat > /etc/nginx/sites-available/checkfunnel << EOF
upstream daphne {
    server unix:/run/checkfunnel/daphne.sock fail_timeout=0;
}

server {
    listen 80;
    server_name $DOMAIN;

    # Redirect HTTP → HTTPS (certbot will handle this)
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    # SSL — managed by Certbot
    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 20M;

    # ── Static files (Django collectstatic) ──────────────────────────────────
    location /static/ {
        alias $APP_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # ── Vue admin SPA assets ──────────────────────────────────────────────────
    location /admin-assets/ {
        alias $APP_DIR/widget-vue/dist/assets/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # ── WebSocket connections ─────────────────────────────────────────────────
    location /ws/ {
        proxy_pass http://daphne;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }

    # ── Everything else → Django / Daphne ────────────────────────────────────
    location / {
        proxy_pass http://daphne;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/checkfunnel /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
info "Nginx config validated."

# =============================================================================
# 13. SSL CERTIFICATE (Let's Encrypt)
# =============================================================================
info "Obtaining SSL certificate for $DOMAIN..."
# Temporarily serve HTTP for ACME challenge
sed -i 's/return 301/#return 301/' /etc/nginx/sites-available/checkfunnel
systemctl reload nginx
certbot --nginx -d $DOMAIN --non-interactive --agree-tos \
    -m "admin@checkfunnels.com" --redirect || \
    warn "SSL cert failed — check DNS is pointing to this server's IP first."
sed -i 's/#return 301/return 301/' /etc/nginx/sites-available/checkfunnel
systemctl reload nginx

# =============================================================================
# 14. FIREWALL
# =============================================================================
info "Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
info "Firewall enabled (SSH + HTTP/HTTPS open)."

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Checkfunnel deployed at https://$DOMAIN  ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Admin login:  https://$DOMAIN/panel/"
echo "  Default user: admin"
echo "  Default pass: changeme123!  ← CHANGE THIS NOW"
echo ""
echo "  Service status:"
systemctl is-active checkfunnel-daphne checkfunnel-celery checkfunnel-celerybeat
echo ""
