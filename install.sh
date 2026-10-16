#!/bin/bash
# PlannedEducation Linux Installer
# Run with: curl -fsSL https://raw.githubusercontent.com/ezixen/PlannedEducation/main/install.sh | bash
# Or download and run: chmod +x install.sh && ./install.sh

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

print_header() {
    echo -e "\n${CYAN}${BOLD}============================================================${RESET}"
    echo -e "${CYAN}${BOLD}$1${RESET}"
    echo -e "${CYAN}${BOLD}============================================================${RESET}\n"
}

print_step() {
    echo -e "${BLUE}${BOLD}[Step $1/$2] $3${RESET}"
}

print_success() {
    echo -e "${GREEN}[OK] $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}[WARN] $1${RESET}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${RESET}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_warning "Running as root. This is not recommended for production."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_header "PlannedEducation Linux Installer"

# Detect OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    print_success "Detected OS: $PRETTY_NAME"
else
    print_warning "Could not detect OS version"
fi

# Choose deployment mode
print_header "Deployment Mode Selection"
echo -e "${BOLD}Choose deployment mode:${RESET}"
echo -e "  ${GREEN}1)${RESET} Native (no Docker) - PostgreSQL, Redis, and app run directly on host"
echo -e "  ${GREEN}2)${RESET} Docker Compose - All services in containers (current default)"
echo
read -p "Select mode [1/2] [1]: " DEPLOY_MODE
DEPLOY_MODE="${DEPLOY_MODE:-1}"

if [[ "$DEPLOY_MODE" == "1" ]]; then
    DEPLOY_NATIVE=true
    print_success "Native deployment selected"
else
    DEPLOY_NATIVE=false
    print_success "Docker Compose deployment selected"
fi

# Check requirements
print_step 1 8 "Checking requirements..."

check_command() {
    if command -v "$1" &> /dev/null; then
        version=$($1 --version 2>&1 | head -n1)
        print_success "$1: $version"
        return 0
    else
        print_error "$1: NOT FOUND"
        return 1
    fi
}

checks_passed=true
USE_SQLITE=false

if [[ "$DEPLOY_NATIVE" == "true" ]]; then
    # Native deployment requirements
    # Python and Git are mandatory
    for cmd in git python3; do
        if ! check_command "$cmd"; then
            checks_passed=false
        fi
    done
    
    # Optional services
    if ! command -v psql &> /dev/null || ! command -v redis-cli &> /dev/null; then
        print_warning "PostgreSQL or Redis CLI not found. Falling back to Native SQLite mode (zero-configuration standalone mode)."
        USE_SQLITE=true
    else
        # Check PostgreSQL service
        if systemctl is-active --quiet postgresql 2>/dev/null || service postgresql status 2>/dev/null | grep -q "active"; then
            print_success "PostgreSQL: running"
        else
            print_warning "PostgreSQL: not running (will attempt to start or fall back to SQLite)"
        fi
        
        # Check Redis service
        if systemctl is-active --quiet redis 2>/dev/null || service redis status 2>/dev/null | grep -q "active"; then
            print_success "Redis: running"
        else
            print_warning "Redis: not running (will attempt to start)"
        fi
    fi
else
    # Docker deployment requirements
    for cmd in docker git python3; do
        if ! check_command "$cmd"; then
            checks_passed=false
        fi
    done

    # Check Docker Compose
    if docker compose version &> /dev/null; then
        version=$(docker compose version --short)
        print_success "Docker Compose: $version"
    elif command -v docker-compose &> /dev/null; then
        version=$(docker-compose --version | head -n1)
        print_success "Docker Compose: $version"
    else
        print_error "Docker Compose: NOT FOUND"
        checks_passed=false
    fi
fi

if [[ "$checks_passed" != "true" ]]; then
    print_error "Please install missing requirements and try again."
    if [[ "$DEPLOY_NATIVE" == "true" ]]; then
        echo "Ubuntu/Debian: sudo apt update && sudo apt install -y git python3 python3-venv python3-pip"
    else
        echo "Install Docker: https://docs.docker.com/engine/install/"
        echo "Install Docker Compose: https://docs.docker.com/compose/install/"
    fi
    exit 1
fi

# Get installation directory
print_step 2 8 "Setting up installation directory..."
INSTALL_DIR="${1:-/opt/plannededucation}"
read -p "Installation directory [$INSTALL_DIR]: " input_dir
INSTALL_DIR="${input_dir:-$INSTALL_DIR}"

if [[ -d "$INSTALL_DIR" ]]; then
    print_warning "Directory $INSTALL_DIR already exists"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Clone repository
print_step 3 8 "Cloning repository..."
if [[ -d "$INSTALL_DIR/.git" ]]; then
    print_warning "Repository already exists, pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone https://github.com/ezixen/PlannedEducation.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Configure environment
print_step 4 8 "Configuring environment..."
if [[ ! -f .env ]]; then
    cp .env.example .env
    
    # Generate secure keys
    JWT_KEY=$(python3 -c "import secrets; print(secrets.token_hex(64))")
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    # Get domain
    read -p "School domain (e.g., yourschool.edu) [localhost]: " DOMAIN
    DOMAIN="${DOMAIN:-localhost}"
    
    # Update .env
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_KEY|" .env
    sed -i "s|AI_KEY_MASTER_SECRET=.*|AI_KEY_MASTER_SECRET=$FERNET_KEY|" .env
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -base64 32)|" .env
    
    if [[ "$DOMAIN" != "localhost" ]]; then
        sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://$DOMAIN|" .env
        sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$DOMAIN|" .env
        sed -i "s|WEBAUTHN_RP_ID=.*|WEBAUTHN_RP_ID=$DOMAIN|" .env
        sed -i "s|WEBAUTHN_ORIGIN=.*|WEBAUTHN_ORIGIN=https://$DOMAIN|" .env
    fi
    
    print_success "Environment configured"
