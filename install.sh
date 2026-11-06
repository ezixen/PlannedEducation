#!/usr/bin/env bash
# ==============================================================================
# PlannedEducation - Complete Automated Installation Script (Linux / WSL)
# ==============================================================================
# Supports: Ubuntu/Debian, CentOS/RHEL/Fedora, Arch Linux, WSL2
# Designed for both human operators and AI coding/deployment agents.
#
# AI AGENT DEPLOYMENT CONTRACT (MANDATORY FOR AI AGENTS):
# AI agents can run this script non-interactively with `AUTO_CONFIRM=true`, BUT
# before invoking this installer, the AI agent MUST STOP AND ASK the human
# operator to confirm:
#   1. Target installation directory (`INSTALL_DIR`, e.g., /opt/plannededucation)
#   2. Deployment mode (`DEPLOY_MODE`: 1=SQLite Single-Server, 2=PostgreSQL+Redis, 3=Docker)
#   3. Initial Superadmin / School Admin identity (`ADMIN_EMAIL`, `ADMIN_NAME`, `ADMIN_PASS`, `SCHOOL_NAME`)
#   4. Domain and preferred ports (`DOMAIN`, `API_PORT` default 8000, `FRONTEND_PORT` default 5173)
#
# DIAGNOSTIC LOGS (for humans & AI agents):
# All installation and runtime logs are written to `<INSTALL_DIR>/logs/`:
#   - `logs/install.log`        (full installation log)
#   - `logs/install_error.log`  (installation warnings & errors only)
#   - `logs/backend.log`        (backend structured JSON log, INFO and above)
#   - `logs/backend_error.log`  (backend warnings/exceptions only, with tracebacks)
#   - `logs/backend_stdout.log` / `logs/backend_stderr.log` (raw console capture - check if the backend fails to start)
#   - `logs/frontend.log`       (frontend runtime stdout log)
#   - `logs/frontend_error.log` (frontend runtime stderr/errors only)
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

INSTALL_DIR="${INSTALL_DIR:-${1:-/opt/plannededucation}}"
DEPLOY_MODE="${DEPLOY_MODE:-1}"
DOMAIN="${DOMAIN:-localhost}"
API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@yourschool.edu}"
# F-031: no predictable default password; empty triggers interactive/random generation.
ADMIN_PASS="${ADMIN_PASSWORD:-${ADMIN_PASS:-}}"
ADMIN_NAME="${ADMIN_NAME:-School Administrator}"
SCHOOL_NAME="${SCHOOL_NAME:-PlannedEducation School}"
# Portable admin/env settings JSON (no DB / JWT secrets). Also PE_SETTINGS_FILE.
SETTINGS_FILE="${SETTINGS_FILE:-${PE_SETTINGS_FILE:-}}"
AUTO_CONFIRM="${AUTO_CONFIRM:-false}"
SHARED_VENV="${SHARED_VENV:-}"

LOG_DIR="$INSTALL_DIR/logs"
INSTALL_LOG="$LOG_DIR/install.log"
INSTALL_ERR_LOG="$LOG_DIR/install_error.log"

write_install_log() {
    local level="$1"
    local msg="$2"
    local is_err="${3:-false}"
    if [[ -d "$INSTALL_DIR" ]]; then
        mkdir -p "$LOG_DIR" 2>/dev/null || true
        local ts
        ts=$(date +"%Y-%m-%d %H:%M:%S")
        echo "[$ts] [$level] $msg" >> "$INSTALL_LOG" 2>/dev/null || true
        if [[ "$is_err" == "true" ]]; then
            echo "[$ts] [$level] $msg" >> "$INSTALL_ERR_LOG" 2>/dev/null || true
        fi
    fi
}

get_available_port() {
    local preferred="$1"
    shift
    local candidates=("$preferred" "$@")
    for p in "${candidates[@]}"; do
        if ! ss -ltn 2>/dev/null | grep -q -E ":${p}[[:space:]]" && ! netstat -ltn 2>/dev/null | grep -q -E ":${p}[[:space:]]"; then
            echo "$p"
            return 0
        fi
    done
    echo "$preferred"
}

print_header() {
    echo ""
    echo -e "${CYAN}============================================================${RESET}"
    echo -e "${BOLD}${CYAN}$1${RESET}"
    echo -e "${CYAN}============================================================${RESET}"
    echo ""
    write_install_log "STEP" "$1" "false"
}

print_success() {
    echo -e "${GREEN}[OK] $1${RESET}"
    write_install_log "OK" "$1" "false"
}

print_warning() {
    echo -e "${YELLOW}[WARN] $1${RESET}"
    write_install_log "WARN" "$1" "true"
}

print_error() {
    echo -e "${RED}[ERROR] $1${RESET}"
    write_install_log "ERROR" "$1" "true"
}

print_info() {
    echo -e "${BLUE}[INFO] $1${RESET}"
    write_install_log "INFO" "$1" "false"
}

confirm_action() {
    # Usage: confirm_action "message" [auto_default]
    # auto_default: "yes" (default) or "no" — used when AUTO_CONFIRM=true.
    # Preserve-data prompts MUST pass "no" so updates never wipe secrets/DB.
    local message="$1"
    local auto_default="${2:-yes}"
    if [[ "$AUTO_CONFIRM" == "true" ]]; then
        [[ "$auto_default" == "yes" ]]
        return $?
    fi
    read -r -p "$message (y/N): " response
    [[ "$response" =~ ^[Yy]$ ]]
}

is_existing_deployment() {
    local dir="$1"
    [[ -f "$dir/.env" || -f "$dir/plannededucation.db" || ( -f "$dir/config/deployment.json" && -d "$dir/src/plannededucation" ) ]]
}

check_command() {
    local name="$1"
    local cmd="$2"
    echo -n "Checking for $name... "
    if command -v "$cmd" &>/dev/null; then
        local ver
        ver=$("$cmd" --version 2>&1 | head -n 1 || true)
        echo -e "${GREEN}FOUND ($ver)${RESET}"
        return 0
    else
        echo -e "${RED}NOT FOUND${RESET}"
        return 1
    fi
}

load_dotenv() {
    local env_file="$1"
    if [[ -f "$env_file" ]]; then
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
    fi
}

print_header "PlannedEducation Automated Installer (Linux)"

# Detect OS
if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS=$ID
    VER=${VERSION_ID:-unknown}
else
    OS=$(uname -s)
    VER=$(uname -r)
fi
print_info "Detected OS: $OS $VER"

HAS_SUDO=false
if [[ $EUID -eq 0 ]]; then
    HAS_SUDO=true
elif sudo -n true 2>/dev/null; then
    HAS_SUDO=true
fi

# ==============================================================================
# Step 1: Check Required Dependencies
# ==============================================================================
print_header "Step 1: Checking Required Dependencies"

