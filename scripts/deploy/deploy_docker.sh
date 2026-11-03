#!/bin/bash
# PlannedEducation - Simple Deployment Script
# Usage: ./deploy.sh [environment]
# Environments: development, production

set -e

ENVIRONMENT=${1:-production}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "PlannedEducation Deployment Script"
echo "Environment: $ENVIRONMENT"
echo "=========================================="

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo "ERROR: Docker Compose not installed."
        exit 1
    fi
    
    if [ ! -f .env ]; then
        echo "ERROR: .env file not found. Copy .env.example to .env and configure."
        exit 1
    fi
    
    echo "Prerequisites check passed."
}

# Generate secure secrets if not set
generate_secrets() {
    echo "Checking for required secrets..."
    
    if grep -q "your-super-secret-jwt-key-change-in-production" .env; then
        echo "Generating JWT_SECRET_KEY..."
        JWT_KEY=$(python3 -c "import secrets; print(secrets.token_hex(64))")
        sed -i "s/your-super-secret-jwt-key-change-in-production-min-64-chars/$JWT_KEY/" .env
    fi
    
    if grep -q "your-fernet-key-change-in-production-44-chars" .env; then
        echo "Generating AI_KEY_MASTER_SECRET..."
        FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
        sed -i "s/your-fernet-key-change-in-production-44-chars/$FERNET_KEY/" .env
    fi
    
    if grep -q "changeme" .env && grep -q "POSTGRES_PASSWORD=changeme" .env; then
        echo "Generating POSTGRES_PASSWORD..."
        PG_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i "s/POSTGRES_PASSWORD=changeme/POSTGRES_PASSWORD=$PG_PASS/" .env
    fi
    
    if grep -q "GRAFANA_PASSWORD=admin" .env; then
        echo "Generating GRAFANA_PASSWORD..."
        GRAFANA_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
        sed -i "s/GRAFANA_PASSWORD=admin/GRAFANA_PASSWORD=$GRAFANA_PASS/" .env
    fi
}

# Deploy function
deploy() {
    echo "Starting deployment for $ENVIRONMENT..."
    
    # Pull latest images
    echo "Pulling latest Docker images..."
    docker-compose pull
    
    # Build images
    echo "Building images..."
    docker-compose build --no-cache
    
    # Start services
    echo "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    echo "Waiting for services to be healthy..."
    sleep 15
    
    # Initialize database
    echo "Initializing database..."
    docker-compose exec -T backend python -c "
from src.plannededucation.api.database import Base, engine
from src.plannededucation.api import models
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
    
    # Create admin user if not exists - FAIL CLOSED if no admin configured
    echo "Creating admin user..."
    docker-compose exec -T backend python -c "
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.models import User

db = SessionLocal()
admin = db.query(User).filter(User.is_admin == True).first()
if not admin:
    print('ERROR: No admin account configured. Set ADMIN_EMAIL and ADMIN_PASSWORD environment variables.')
    print('Exiting deployment to prevent predictable credentials.')
    exit(1)
else:
    print(f'Admin account exists: {admin.email}')
"
    
    echo "=========================================="
    echo "Deployment complete!"
    echo "=========================================="
    echo "Frontend: http://localhost:5173 (or your domain)"
    echo "API Docs: http://localhost:8000/docs"
    echo "Admin: Check your configured ADMIN_EMAIL"
    echo "CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN"
}

# Main
main() {
    check_prerequisites
    generate_secrets
    deploy
}

main "$@"