else
    print_warning ".env already exists, skipping configuration"
fi

# Build and start
print_step 5 8 "Building and starting platform..."

if [[ "$DEPLOY_NATIVE" == "true" ]]; then
    # Native deployment
    print_step 5 8 "Setting up Python environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -r src/requirements.txt
    
    # Build frontend
    print_step 5 8 "Building frontend..."
    cd web/apps/portal
    npm ci
    npm run build
    cd "$INSTALL_DIR"
    
    # Setup database
    if [[ "$USE_SQLITE" == "true" ]]; then
        print_step 5 8 "Setting up SQLite database..."
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///$INSTALL_DIR/plannededucation.db|" .env
        print_success "Configured SQLite: sqlite:///$INSTALL_DIR/plannededucation.db"
    else
        # Setup PostgreSQL database
        print_step 5 8 "Setting up PostgreSQL database..."
        DB_NAME="plannededucation"
        DB_USER="plannededucation"
        DB_PASS=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(24))")
        
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || true
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true
        
        # Update .env with database URL
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME|" .env
        
        # Start Redis
        sudo systemctl start redis 2>/dev/null || sudo service redis start 2>/dev/null || true
    fi
    
    # Initialize database
    print_step 6 8 "Initializing database..."
    source .venv/bin/activate
    python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
    
    # Create systemd services
    print_step 6 8 "Creating systemd services..."
    cat > /tmp/plannededucation-backend.service << EOF
[Unit]
Description=PlannedEducation Backend
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn src.plannededucation.api.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv /tmp/plannededucation-backend.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable plannededucation-backend
    sudo systemctl start plannededucation-backend
    
    # Configure nginx
    print_step 6 8 "Configuring nginx..."
    cat > /tmp/plannededucation-nginx << EOF