print_info "REQUIRED (must be installed for any mode):"
HAS_GIT=false; check_command "Git (REQUIRED)" "git" && HAS_GIT=true || true
HAS_PYTHON=false; check_command "Python 3.11+ (REQUIRED)" "python3" && HAS_PYTHON=true || true
HAS_NODE=false; check_command "Node.js 20+ (REQUIRED)" "node" && HAS_NODE=true || true
HAS_NPM=false; check_command "npm (REQUIRED)" "npm" && HAS_NPM=true || true
print_info ""
print_info "OPTIONAL (only needed for specific deployment modes):"
HAS_DOCKER=false; check_command "Docker (OPTIONAL - Mode 3)" "docker" && HAS_DOCKER=true || true
HAS_POSTGRES=false; check_command "PostgreSQL (OPTIONAL - Mode 2)" "psql" && HAS_POSTGRES=true || true
HAS_REDIS=false; check_command "Redis (OPTIONAL - Mode 2)" "redis-cli" && HAS_REDIS=true || true
print_info ""
print_info "NOTE: Mode 1 (SQLite) works with just Git, Python, and Node.js."
print_info "      Optional items are NOT required for Mode 1."

# ==============================================================================
# Step 2: Choose Deployment Mode
# ==============================================================================
print_header "Step 2: Choose Deployment Mode"

if [[ "$AUTO_CONFIRM" != "true" ]]; then
    echo "How would you like to deploy PlannedEducation?"
    echo ""
    echo "  1) Local Development / Single-Server (SQLite + In-Memory Cache) - Fastest setup"
    echo "  2) Production Server (PostgreSQL + Redis + Systemd + Nginx) - Recommended for schools"
    echo "  3) Docker Compose (All-in-One Containers) - Easiest management"
    echo ""
    read -r -p "Select mode [1-3] (default: $DEPLOY_MODE): " input_mode
    DEPLOY_MODE=${input_mode:-$DEPLOY_MODE}
fi

USE_SQLITE="false"
USE_DOCKER="false"

case "$DEPLOY_MODE" in
    1)
        print_info "Selected: Local Development / Single-Server Mode (SQLite)"
        USE_SQLITE="true"
        ;;
    2)
        print_info "Selected: Production Server Mode (PostgreSQL + Redis)"
        USE_SQLITE="false"
        ;;
    3)
        print_info "Selected: Docker Compose Mode"
        USE_DOCKER="true"
        ;;
    *)
        print_warning "Invalid selection. Defaulting to Mode 1 (SQLite)."
        DEPLOY_MODE="1"
        USE_SQLITE="true"
        ;;
esac

# ==============================================================================
# Step 3: Check & Install Required Dependencies
# ==============================================================================
print_header "Step 3: Checking & Installing Required Dependencies"

MISSING_REQUIRED=()
[[ "$HAS_GIT" == "false" ]] && MISSING_REQUIRED+=("git")
if [[ "$USE_DOCKER" == "false" ]]; then
    [[ "$HAS_PYTHON" == "false" ]] && MISSING_REQUIRED+=("python3")
    [[ "$HAS_NODE" == "false" ]] && MISSING_REQUIRED+=("nodejs")
    [[ "$HAS_NPM" == "false" ]] && MISSING_REQUIRED+=("npm")
fi
if [[ "$USE_SQLITE" == "false" && "$USE_DOCKER" == "false" ]]; then
    [[ "$HAS_POSTGRES" == "false" ]] && MISSING_REQUIRED+=("postgresql")
    [[ "$HAS_REDIS" == "false" ]] && MISSING_REQUIRED+=("redis")
fi
if [[ "$USE_DOCKER" == "true" && "$HAS_DOCKER" == "false" ]]; then
    MISSING_REQUIRED+=("docker")
fi

if [[ ${#MISSING_REQUIRED[@]} -gt 0 ]]; then
    print_warning "Missing required dependencies for Mode $DEPLOY_MODE: ${MISSING_REQUIRED[*]}"
    if confirm_action "Install missing dependencies using system package manager?"; then
        case "$OS" in
            ubuntu|debian|pop|linuxmint)
                sudo apt-get update
                sudo apt-get install -y curl wget gnupg2 software-properties-common build-essential libpq-dev python3 python3-venv python3-pip git
                if [[ "$HAS_NODE" == "false" || "$HAS_NPM" == "false" ]]; then
                    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                    sudo apt-get install -y nodejs
                fi
                if [[ "$USE_SQLITE" == "false" && "$USE_DOCKER" == "false" ]]; then
                    sudo apt-get install -y postgresql postgresql-contrib redis-server nginx certbot python3-certbot-nginx
                fi
                ;;
            centos|rhel|fedora|rocky|almalinux)
                sudo dnf install -y curl wget git gcc gcc-c++ make postgresql-devel python3 python3-pip nodejs npm
                ;;
            arch|manjaro)
                sudo pacman -Sy --noconfirm base-devel git python python-pip nodejs npm
                ;;
            *)
                print_error "Unsupported OS for automatic dependency installation: $OS"
                exit 1
                ;;
        esac
        print_success "Required dependencies installed!"
    else
        print_error "Cannot proceed without required dependencies."
        exit 1
    fi
else
    print_success "All required dependencies for Mode $DEPLOY_MODE are installed!"
fi

# ==============================================================================
# Step 4: Clone Repository & Setup Directory
# ==============================================================================
print_header "Step 4: Setting Up Application Directory"

if [[ "$AUTO_CONFIRM" != "true" ]]; then
    read -r -p "Installation directory (default: $INSTALL_DIR): " input_dir
    INSTALL_DIR=${input_dir:-$INSTALL_DIR}
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$INSTALL_DIR" ]]; then
    mkdir -p "$INSTALL_DIR" 2>/dev/null || {
        sudo mkdir -p "$INSTALL_DIR"
        sudo chown -R "$USER:$USER" "$INSTALL_DIR"
    }
    print_success "Created directory: $INSTALL_DIR"
fi

# DATA PRESERVATION: detect update-vs-fresh before mutating secrets/accounts.
IS_UPDATE="false"
if is_existing_deployment "$INSTALL_DIR"; then
    IS_UPDATE="true"
    print_header "Update Mode Detected"
    print_info "Existing deployment found under $INSTALL_DIR"
    print_info "Preserving database files, .env secrets, logs, uploads, and user accounts."
    print_info "This run will refresh application code/modules and apply additive schema updates only."
fi

