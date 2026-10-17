#!/bin/bash
#
# PlannedEducation Uninstaller for Linux
# Carefully removes only the PlannedEducation platform from the server.
# Does NOT touch other system files or unrelated applications.
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

INSTALL_DIR="${INSTALL_DIR:-/opt/plannededucation}"
REMOVE_ALL_DEPS="${REMOVE_ALL_DEPS:-false}"
AUTO_CONFIRM="${AUTO_CONFIRM:-false}"

write_header() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
}

write_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

write_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

write_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

write_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

confirm_action() {
    local message="$1"
    if [[ "$AUTO_CONFIRM" == "true" ]]; then
        return 0
    fi
    read -p "$message (y/N): " response
    [[ "$response" =~ ^[Yy]$ ]]
}

# Check for root
if [[ $EUID -ne 0 ]]; then
    write_warning "Not running as root. Some operations may fail."
    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        read -p "Continue anyway? (y/N): " confirm
        [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
    fi
fi

write_header "PlannedEducation Uninstaller (Linux)"

# Verify installation directory exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    write_error "Installation directory not found: $INSTALL_DIR"
    write_info "Please specify the correct path with INSTALL_DIR environment variable"
    exit 1
fi

write_success "Found PlannedEducation at: $INSTALL_DIR"

# Step 1: Stop running processes
write_header "Step 1: Stopping Running Processes"

# Stop backend API processes
API_PIDS=$(pgrep -f "python.*uvicorn.*$INSTALL_DIR" 2>/dev/null || true)
if [[ -n "$API_PIDS" ]]; then
    write_info "Stopping backend API processes..."
    echo "$API_PIDS" | xargs kill -9 2>/dev/null || true
    write_success "Stopped backend API processes"
else
    write_info "No backend API processes running"
fi

# Stop frontend processes
NODE_PIDS=$(pgrep -f "vite.*$INSTALL_DIR" 2>/dev/null || true)
if [[ -n "$NODE_PIDS" ]]; then
    write_info "Stopping frontend processes..."
    echo "$NODE_PIDS" | xargs kill -9 2>/dev/null || true
    write_success "Stopped frontend processes"
else
    write_info "No frontend processes running"
fi

# Stop any remaining python processes related to the install
PY_PIDS=$(pgrep -f "python.*$INSTALL_DIR" 2>/dev/null || true)
if [[ -n "$PY_PIDS" ]]; then
    write_info "Stopping remaining Python processes..."
    echo "$PY_PIDS" | xargs kill -9 2>/dev/null || true
    write_success "Stopped remaining Python processes"
fi

# Step 2: Remove systemd services
write_header "Step 2: Removing Systemd Services"

SERVICE_NAME="plannededucation-backend"
if systemctl list-unit-files 2>/dev/null | grep -q "$SERVICE_NAME"; then
    write_info "Removing systemd service: $SERVICE_NAME"
    systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload 2>/dev/null || true
    write_success "Removed systemd service: $SERVICE_NAME"
else
    write_info "No systemd service found: $SERVICE_NAME"
fi

# Remove service scripts
SERVICE_SCRIPT="$INSTALL_DIR/start_backend.sh"
if [[ -f "$SERVICE_SCRIPT" ]]; then
    rm -f "$SERVICE_SCRIPT"
    write_success "Removed service script: start_backend.sh"
fi

# Step 3: Ask about external dependencies
write_header "Step 3: External Dependencies"

REMOVE_DEPS=false
if [[ "$REMOVE_ALL_DEPS" == "true" ]]; then
    REMOVE_DEPS=true
elif [[ "$AUTO_CONFIRM" != "true" ]]; then
    if confirm_action "Do you want to remove all external dependencies (Python, Node.js, PostgreSQL, Redis, Docker, Git)?"; then
        REMOVE_DEPS=true
    fi
fi

DEPS_TO_REMOVE=()

if [[ "$REMOVE_DEPS" == "true" ]]; then
    REMOVE_ONE_BY_ONE=false
    if [[ "$AUTO_CONFIRM" != "true" ]] && confirm_action "Do you want to decide for each dependency one by one (keep/remove)?"; then
        REMOVE_ONE_BY_ONE=true
    fi

    # Check which external dependencies are installed
    declare -A DEP_CHECKS=(
        ["Python"]="python3 --version"
        ["Node.js"]="node --version"
        ["PostgreSQL"]="psql --version"
        ["Redis"]="redis-cli --version"
        ["Docker"]="docker --version"
        ["Git"]="git --version"
    )

    declare -A DEP_REMOVE_CMDS=(
        ["Python"]="apt-get remove -y python3 python3-pip 2>/dev/null || yum remove -y python3 python3-pip 2>/dev/null || true"
        ["Node.js"]="apt-get remove -y nodejs npm 2>/dev/null || yum remove -y nodejs npm 2>/dev/null || true"
        ["PostgreSQL"]="apt-get remove -y postgresql postgresql-contrib 2>/dev/null || yum remove -y postgresql postgresql-contrib 2>/dev/null || true"
        ["Redis"]="apt-get remove -y redis-server 2>/dev/null || yum remove -y redis 2>/dev/null || true"
        ["Docker"]="apt-get remove -y docker.io docker-compose 2>/dev/null || yum remove -y docker docker-compose 2>/dev/null || true"
        ["Git"]="apt-get remove -y git 2>/dev/null || yum remove -y git 2>/dev/null || true"
    )

    for dep_name in "${!DEP_CHECKS[@]}"; do
        if command -v "${DEP_CHECKS[$dep_name]%% *}" &>/dev/null; then
            if [[ "$REMOVE_ONE_BY_ONE" == "true" ]]; then
                read -p "Keep $dep_name? (y=keep, n=remove): " keep_dep
                if [[ ! "$keep_dep" =~ ^[Yy]$ ]]; then
                    DEPS_TO_REMOVE+=("$dep_name")
                else
                    write_info "Keeping $dep_name"
                fi
            else
                DEPS_TO_REMOVE+=("$dep_name")
            fi
        else
            write_info "$dep_name: Not installed, skipping"
        fi
    done
else
    write_info "Keeping all external dependencies"
fi

# Step 4: Confirm removal of platform
write_header "Step 4: Confirm Platform Removal"

write_warning "This will PERMANENTLY DELETE the following:"
echo "  📁 $INSTALL_DIR"
echo "  🗄️  All databases (*.db files)"
echo "  🔐 All secrets and environment files"
echo "  📋 All logs and cache files"
echo ""
write_warning "This action CANNOT be undone!"

if ! confirm_action "Do you want to proceed with removing PlannedEducation from $INSTALL_DIR?"; then
    write_info "Uninstall cancelled by user"
    exit 0
fi

# Step 5: Remove the platform
write_header "Step 5: Removing PlannedEducation Platform"

# Kill any processes using files in the directory
fuser -k "$INSTALL_DIR" 2>/dev/null || true

# Remove the directory
if rm -rf "$INSTALL_DIR" 2>/dev/null; then
    write_success "Successfully removed: $INSTALL_DIR"
else
    write_error "Failed to remove $INSTALL_DIR"
    write_info "You may need to close applications using files in this directory and try again"
    exit 1
fi

# Step 6: Remove external dependencies (if requested)
if [[ ${#DEPS_TO_REMOVE[@]} -gt 0 ]]; then
    write_header "Step 6: Removing External Dependencies"

    for dep in "${DEPS_TO_REMOVE[@]}"; do
        write_info "Removing $dep..."
        eval "${DEP_REMOVE_CMDS[$dep]}" 2>/dev/null || true
        if command -v "${DEP_CHECKS[$dep]%% *}" &>/dev/null; then
            write_warning "Failed to remove $dep automatically"
            write_info "Please remove $dep manually"
        else
            write_success "Removed $dep"
        fi
    done
fi

# Step 7: Summary
write_header "Uninstall Complete"

write_success "PlannedEducation has been removed from: $INSTALL_DIR"
if [[ ${#DEPS_TO_REMOVE[@]} -gt 0 ]]; then
    write_success "Removed ${#DEPS_TO_REMOVE[@]} external dependency(ies)"
else
    write_info "All external dependencies were kept"
}

echo ""
write_info "To reinstall PlannedEducation, run: install.sh"
echo ""