server {
    listen 80;
    server_name ${DOMAIN:-localhost};
    
    # Frontend static files
    location / {
        root $INSTALL_DIR/web/apps/portal/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    # Health checks
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF
    
    sudo mv /tmp/plannededucation-nginx /etc/nginx/sites-available/plannededucation
    sudo ln -sf /etc/nginx/sites-available/plannededucation /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx
    
else
    # Docker deployment
    docker compose up -d --build

    # Wait for services
    print_step 6 8 "Waiting for services to start..."
    sleep 20

    # Initialize database
    print_step 7 8 "Initializing database..."
    docker compose exec -T backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
fi

# Create admin user
print_step 7 8 "Creating admin user..."
read -p "Admin email [admin@yourschool.edu]: " ADMIN_EMAIL
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@yourschool.edu}"

read -p "Admin username [admin]: " ADMIN_USER
ADMIN_USER="${ADMIN_USER:-admin}"

read -p "Admin full name [School Administrator]: " ADMIN_NAME
ADMIN_NAME="${ADMIN_NAME:-School Administrator}"

read -s -p "Admin password (min 8 chars) [ChangeMe123!]: " ADMIN_PASS
echo
ADMIN_PASS="${ADMIN_PASS:-ChangeMe123!}"

if [[ "$DEPLOY_NATIVE" == "true" ]]; then
    source .venv/bin/activate
    python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User
from src.plannededucation.api.routes_auth import get_password_hash
db = SessionLocal()
admin = User(
    email='$ADMIN_EMAIL',
    username='$ADMIN_USER',
    full_name='$ADMIN_NAME',
    hashed_password=get_password_hash('$ADMIN_PASS'),
    role='admin',
    is_admin=True,
    is_active=True
)
db.add(admin)
db.commit()
print('Admin created: $ADMIN_EMAIL')
print('CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN')
"
else
    docker compose exec -T backend python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User
from src.plannededucation.api.routes_auth import get_password_hash
db = SessionLocal()
admin = User(
    email='$ADMIN_EMAIL',
    username='$ADMIN_USER',
    full_name='$ADMIN_NAME',
    hashed_password=get_password_hash('$ADMIN_PASS'),
    role='admin',
    is_admin=True,
    is_active=True
)
db.add(admin)
db.commit()
print('Admin created: $ADMIN_EMAIL')
print('CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN')
"
fi

# Verify deployment
print_step 8 8 "Verifying deployment..."

if [[ "$DEPLOY_NATIVE" == "true" ]]; then
    checks=(
        "Backend API:curl -f http://localhost:8000/health"
        "Frontend:curl -f http://localhost/health"
        "Database:sudo -u postgres psql -c 'SELECT 1' >/dev/null 2>&1"
        "Redis:redis-cli ping"
        "Nginx:systemctl is-active --quiet nginx"
        "Backend Service:systemctl is-active --quiet plannededucation-backend"
    )
else
    checks=(
        "Backend API:curl -f http://localhost:8000/health"
        "Frontend:curl -f http://localhost/health"
        "Database:docker compose exec -T postgres pg_isready -U postgres"
        "Redis:docker compose exec -T redis redis-cli ping"
    )
fi

all_ok=true
for check in "${checks[@]}"; do
    name="${check%%:*}"
    cmd="${check#*:}"
    if eval "$cmd" &> /dev/null; then
        echo -e "\033[0;32m[OK]\033[0m $name: OK"
    else
        echo -e "\033[0;31m[ERROR]\033[0m $name: FAILED"
        all_ok=false
    fi
done

# Show results
if [[ "$all_ok" == "true" ]]; then
    PROTOCOL="http"
    PORT=""
    if [[ "$DOMAIN" != "localhost" ]]; then
        PROTOCOL="https"
    fi
    URL="${PROTOCOL}://${DOMAIN}${PORT}"
    
    echo -e "\n\033[0;32m\033[1m╔══════════════════════════════════════════════════════════╗"
    echo -e "║                    DEPLOYMENT SUCCESSFUL!                    ║"
    echo -e "╚══════════════════════════════════════════════════════════╝\033[0m"
    echo -e "\n\033[1mAccess your platform:\033[0m"
    echo -e "  🌐 Frontend:  ${URL}"
    echo -e "  📚 API Docs:  ${PROTOCOL}://${DOMAIN}:8000/docs"
    echo -e "  ❤️  Health:    ${PROTOCOL}://${DOMAIN}:8000/health"
    echo -e "\n\033[1mFirst Login:\033[0m"
    echo -e "  1. Open ${URL} in your browser"
    echo -e "  2. Login with your admin credentials"
    echo -e "  3. \033[0;31mIMMEDIATELY change your password\033[0m in Settings → Security"
    echo -e "\n\033[1mUseful Commands:\033[0m"
    if [[ "$DEPLOY_NATIVE" == "true" ]]; then
        echo -e "  View logs:     sudo journalctl -u plannededucation-backend -f"
        echo -e "  Update:        cd $INSTALL_DIR && git pull && source .venv/bin/activate && pip install -r src/requirements.txt && cd web/apps/portal && npm ci && npm run build && sudo systemctl restart plannededucation-backend"
        echo -e "  Backup:        sudo -u postgres pg_dump plannededucation | gzip > backup_\$(date +%Y%m%d).sql.gz"
        echo -e "  Restart:       sudo systemctl restart plannededucation-backend nginx"
    else
        echo -e "  View logs:     docker compose logs -f backend"
        echo -e "  Update:        git pull && docker compose build --no-cache && docker compose up -d"
        echo -e "  Backup:        docker compose exec -T postgres pg_dump -U postgres plannededucation | gzip > backup_\$(date +%Y%m%d).sql.gz"
        echo -e "  Restart:       docker compose restart"
    fi
    echo -e "\n\033[1mNext Steps:\033[0m"
    echo -e "  1. Change admin password immediately"
    echo -e "  2. Configure Google OAuth (optional) in Settings"
    echo -e "  3. Add AI API keys in Settings → AI Keys"
    echo -e "  4. Download SEB config for secure exams"
    echo -e "  4. Set up daily backups (see DEPLOY_SIMPLE.md)"
    echo -e "\n\033[0;36mNeed help? Check DEPLOY_SIMPLE.md or GitHub Issues\033[0m"
else
    echo -e "\n\033[0;31mSome services failed to start."
    if [[ "$DEPLOY_NATIVE" == "true" ]]; then
        echo -e "Check logs with: sudo journalctl -u plannededucation-backend -f\033[0m"
    else
        echo -e "Check logs with: docker compose logs -f\033[0m"
    fi
fi