PROTECTED_DATA_NAMES=".env .env.local plannededucation.db plannededucation.db-wal plannededucation.db-shm ADMIN_CREDENTIALS.txt admin_recovery_codes.tmp local-secrets logs uploads backups artifacts data"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    print_info "Cloning PlannedEducation repository into $INSTALL_DIR..."
    CLONE_TMP="$INSTALL_DIR.clone-tmp"
    rm -rf "$CLONE_TMP" 2>/dev/null || sudo rm -rf "$CLONE_TMP" 2>/dev/null || true
    # End-user / school installs track stable `main`.
    if git clone --quiet --branch main --single-branch https://github.com/ezixen/PlannedEducation.git "$CLONE_TMP" \
       || git clone --quiet https://github.com/ezixen/PlannedEducation.git "$CLONE_TMP"; then
        # Copy code without clobbering protected runtime data already present.
        shopt -s dotglob nullglob
        for item in "$CLONE_TMP"/*; do
            base="$(basename "$item")"
            skip="false"
            for protected in $PROTECTED_DATA_NAMES; do
                if [[ "$base" == "$protected" ]]; then
                    print_info "Preserving existing runtime data: $base"
                    skip="true"
                    break
                fi
            done
            if [[ "$skip" == "false" ]]; then
                cp -a "$item" "$INSTALL_DIR/"
            fi
        done
        shopt -u dotglob nullglob
        rm -rf "$CLONE_TMP" 2>/dev/null || sudo rm -rf "$CLONE_TMP" 2>/dev/null || true
        print_success "Repository cloned successfully"
    else
        print_error "git clone failed"
        exit 1
    fi
else
    print_info "Repository already exists in $INSTALL_DIR, pulling latest stable changes from origin/main..."
    (cd "$INSTALL_DIR" && git fetch origin 2>/dev/null || true
     git checkout main 2>/dev/null || true
     git pull origin main 2>/dev/null || true)
    print_success "Repository ready"
fi

# Sync local workspace files if running from a local repository checkout
if [[ -d "$SCRIPT_DIR/src/plannededucation" && "$SCRIPT_DIR" != "$INSTALL_DIR" ]]; then
    print_info "Syncing latest workspace source files from $SCRIPT_DIR to $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR/src" "$INSTALL_DIR/web/apps/portal/src"
    if command -v rsync &>/dev/null; then
        rsync -a --exclude '__pycache__' --exclude '*.pyc' "$SCRIPT_DIR/src/" "$INSTALL_DIR/src/"
        rsync -a --exclude 'node_modules' --exclude 'dist' --exclude '.mypy_cache' --exclude '.env*' "$SCRIPT_DIR/web/apps/portal/" "$INSTALL_DIR/web/apps/portal/"
    else
        cp -r "$SCRIPT_DIR/src/"* "$INSTALL_DIR/src/"
        cp -r "$SCRIPT_DIR/web/apps/portal/src/"* "$INSTALL_DIR/web/apps/portal/src/"
        [[ -f "$SCRIPT_DIR/web/apps/portal/package.json" ]] && cp -f "$SCRIPT_DIR/web/apps/portal/package.json" "$INSTALL_DIR/web/apps/portal/package.json"
        [[ -f "$SCRIPT_DIR/web/apps/portal/vite.config.ts" ]] && cp -f "$SCRIPT_DIR/web/apps/portal/vite.config.ts" "$INSTALL_DIR/web/apps/portal/vite.config.ts"
        [[ -f "$SCRIPT_DIR/web/apps/portal/index.html" ]] && cp -f "$SCRIPT_DIR/web/apps/portal/index.html" "$INSTALL_DIR/web/apps/portal/index.html"
    fi
    cp -f "$SCRIPT_DIR/install.sh" "$INSTALL_DIR/install.sh"
    cp -f "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/uninstall.sh"
    cp -f "$SCRIPT_DIR/install.ps1" "$INSTALL_DIR/install.ps1"
    cp -f "$SCRIPT_DIR/uninstall.ps1" "$INSTALL_DIR/uninstall.ps1"
fi

cd "$INSTALL_DIR"

# Optional portable admin/env settings file for clean installs
if [[ -n "$SETTINGS_FILE" ]]; then
    if [[ ! -f "$SETTINGS_FILE" ]]; then
        print_error "SETTINGS_FILE not found: $SETTINGS_FILE"
        exit 1
    fi
    export PE_SETTINGS_FILE_PATH="$SETTINGS_FILE"
    eval "$(python3 - <<'PY'
import json, os, shlex
from pathlib import Path
path = Path(os.environ["PE_SETTINGS_FILE_PATH"])
raw = json.loads(path.read_text(encoding="utf-8-sig"))
s = raw.get("settings", raw) if isinstance(raw, dict) else {}
def emit(k, v):
    if v is None:
        return
    print(f"export {k}={shlex.quote(str(v))}")
emit("DOMAIN", s.get("domain"))
emit("API_PORT", s.get("api_port"))
emit("FRONTEND_PORT", s.get("frontend_port"))
emit("SCHOOL_NAME", s.get("school_name"))
print("export PE_IMPORTED_SETTINGS=1")
PY
)"
    print_success "Loaded portable admin settings from $SETTINGS_FILE"
fi

# Read existing deployment.json defaults if available (on existing installations)
if [[ -f "$INSTALL_DIR/.env" && -f "$INSTALL_DIR/config/deployment.json" && -z "${PE_IMPORTED_SETTINGS:-}" ]]; then
    DEP_DOMAIN=$(python3 -c "import json; d=json.load(open('$INSTALL_DIR/config/deployment.json')); print(d.get('domain', ''))" 2>/dev/null || true)
    DEP_API_PORT=$(python3 -c "import json; d=json.load(open('$INSTALL_DIR/config/deployment.json')); print(d.get('api_port', ''))" 2>/dev/null || true)
    DEP_FRONTEND_PORT=$(python3 -c "import json; d=json.load(open('$INSTALL_DIR/config/deployment.json')); print(d.get('frontend_port', ''))" 2>/dev/null || true)
    DEP_SCHOOL=$(python3 -c "import json; d=json.load(open('$INSTALL_DIR/config/deployment.json')); print(d.get('school_name', ''))" 2>/dev/null || true)
    [[ -n "$DEP_DOMAIN" ]] && DOMAIN="$DEP_DOMAIN"
    [[ -n "$DEP_API_PORT" ]] && API_PORT="$DEP_API_PORT"
    [[ -n "$DEP_FRONTEND_PORT" ]] && FRONTEND_PORT="$DEP_FRONTEND_PORT"
    [[ -n "$DEP_SCHOOL" ]] && SCHOOL_NAME="$DEP_SCHOOL"
fi

# ==============================================================================
# Step 5: Configure Environment Variables & Secrets
# ==============================================================================
print_header "Step 5: Configuring Environment & Secrets"

ENV_FILE="$INSTALL_DIR/.env"
SHOULD_WRITE_ENV="false"
if [[ ! -f "$ENV_FILE" ]]; then
    SHOULD_WRITE_ENV="true"
elif [[ "$IS_UPDATE" == "true" ]]; then
    print_info "Keeping existing .env (update mode — secrets and DB encryption keys preserved)."
elif confirm_action "Overwrite existing .env configuration? WARNING: regenerates secrets and can lock out existing encrypted data." "no"; then
    SHOULD_WRITE_ENV="true"
else
    print_info "Keeping existing .env file"
fi
if [[ "$SHOULD_WRITE_ENV" == "true" ]]; then
    print_info "Generating cryptographically secure secrets..."

    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    FERNET_KEY=$(python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
    DB_ENC_KEY=$(python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
    RECOVERY_HASH_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    TOKEN_HASH_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        read -r -p "Enter your domain or IP address (default: $DOMAIN): " input_domain
        DOMAIN=${input_domain:-$DOMAIN}
    fi

    API_PORT=$(get_available_port "$API_PORT" 8002 8001 8080)
    FRONTEND_PORT=$(get_available_port "$FRONTEND_PORT" 5175 5174 5176)

    if [[ "$USE_SQLITE" == "true" ]]; then
        DB_URL="sqlite:///$INSTALL_DIR/plannededucation.db"
        REDIS_URL="memory://"
        ENV_MODE="development"
        SEB_BYPASS="true"
    else
        DB_PASS=$(python3 -c "import secrets; print(secrets.token_hex(16))")
        DB_URL="postgresql://pe_user:${DB_PASS}@localhost:5432/plannededucation"
        REDIS_URL="redis://localhost:6379/0"
        ENV_MODE="production"
        SEB_BYPASS="false"
    fi
    if [[ "$ENV_MODE" == "production" ]]; then
        FRONTEND_URL="https://${DOMAIN}"
    else
        FRONTEND_URL="http://${DOMAIN}:${FRONTEND_PORT}"
    fi

    cat > "$ENV_FILE" <<EOF
# PlannedEducation Environment Configuration
# Generated on $(date +"%d/%m/%Y %H:%M:%S")

# Database
DATABASE_URL=${DB_URL}

# Redis
REDIS_URL=${REDIS_URL}

# Security Secrets (NEVER SHARE THESE!)
JWT_SECRET_KEY=${JWT_SECRET}
RECOVERY_CODE_HASH_SECRET=${RECOVERY_HASH_SECRET}
TOKEN_HASH_SECRET=${TOKEN_HASH_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=${FERNET_KEY}
AI_KEY_MASTER_SECRET=${FERNET_KEY}
# Field-level DB encryption for chat bodies, TOTP secrets, recovery codes (distinct from JWT/AI keys)
DATABASE_ENCRYPTION=true
DB_ENCRYPTION_MASTER_KEY=${DB_ENC_KEY}

# Server Configuration
FRONTEND_URL=${FRONTEND_URL}
HOST=0.0.0.0
PORT=${API_PORT}
FRONTEND_PORT=${FRONTEND_PORT}
CORS_ORIGINS=http://${DOMAIN}:${FRONTEND_PORT},http://${DOMAIN}:5173,http://${DOMAIN}:5175,http://localhost:${FRONTEND_PORT},http://localhost:5173,http://localhost:5175,http://127.0.0.1:${FRONTEND_PORT},http://127.0.0.1:5173,http://127.0.0.1:5175,https://${DOMAIN}

# Anonymizer / Presidio
ANONYMIZER_ENABLED=true
ANONYMIZER_LANGUAGE=en

# Environment & SEB
ENVIRONMENT=${ENV_MODE}
PLANNED_EDUCATION_ENV=${ENV_MODE}
ALLOW_DEV_SEB_BYPASS=${SEB_BYPASS}
EOF
    chmod 600 "$ENV_FILE"
    print_success "Created .env file with secure random secrets (API port: $API_PORT, Frontend port: $FRONTEND_PORT)"

    mkdir -p "$INSTALL_DIR/config"
    CORS_LIST="http://${DOMAIN}:${FRONTEND_PORT},http://${DOMAIN}:5173,http://${DOMAIN}:5175,http://localhost:${FRONTEND_PORT},http://localhost:5173,http://localhost:5175,http://127.0.0.1:${FRONTEND_PORT},http://127.0.0.1:5173,http://127.0.0.1:5175,https://${DOMAIN}"
    if [[ -n "${PE_IMPORTED_SETTINGS:-}" && -n "${PE_SETTINGS_FILE_PATH:-}" ]]; then
        export ENV_MODE SEB_BYPASS
        export CORS_LIST
        python3 - <<PY
import json, os
from datetime import datetime, timezone
from pathlib import Path
raw = json.loads(Path(os.environ["PE_SETTINGS_FILE_PATH"]).read_text(encoding="utf-8-sig"))
s = raw.get("settings", raw) if isinstance(raw, dict) else {}
dep = {
    "school_name": os.environ.get("SCHOOL_NAME") or s.get("school_name") or "PlannedEducation School",
    "domain": os.environ.get("DOMAIN") or s.get("domain") or "localhost",
    "api_port": int(os.environ.get("API_PORT") or s.get("api_port") or 8000),
    "frontend_port": int(os.environ.get("FRONTEND_PORT") or s.get("frontend_port") or 5173),
    "cors_origins": s.get("cors_origins") or os.environ.get("CORS_LIST") or "",
    "allowed_hosts": s.get("allowed_hosts") or f"{os.environ.get('DOMAIN', 'localhost')},localhost,127.0.0.1",
    "environment": os.environ.get("ENV_MODE") or s.get("environment") or "development",
    "allow_dev_seb_bypass": bool(s.get("allow_dev_seb_bypass", os.environ.get("SEB_BYPASS", "true") == "true")),
    "anonymizer_enabled": bool(s.get("anonymizer_enabled", True)),
    "anonymizer_language": s.get("anonymizer_language") or "en",
    "smtp_host": s.get("smtp_host"),
    "smtp_port": int(s.get("smtp_port") or 587),
    "smtp_user": s.get("smtp_user"),
    "smtp_use_tls": bool(s.get("smtp_use_tls", True)),
    "smtp_use_ssl": bool(s.get("smtp_use_ssl", False)),
    "email_from": s.get("email_from") or "PlannedEducation <noreply@localhost>",
    "header_mode": s.get("header_mode") or "text",
    "header_image_url": s.get("header_image_url"),
    "backup_location": s.get("backup_location") or "backups",
    "backup_frequency_days": int(s.get("backup_frequency_days") or 1),
    "backup_retention_days": int(s.get("backup_retention_days") or 30),
    "backup_time": s.get("backup_time") or "22:00",
    "admin_support_email": s.get("admin_support_email"),
    "home_exam_proctoring_enabled": bool(s.get("home_exam_proctoring_enabled", False)),
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
if not dep["cors_origins"]:
    dep["cors_origins"] = """$CORS_LIST"""
out = Path("$INSTALL_DIR/config/deployment.json")
out.write_text(json.dumps(dep, indent=2) + "\n", encoding="utf-8")
# Overlay non-secret env keys (crypto secrets already written above stay intact).
env_path = Path("$ENV_FILE")
lines = env_path.read_text(encoding="utf-8").splitlines()
updates = {
    "PE_SCHOOL_NAME": dep["school_name"],
    "ANONYMIZER_ENABLED": "true" if dep["anonymizer_enabled"] else "false",
    "ANONYMIZER_LANGUAGE": dep["anonymizer_language"],
    "ALLOW_DEV_SEB_BYPASS": "true" if dep["allow_dev_seb_bypass"] else "false",
    "HOME_EXAM_PROCTORING_ENABLED": "true" if dep["home_exam_proctoring_enabled"] else "false",
    "SMTP_HOST": dep.get("smtp_host") or "",
    "SMTP_PORT": str(dep.get("smtp_port") or 587),
    "SMTP_USER": dep.get("smtp_user") or "",
    "SMTP_USE_TLS": "true" if dep.get("smtp_use_tls") else "false",
    "SMTP_USE_SSL": "true" if dep.get("smtp_use_ssl") else "false",
    "EMAIL_FROM": dep.get("email_from") or "",
    "BACKUP_LOCATION": dep.get("backup_location") or "backups",
    "BACKUP_FREQUENCY_DAYS": str(dep.get("backup_frequency_days") or 1),
    "BACKUP_RETENTION_DAYS": str(dep.get("backup_retention_days") or 30),
    "BACKUP_TIME": dep.get("backup_time") or "22:00",
    "ADMIN_SUPPORT_EMAIL": dep.get("admin_support_email") or "",
}
seen = set()
out_lines = []
for line in lines:
    if line.strip() and not line.strip().startswith("#") and "=" in line:
        k = line.split("=", 1)[0].strip()
        if k in updates:
            out_lines.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out_lines.append(line)
for k, v in updates.items():
    if k not in seen:
        out_lines.append(f"{k}={v}")
env_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
PY
    else
        cat > "$INSTALL_DIR/config/deployment.json" <<EOF
{
  "school_name": "${SCHOOL_NAME}",
  "domain": "${DOMAIN}",
  "api_port": ${API_PORT},
  "frontend_port": ${FRONTEND_PORT},
  "cors_origins": "${CORS_LIST}",
  "allowed_hosts": "${DOMAIN},localhost,127.0.0.1",
  "environment": "${ENV_MODE}",
  "allow_dev_seb_bypass": $( [ "$SEB_BYPASS" = "true" ] && echo "true" || echo "false" ),
  "anonymizer_enabled": true,
  "anonymizer_language": "en",
  "home_exam_proctoring_enabled": false,
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
    fi
    chmod 600 "$INSTALL_DIR/config/deployment.json"
    print_success "Created config/deployment.json configuration file"
fi

load_dotenv "$ENV_FILE"
API_PORT="${PORT:-$API_PORT}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# ==============================================================================
# Step 6: Setup Application & Databases
# ==============================================================================
if [[ "$USE_DOCKER" == "true" ]]; then
    print_header "Step 6: Starting Docker Containers"
    print_info "Building and starting containers via Docker Compose..."
    docker compose up -d --build
    print_success "Docker containers started!"
else
    print_header "Step 6: Setting Up Databases & Application"

    if [[ "$USE_SQLITE" == "false" && "$HAS_SUDO" == "true" ]]; then
        print_info "Setting up PostgreSQL database..."
        sudo -u postgres psql -c "CREATE USER pe_user WITH PASSWORD '${DB_PASS:-}';" 2>/dev/null || true
        sudo -u postgres psql -c "CREATE DATABASE plannededucation OWNER pe_user;" 2>/dev/null || true
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE plannededucation TO pe_user;" 2>/dev/null || true
        print_success "PostgreSQL database configured"
    fi

    # Setup Python Virtual Environment
    if [[ -n "$SHARED_VENV" && -x "$SHARED_VENV/bin/python" ]]; then
        PYTHON_EXE="$SHARED_VENV/bin/python"
        print_info "Using shared Python virtual environment at $SHARED_VENV..."
    else
        print_info "Creating Python virtual environment at $INSTALL_DIR/.venv..."
        python3 -m venv "$INSTALL_DIR/.venv" || {
            python3 -m venv --without-pip "$INSTALL_DIR/.venv"
            curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$INSTALL_DIR/.venv/bin/python"
        }
        PYTHON_EXE="$INSTALL_DIR/.venv/bin/python"
    fi

    print_info "Installing Python dependencies..."
    "$PYTHON_EXE" -m pip install -q --upgrade pip
    "$PYTHON_EXE" -m pip install -q -r "$INSTALL_DIR/src/requirements.txt"
    print_success "Python dependencies installed"

    # Initialize / upgrade schema (additive only — never drops tables or wipes rows).
    if [[ "$IS_UPDATE" == "true" ]]; then
        print_info "Applying additive schema updates to existing database (no wipe)..."
    else
        print_info "Initializing database tables..."
    fi
    export PYTHONPATH="$INSTALL_DIR/src"
    "$PYTHON_EXE" -c "import plannededucation.api.models; from plannededucation.api.database import Base, engine; from plannededucation.api.schema_ensure import ensure_schema; Base.metadata.create_all(bind=engine); ensure_schema(engine); print('Database schema ready (create_all + ensure_schema; no data wipe).')"
    print_success "Database schema ready (existing user data preserved)"

    # Setup Frontend
    print_info "Building React frontend..."
    cd "$INSTALL_DIR/web/apps/portal"
    rm -f .env.local .env.development .env.production 2>/dev/null || true
    echo "VITE_API_URL=http://127.0.0.1:${API_PORT}" > .env
    echo "VITE_API_URL=http://127.0.0.1:${API_PORT}" > .env.local
    npm install --silent --no-audit --no-fund
    npm run build
    cd "$INSTALL_DIR"
    print_success "Frontend built successfully"

    mkdir -p "$LOG_DIR"

    # Create Complete Launcher & Management Script Suite
    cat > "$INSTALL_DIR/start_all.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$INSTALL_DIR/logs"
mkdir -p "$LOGS_DIR"

API_PORT=8000
FRONTEND_PORT=5173
DOMAIN="localhost"

if [[ -f "$INSTALL_DIR/config/deployment.json" ]]; then
    API_PORT="$(grep -o '"api_port":[ ]*[0-9]*' "$INSTALL_DIR/config/deployment.json" | grep -o '[0-9]*' || echo 8000)"
    FRONTEND_PORT="$(grep -o '"frontend_port":[ ]*[0-9]*' "$INSTALL_DIR/config/deployment.json" | grep -o '[0-9]*' || echo 5173)"
fi

echo "============================================================"
echo "   Starting PlannedEducation Platform"
echo "============================================================"

echo "1. Starting Backend on port $API_PORT..."
nohup "$INSTALL_DIR/start_backend.sh" </dev/null >> "$LOGS_DIR/backend_stdout.log" 2>> "$LOGS_DIR/backend_stderr.log" &
echo $! > "$LOGS_DIR/backend.pid"
disown $! 2>/dev/null || true

echo "2. Starting Frontend on port $FRONTEND_PORT..."
nohup "$INSTALL_DIR/start_frontend.sh" </dev/null >> "$LOGS_DIR/frontend.log" 2>> "$LOGS_DIR/frontend_error.log" &
echo $! > "$LOGS_DIR/frontend.pid"
disown $! 2>/dev/null || true

echo "3. Waiting for services to become ready..."
BACKEND_HEALTHY=false
FRONTEND_HEALTHY=false
for i in {1..30}; do
    sleep 1
    if [[ "$BACKEND_HEALTHY" != "true" ]]; then
        if curl -s "http://127.0.0.1:$API_PORT/health" 2>/dev/null | grep -q '"status":"ok"'; then
            BACKEND_HEALTHY=true
        fi
    fi
    if [[ "$FRONTEND_HEALTHY" != "true" ]]; then
        if curl -s -I "http://127.0.0.1:$FRONTEND_PORT" 2>/dev/null | grep -q 'HTTP'; then
            FRONTEND_HEALTHY=true
        fi
    fi
    if [[ "$BACKEND_HEALTHY" == "true" && "$FRONTEND_HEALTHY" == "true" ]]; then
        break
    fi
done

echo ""
echo "============================================================"
if [[ "$BACKEND_HEALTHY" == "true" && "$FRONTEND_HEALTHY" == "true" ]]; then
    echo "  [OK] PlannedEducation is LIVE and HEALTHY!"
    echo "============================================================"
    echo "  Frontend Portal: http://$DOMAIN:$FRONTEND_PORT"
    echo "  Backend API:     http://$DOMAIN:$API_PORT"
    echo "  API Docs:        http://$DOMAIN:$API_PORT/docs"
    echo "  To stop:         Run ./stop_all.sh"
    echo "============================================================"
else
    if [[ "$BACKEND_HEALTHY" != "true" ]]; then
        echo "  [WARN] Backend health check timed out."
        echo "  Check diagnostic logs in: $LOGS_DIR/backend_error.log and $LOGS_DIR/backend_stderr.log"
    fi
    if [[ "$FRONTEND_HEALTHY" != "true" ]]; then
        echo "  [WARN] Frontend preview check timed out."
        echo "  Check diagnostic logs in: $LOGS_DIR/frontend_error.log"
    fi
    echo "============================================================"
fi
EOF
    chmod +x "$INSTALL_DIR/start_all.sh"

    cat > "$INSTALL_DIR/stop_all.sh" << 'EOF'
#!/usr/bin/env bash
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$INSTALL_DIR/logs"

echo "Stopping PlannedEducation services..."
if [[ -f "$LOGS_DIR/backend.pid" ]]; then
    PID="$(cat "$LOGS_DIR/backend.pid")"
    if kill -0 "$PID" 2>/dev/null; then
        echo "  Stopping Backend (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
    fi
    rm -f "$LOGS_DIR/backend.pid"
fi

if [[ -f "$LOGS_DIR/frontend.pid" ]]; then
    PID="$(cat "$LOGS_DIR/frontend.pid")"
    if kill -0 "$PID" 2>/dev/null; then
        echo "  Stopping Frontend (PID: $PID)..."
        kill "$PID" 2>/dev/null || true
    fi
    rm -f "$LOGS_DIR/frontend.pid"
fi

pkill -f "uvicorn plannededucation.api.main:app" 2>/dev/null || true
pkill -f "preview-server.mjs" 2>/dev/null || true
pkill -f "vite preview" 2>/dev/null || true
pkill -f "npm run preview" 2>/dev/null || true
echo "[OK] PlannedEducation processes stopped."
EOF
    chmod +x "$INSTALL_DIR/stop_all.sh"

    cat > "$INSTALL_DIR/verify.sh" << 'EOF'
#!/usr/bin/env bash
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

API_PORT=8000
FRONTEND_PORT=5173
DOMAIN="localhost"

if [[ -f "$INSTALL_DIR/config/deployment.json" ]]; then
    API_PORT="$(grep -o '"api_port":[ ]*[0-9]*' "$INSTALL_DIR/config/deployment.json" | grep -o '[0-9]*' || echo 8000)"
    FRONTEND_PORT="$(grep -o '"frontend_port":[ ]*[0-9]*' "$INSTALL_DIR/config/deployment.json" | grep -o '[0-9]*' || echo 5173)"
fi

echo ""
echo "============================================================"
echo "  PlannedEducation Deployment Health Verification"
echo "============================================================"

ALL_OK=true

echo -n "Checking installation directory ($INSTALL_DIR)... "
if [[ -d "$INSTALL_DIR" ]]; then echo "OK"; else echo "FAIL"; ALL_OK=false; fi

echo -n "Checking database ($INSTALL_DIR/plannededucation.db)... "
if [[ -f "$INSTALL_DIR/plannededucation.db" ]]; then
    echo "OK ($(stat -c%s "$INSTALL_DIR/plannededucation.db" 2>/dev/null || wc -c < "$INSTALL_DIR/plannededucation.db") bytes)"
else
    echo "WARN (SQLite file not present, or using external PostgreSQL)"
fi

echo -n "Checking Backend API (http://127.0.0.1:$API_PORT/health)... "
if curl -s "http://127.0.0.1:$API_PORT/health" 2>/dev/null | grep -q '"status":"ok"'; then
    echo "OK"
else
    echo "NOT RESPONDING (Backend is not running)"
    ALL_OK=false
fi

echo -n "Checking Package Engine (http://127.0.0.1:$API_PORT/packages/health)... "
if curl -s "http://127.0.0.1:$API_PORT/packages/health" 2>/dev/null | grep -E -q '"status":"ok"|"available":true'; then
    echo "OK"
else
    echo "NOT RESPONDING"
fi

echo -n "Checking Frontend Portal (http://127.0.0.1:$FRONTEND_PORT)... "
if curl -s -I "http://127.0.0.1:$FRONTEND_PORT" 2>/dev/null | grep -q 'HTTP'; then
    echo "OK"
else
    echo "NOT LISTENING (Frontend is not running)"
    ALL_OK=false
fi

echo "============================================================"
if [[ "$ALL_OK" == "true" ]]; then
    echo "  Result: ALL SYSTEMS OPERATIONAL ✅"
    echo "  Portal URL:  http://$DOMAIN:$FRONTEND_PORT"
    echo "  Backend API: http://$DOMAIN:$API_PORT"
else
    echo "  Result: SOME SERVICES NOT RUNNING OR FAILED ⚠️"
    echo "  To start: Run ./start_all.sh"
    echo "  To stop:  Run ./stop_all.sh"
fi
echo "============================================================"
echo ""
EOF
    chmod +x "$INSTALL_DIR/verify.sh"

    cat > "$INSTALL_DIR/start_backend.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
INSTALL_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "\$INSTALL_DIR/logs"
if [[ -f "\$INSTALL_DIR/.env" ]]; then
    set -a
    source "\$INSTALL_DIR/.env"
    set +a
fi
export PYTHONPATH="\$INSTALL_DIR/src"
export PLANNED_EDUCATION_LOG_DIR="\$INSTALL_DIR/logs"
API_PORT="${API_PORT:-8000}"
if [[ -f "\$INSTALL_DIR/config/deployment.json" ]]; then
    API_PORT="\$(grep -o '"api_port":[ ]*[0-9]*' "\$INSTALL_DIR/config/deployment.json" | grep -o '[0-9]*' || echo \${API_PORT})"
fi
echo "Starting PlannedEducation Backend on port \${API_PORT}..."
echo "Structured logs: logs/backend.log, logs/backend_error.log"
exec "$PYTHON_EXE" -m uvicorn plannededucation.api.main:app --host 0.0.0.0 --port "\${API_PORT}"
EOF
    chmod +x "$INSTALL_DIR/start_backend.sh"

    cat > "$INSTALL_DIR/start_frontend.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export CI=true
INSTALL_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$INSTALL_DIR/web/apps/portal"
mkdir -p "\$INSTALL_DIR/logs"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
if [[ -f "\$INSTALL_DIR/config/deployment.json" ]]; then
    FRONTEND_PORT="\$(grep -o '"frontend_port":[ ]*[0-9]*' "\$INSTALL_DIR/config/deployment.json" | grep -o '[0-9]*' || echo \${FRONTEND_PORT})"
fi
PREVIEW_SCRIPT="\$INSTALL_DIR/web/apps/portal/scripts/preview-server.mjs"
if [[ -f "\$PREVIEW_SCRIPT" ]]; then
    exec node "\$PREVIEW_SCRIPT" "\${FRONTEND_PORT}" </dev/null
else
    exec npx vite preview --host 0.0.0.0 --port "\${FRONTEND_PORT}" </dev/null
fi
EOF
    chmod +x "$INSTALL_DIR/start_frontend.sh"
    print_success "Created launcher & management suite: start_all.sh, stop_all.sh, verify.sh, start_backend.sh, start_frontend.sh"


    # Setup Systemd & Nginx if in Mode 2 and root/sudo with active systemd
    if [[ "$USE_SQLITE" == "false" && "$HAS_SUDO" == "true" ]] && pidof systemd &>/dev/null; then
        print_info "Creating Systemd service for Backend..."
        cat > /tmp/plannededucation-backend.service <<EOF
[Unit]
Description=PlannedEducation FastAPI Backend
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PYTHONPATH=$INSTALL_DIR/src"
Environment="PLANNED_EDUCATION_LOG_DIR=$INSTALL_DIR/logs"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$PYTHON_EXE -m uvicorn plannededucation.api.main:app --host 0.0.0.0 --port ${API_PORT} --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/plannededucation-backend.service /etc/systemd/system/plannededucation-backend.service
sudo systemctl daemon-reload
sudo systemctl enable plannededucation-backend
sudo systemctl restart plannededucation-backend
print_success "Systemd service 'plannededucation-backend' started"
    fi
fi

# ==============================================================================
# Step 7: Create Initial Superadmin & School (fresh installs only)
# ==============================================================================
print_header "Step 7: Creating Initial Superadmin & School"

SKIP_ADMIN_BOOTSTRAP="false"
if [[ "$IS_UPDATE" == "true" && "$USE_DOCKER" == "false" ]]; then
    export PYTHONPATH="$INSTALL_DIR/src"
    load_dotenv "$ENV_FILE"
    USER_COUNT="$("$PYTHON_EXE" -c "from plannededucation.api.database import SessionLocal; from plannededucation.api.models import User; db=SessionLocal(); print(db.query(User).count()); db.close()" 2>/dev/null || echo "0")"
    if [[ "$USER_COUNT" =~ ^[0-9]+$ ]] && [[ "$USER_COUNT" -gt 0 ]]; then
        SKIP_ADMIN_BOOTSTRAP="true"
        print_info "Existing users detected ($USER_COUNT). Skipping admin bootstrap to preserve accounts and passwords."
        print_info "Set PE_FORCE_ADMIN_BOOTSTRAP=1 only if you intentionally need to reset the bootstrap superadmin."
    fi
    if [[ "${PE_FORCE_ADMIN_BOOTSTRAP:-}" == "1" ]]; then
        SKIP_ADMIN_BOOTSTRAP="false"
        print_warning "PE_FORCE_ADMIN_BOOTSTRAP=1 set — bootstrap admin may be created/updated."
    fi
fi

if [[ "$SKIP_ADMIN_BOOTSTRAP" == "true" ]]; then
    print_success "Update mode: existing school accounts left unchanged."
elif [[ "$AUTO_CONFIRM" != "true" ]]; then
    read -r -p "Enter School / Institution Name (default: $SCHOOL_NAME): " input_school
    SCHOOL_NAME=${input_school:-$SCHOOL_NAME}
    read -r -p "Enter Superadmin Email (default: $ADMIN_EMAIL): " input_email
    ADMIN_EMAIL=${input_email:-$ADMIN_EMAIL}
    read -r -s -p "Enter Superadmin Password (press Enter to generate a secure random password): " input_pass
    echo ""
    if [[ -n "$input_pass" ]]; then
        ADMIN_PASS="$input_pass"
    else
        ADMIN_PASS=$(openssl rand -base64 18 2>/dev/null || tr -dc 'A-Za-z0-9!@#%' </dev/urandom | head -c 20)
        GENERATED_RANDOM="true"
    fi
    read -r -p "Enter Superadmin Full Name (default: $ADMIN_NAME): " input_name
    ADMIN_NAME=${input_name:-$ADMIN_NAME}
else
    # AutoConfirm / non-interactive: reject empty/predictable passwords (F-031).
    if [[ -z "$ADMIN_PASS" || "$ADMIN_PASS" == "AdminPassword123!" || "$ADMIN_PASS" == "ChangeMe123!" || "$ADMIN_PASS" == "changeme" || "$ADMIN_PASS" == "password" ]]; then
        echo ""
        print_warning "[SECURITY REQUIREMENT] Superadmin Password Configuration"
        echo "For security, you must set a secure administrator password."
        if [ -t 0 ]; then
            read -r -s -p "Enter Superadmin Password (press Enter to generate a secure random password): " input_pass
            echo ""
            if [[ -n "$input_pass" ]]; then
                ADMIN_PASS="$input_pass"
            else
                ADMIN_PASS=$(openssl rand -base64 18 2>/dev/null || tr -dc 'A-Za-z0-9!@#%' </dev/urandom | head -c 20)
                GENERATED_RANDOM="true"
            fi
        else
            ADMIN_PASS=$(openssl rand -base64 18 2>/dev/null || tr -dc 'A-Za-z0-9!@#%' </dev/urandom | head -c 20)
            GENERATED_RANDOM="true"
            print_info "Non-interactive environment: generated a secure random administrator password."
        fi
    fi
fi

if [[ "${GENERATED_RANDOM:-false}" == "true" && "$SKIP_ADMIN_BOOTSTRAP" != "true" ]]; then
    echo ""
    echo -e "${YELLOW}============================================================${RESET}"
    echo -e "${GREEN}  [KEY] GENERATED SUPERADMIN PASSWORD${RESET}"
    echo -e "${YELLOW}============================================================${RESET}"
    echo -e "  Email / Username:   $ADMIN_EMAIL"
    echo -e "  Generated Password: ${GREEN}$ADMIN_PASS${RESET}"
    echo -e "${YELLOW}============================================================${RESET}"
    echo -e "${YELLOW}  [IMPORTANT] Please copy or write down this password now!${RESET}"
    echo -e "${YELLOW}  It will NOT be shown again in plaintext on screen.${RESET}"
    echo -e "${YELLOW}============================================================${RESET}"
    if [ -t 0 ] && [[ "$AUTO_CONFIRM" != "true" ]]; then
        read -r -p "  Press [Enter] once you have copied/noted down the password to continue: " _
    fi
    echo ""
fi

if [[ "$USE_DOCKER" == "false" && "$SKIP_ADMIN_BOOTSTRAP" != "true" ]]; then
    export PYTHONPATH="$INSTALL_DIR/src"
    export PE_ADMIN_EMAIL="$ADMIN_EMAIL"
    export PE_ADMIN_PASSWORD="$ADMIN_PASS"
    export PE_ADMIN_PASS="$ADMIN_PASS"
    export PE_ADMIN_NAME="$ADMIN_NAME"
    export PE_SCHOOL_NAME="$SCHOOL_NAME"

    SETUP_ADMIN_SCRIPT="$INSTALL_DIR/scripts/deploy/setup_admin.py"
    if [[ ! -f "$SETUP_ADMIN_SCRIPT" ]]; then
        SETUP_ADMIN_SCRIPT="${BASH_SOURCE[0]%/*}/scripts/deploy/setup_admin.py"
    fi
    "$PYTHON_EXE" "$SETUP_ADMIN_SCRIPT"

    CODES_TEXT=""
    if [[ -f "$INSTALL_DIR/admin_recovery_codes.tmp" ]]; then
        echo ""
        echo -e "${CYAN}============================================================${RESET}"
        echo -e "${YELLOW}  [KEY] SUPERADMIN EMERGENCY RECOVERY CODES${RESET}"
        echo -e "${CYAN}============================================================${RESET}"
        while IFS= read -r line; do
            echo -e "${GREEN}    $line${RESET}"
            CODES_TEXT="${CODES_TEXT}  - $line\n"
        done < "$INSTALL_DIR/admin_recovery_codes.tmp"
        echo -e "${CYAN}============================================================${RESET}"
        echo -e "${YELLOW}  [!] CRITICAL NOTICE FOR ADMINISTRATOR:${RESET}"
        echo -e "  1. Store these 5 one-time recovery codes safely (print or write them down)."
        echo -e "  2. If you lose your administrator password and recovery codes, you will"
        echo -e "     be permanently locked out and may need to redeploy the whole system,"
        echo -e "     as direct database injection is blocked for security."
        echo -e "  3. Recovery codes (not the password) are saved to:"
        echo -e "     ${CYAN}$INSTALL_DIR/ADMIN_CREDENTIALS.txt${RESET}"
        echo -e "${CYAN}============================================================${RESET}"
        if [ -t 0 ] && [[ "$AUTO_CONFIRM" != "true" ]]; then
            read -r -p "  Press [Enter] once you have safely copied or noted these codes to continue: " _
        fi
        echo ""
        rm -f "$INSTALL_DIR/admin_recovery_codes.tmp"
    fi

    # F-031: never write the admin password to disk; recovery codes only.
    cat > "$INSTALL_DIR/ADMIN_CREDENTIALS.txt" <<EOF
PlannedEducation Superadmin Recovery Codes (password NOT stored)
===============================================================
School Name:    $SCHOOL_NAME
Admin Email:    $ADMIN_EMAIL
Admin Name:     $ADMIN_NAME
Backend API:    http://$DOMAIN:$API_PORT
Frontend URL:   http://$DOMAIN:$FRONTEND_PORT

EMERGENCY RECOVERY CODES:
$(echo -e "$CODES_TEXT")
Password was shown once during install and is not written to disk.
WARNING: If you lose both your administrator password and these
recovery codes, you will be permanently locked out.
EOF
    chmod 600 "$INSTALL_DIR/ADMIN_CREDENTIALS.txt" 2>/dev/null || true
    print_success "Superadmin account ready: $ADMIN_EMAIL (recovery codes saved; password omitted from disk)"
fi

# ==============================================================================
# Step 8: Run Verification Tests
# ==============================================================================
print_header "Step 8: Running Verification Tests"

TESTS_PASSED=0
TESTS_FAILED=0

run_verify() {
    local name="$1"
    local cmd="$2"
    echo -n "Testing $name... "
    if eval "$cmd" &>/dev/null; then
        echo -e "${GREEN}PASSED${RESET}"
        write_install_log "VERIFY_PASS" "$name" "false"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}FAILED${RESET}"
        write_install_log "VERIFY_FAIL" "$name" "true"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

run_verify "Environment configuration (.env)" "test -s '$INSTALL_DIR/.env'"
run_verify "Deployment configuration (config/deployment.json)" "test -s '$INSTALL_DIR/config/deployment.json'"

if [[ "$USE_SQLITE" == "true" ]]; then
    run_verify "SQLite database initialized" "test -f '$INSTALL_DIR/plannededucation.db'"
elif [[ "$USE_DOCKER" == "false" ]]; then
    run_verify "PostgreSQL connection" "sudo -u postgres psql -c '\l'"
    run_verify "Redis connection" "redis-cli ping | grep -q PONG"
fi

if [[ "$USE_DOCKER" == "false" ]]; then
    run_verify "Frontend production build (dist/index.html)" "test -f '$INSTALL_DIR/web/apps/portal/dist/index.html'"
    run_verify "Backend FastAPI health endpoint (TestClient)" "set -a; [ -f '$INSTALL_DIR/.env' ] && source '$INSTALL_DIR/.env'; set +a; PYTHONPATH='$INSTALL_DIR/src' '$PYTHON_EXE' -c \"from fastapi.testclient import TestClient; from plannededucation.api.main import app; c = TestClient(app); r = c.get('/health'); assert r.status_code == 200\""
fi

# ==============================================================================
# Step 9b: Generate Install Manifest (for safe uninstall)
# ==============================================================================
print_header "Step 9b: Generating Install Manifest"

INSTALL_MANIFEST="$LOG_DIR/install_manifest.txt"
if [[ -d "$INSTALL_DIR" ]]; then
    print_info "Recording installed files for safe uninstall..."
    find "$INSTALL_DIR" \( -type f -o -type l \) 2>/dev/null | sort > "$INSTALL_MANIFEST"
    MANIFEST_COUNT=$(wc -l < "$INSTALL_MANIFEST" 2>/dev/null || echo 0)
    print_success "Install manifest written to: $INSTALL_MANIFEST ($MANIFEST_COUNT files tracked)"
else
    print_warning "Could not generate install manifest - installation directory not found"
    print_info "Uninstall will fall back to removing the entire directory."
fi

# ==============================================================================
# Final Summary
# ==============================================================================
print_header "Installation Complete!"

echo -e "${BOLD}Verification Results:${RESET} ${GREEN}$TESTS_PASSED passed${RESET}, ${RED}$TESTS_FAILED failed${RESET}"
echo ""
echo -e "${CYAN}============================================================${RESET}"
echo -e "${BOLD}${GREEN}  PlannedEducation is installed and ready!${RESET}"
echo -e "${CYAN}============================================================${RESET}"
echo -e "  ${BOLD}Install Dir:${RESET}    $INSTALL_DIR"
echo -e "  ${BOLD}School Name:${RESET}    $SCHOOL_NAME"
echo -e "  ${BOLD}Backend API:${RESET}    http://$DOMAIN:$API_PORT"
echo -e "  ${BOLD}API Docs:${RESET}       http://$DOMAIN:$API_PORT/docs"
echo -e "  ${BOLD}Frontend App:${RESET}   http://$DOMAIN:$FRONTEND_PORT"
echo -e "  ${BOLD}Admin Email:${RESET}    $ADMIN_EMAIL"
echo -e "  ${BOLD}Admin Password:${RESET} $ADMIN_PASS"
echo -e "  ${BOLD}Diagnostic Logs:${RESET}"
echo -e "    - Install Log:        $INSTALL_DIR/logs/install.log"
echo -e "    - Install Error Log:  $INSTALL_DIR/logs/install_error.log"
echo -e "    - Backend Log:        $INSTALL_DIR/logs/backend.log"
echo -e "    - Backend Error Log:  $INSTALL_DIR/logs/backend_error.log"
echo -e "    - Frontend Log:       $INSTALL_DIR/logs/frontend.log"
echo -e "    - Frontend Error Log: $INSTALL_DIR/logs/frontend_error.log"
echo -e "${CYAN}============================================================${RESET}"
echo ""
print_info "Important Management Commands:"
echo "  1. Start Platform: $INSTALL_DIR/start_all.sh"
echo "  2. Verify Status:  $INSTALL_DIR/verify.sh"
echo "  3. Stop Platform:  $INSTALL_DIR/stop_all.sh"
echo "  4. Uninstaller:    $INSTALL_DIR/uninstall.sh"
echo ""
echo "  Log in with your Superadmin credentials and change your password."
echo ""
print_success "Thank you for using PlannedEducation!"