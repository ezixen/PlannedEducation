#!/bin/bash
#
# PlannedEducation Uninstaller for Linux
# Carefully removes only the PlannedEducation platform from the server.
# Does NOT touch other system files or unrelated applications.
#
# AI AGENT CONTRACT: before running with AUTO_CONFIRM=true, the agent MUST STOP AND ASK
# the human to confirm (1) the exact INSTALL_DIR to delete (data loss!) and (2) whether any
# external dependencies (Python, Node.js, PostgreSQL, Redis, Docker, Git) should be removed.
# There is NO "remove all dependencies" option; with AUTO_CONFIRM all dependencies are kept.
# Logs of the installation live in $INSTALL_DIR/logs/ and are deleted with it - copy them
# first if they are needed for diagnosis.
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_INSTALL_DIR="/opt/plannededucation"
if [[ -f "$SCRIPT_DIR/plannededucation.db" || -d "$SCRIPT_DIR/src/plannededucation" || -f "$SCRIPT_DIR/.env" ]]; then
    DEFAULT_INSTALL_DIR="$SCRIPT_DIR"
fi

INSTALL_DIR="${INSTALL_DIR:-${1:-}}"
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
    read -r -p "$message (y/N): " response
    [[ "$response" =~ ^[Yy]$ ]]
}

# Check for root
if [[ $EUID -ne 0 ]]; then
    write_warning "Not running as root. Some operations may fail."
    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        read -r -p "Continue anyway? (y/N): " confirm
        [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
    fi
fi

write_header "PlannedEducation Uninstaller (Linux)"

# Verify or prompt for installation directory
if [[ -z "$INSTALL_DIR" ]]; then
    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        echo -e "${CYAN}Default installation directory: $DEFAULT_INSTALL_DIR${NC}"
        read -r -p "Enter installation directory to remove (press Enter for default '$DEFAULT_INSTALL_DIR'): " user_dir
        if [[ -n "$user_dir" ]]; then
            INSTALL_DIR="$user_dir"
        else
            INSTALL_DIR="$DEFAULT_INSTALL_DIR"
        fi
    else
        INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    fi
fi

if [[ ! -d "$INSTALL_DIR" ]]; then
    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        while [[ ! -d "$INSTALL_DIR" ]]; do
            write_warning "Installation directory not found: $INSTALL_DIR"
            read -r -p "Enter a valid installation directory to remove (or type 'exit' to cancel): " user_dir
            if [[ -z "$user_dir" || "$user_dir" == "exit" ]]; then
                write_error "Uninstallation aborted."
                exit 1
            fi
            INSTALL_DIR="$user_dir"
        done
    else
        write_error "Installation directory not found: $INSTALL_DIR"
        write_info "Please specify the correct path with INSTALL_DIR environment variable or parameter"
        exit 1
    fi
fi

write_success "Found PlannedEducation at: $INSTALL_DIR"

# Step 1: Stop running processes
write_header "Step 1: Stopping Running Processes"

# Protect ourselves and every ancestor (the invoking shell / agent wrapper usually has
# INSTALL_DIR in its own command line and must not be killed).
PROTECTED_PIDS=" "
cur=$$
while [[ -n "$cur" && "$cur" -gt 1 ]]; do
    PROTECTED_PIDS="$PROTECTED_PIDS$cur "
    cur=$(awk '/^PPid:/ {print $2}' "/proc/$cur/status" 2>/dev/null || true)
done

# Stop only platform runtimes whose cmdline or cwd is inside INSTALL_DIR
PIDS_TO_KILL=""
for pid_dir in /proc/[0-9]*; do
    pid="${pid_dir#/proc/}"
    [[ "$PROTECTED_PIDS" == *" $pid "* ]] && continue
    comm=$(cat "$pid_dir/comm" 2>/dev/null || true)
    case "$comm" in
        python*|uvicorn*|node|npm*|vite*|esbuild) ;;
        *) continue ;;
    esac
    cwd_target=$(readlink -f "$pid_dir/cwd" 2>/dev/null || true)
    cmdline=$(tr '\0' ' ' < "$pid_dir/cmdline" 2>/dev/null || true)
    if [[ ( -n "$cwd_target" && "$cwd_target" == "$INSTALL_DIR"* ) || "$cmdline" == *"$INSTALL_DIR"* ]]; then
        PIDS_TO_KILL="$PIDS_TO_KILL $pid"
    fi
done

PIDS_TO_KILL=$(echo "$PIDS_TO_KILL" | xargs || true)
if [[ -n "$PIDS_TO_KILL" ]]; then
    write_info "Stopping platform processes ($PIDS_TO_KILL)..."
    # shellcheck disable=SC2086
    kill -9 $PIDS_TO_KILL 2>/dev/null || true
    write_success "Stopped platform processes"
else
    write_info "No platform processes running from $INSTALL_DIR"
fi

# Step 2: Remove systemd services
write_header "Step 2: Removing Systemd Services"

SERVICE_NAME="plannededucation-backend"
if systemctl list-unit-files 2>/dev/null | grep -q "$SERVICE_NAME"; then
    write_info "Removing systemd service: $SERVICE_NAME"
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/$SERVICE_NAME.service" 2>/dev/null || true
    sudo systemctl daemon-reload 2>/dev/null || true
    write_success "Removed systemd service: $SERVICE_NAME"
else
    write_info "No systemd service found: $SERVICE_NAME"
fi

# Remove launcher scripts
for script_name in "start_backend.sh" "start_frontend.sh"; do
    SERVICE_SCRIPT="$INSTALL_DIR/$script_name"
    if [[ -f "$SERVICE_SCRIPT" ]]; then
        rm -f "$SERVICE_SCRIPT"
        write_success "Removed service script: $script_name"
    fi
done

# Step 3: Ask about external dependencies (one-by-one only, no remove-all)
write_header "Step 3: External Dependencies"

DEP_ORDER=("Python" "Node.js" "PostgreSQL" "Redis" "Docker" "Git")

declare -A DEP_CHECKS=(
    ["Python"]="python3 --version"
    ["Node.js"]="node --version"
    ["PostgreSQL"]="psql --version"
    ["Redis"]="redis-cli --version"
    ["Docker"]="docker --version"
    ["Git"]="git --version"
)

declare -A DEP_REMOVE_CMDS=(
    ["Python"]="sudo apt-get remove -y python3 python3-pip 2>/dev/null || sudo yum remove -y python3 python3-pip 2>/dev/null || true"
    ["Node.js"]="sudo apt-get remove -y nodejs npm 2>/dev/null || sudo yum remove -y nodejs npm 2>/dev/null || true"
    ["PostgreSQL"]="sudo apt-get remove -y postgresql postgresql-contrib 2>/dev/null || sudo yum remove -y postgresql postgresql-contrib 2>/dev/null || true"
    ["Redis"]="sudo apt-get remove -y redis-server 2>/dev/null || sudo yum remove -y redis 2>/dev/null || true"
    ["Docker"]="sudo apt-get remove -y docker.io docker-compose 2>/dev/null || sudo yum remove -y docker docker-compose 2>/dev/null || true"
    ["Git"]="sudo apt-get remove -y git 2>/dev/null || sudo yum remove -y git 2>/dev/null || true"
)

write_info "The following external dependencies may be used by PlannedEducation or other applications:"
INSTALLED_DEPS=()
for dep_name in "${DEP_ORDER[@]}"; do
    cmd_bin="${DEP_CHECKS[$dep_name]%% *}"
    if command -v "$cmd_bin" &>/dev/null; then
        echo -e "  - ${GREEN}${dep_name} [INSTALLED]${NC}"
        INSTALLED_DEPS+=("$dep_name")
    else
        echo -e "  - ${YELLOW}${dep_name} [Not installed]${NC}"
    fi
done
echo ""
DEPS_TO_REMOVE=()

if [[ "$AUTO_CONFIRM" != "true" && ${#INSTALLED_DEPS[@]} -gt 0 ]]; then
    if confirm_action "Do you want to remove any external dependencies?"; then
        for dep_name in "${INSTALLED_DEPS[@]}"; do
            if confirm_action "Remove $dep_name? (y=remove, N=keep)"; then
                DEPS_TO_REMOVE+=("$dep_name")
            else
                write_info "Keeping $dep_name"
            fi
        done
    else
        write_info "Keeping all external dependencies"
    fi
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

INSTALL_MANIFEST="$INSTALL_DIR/logs/install_manifest.txt"
MANIFEST_EXISTS=false
if [[ -f "$INSTALL_MANIFEST" ]]; then
    MANIFEST_EXISTS=true
    write_info "Install manifest found at: $INSTALL_MANIFEST"
else
    write_warning "Install manifest not found at: $INSTALL_MANIFEST"
    write_warning "This means uninstall cannot determine which files were"
    write_warning "installed by the installer vs. added by you afterward."
    write_warning ""
    write_warning "If you proceed, ALL files in $INSTALL_DIR will be deleted,"
    write_warning "including any files you added after installation."
    if [[ "$AUTO_CONFIRM" != "true" ]]; then
        read -r -p "Are you ABSOLUTELY sure you want to delete ALL files in $INSTALL_DIR? (y/N): " confirm_all
        [[ "$confirm_all" =~ ^[Yy]$ ]] || { write_info "Uninstall cancelled by user"; exit 0; }
    fi
fi

# Run stop_all.sh if present to release any bound ports
STOP_SCRIPT="$INSTALL_DIR/stop_all.sh"
if [[ -f "$STOP_SCRIPT" ]]; then
    write_info "Running stop_all.sh to release bound ports..."
    bash "$STOP_SCRIPT" 2>/dev/null || true
fi

# Move working directory outside $INSTALL_DIR so the folder is not locked
ORIG_DIR="$(pwd)"
cd /tmp 2>/dev/null || cd ~ 2>/dev/null || true

# Stop any remaining processes executing from inside the installation directory
for pid_dir in /proc/[0-9]*; do
    pid="${pid_dir#/proc/}"
    [[ "$PROTECTED_PIDS" == *" $pid "* ]] && continue
    comm=$(cat "$pid_dir/comm" 2>/dev/null || true)
    case "$comm" in
        python*|uvicorn*|node|npm*|vite*|esbuild) ;;
        *) continue ;;
    esac
    exe_path=$(readlink -f "$pid_dir/exe" 2>/dev/null || true)
    cmdline=$(tr '\0' ' ' < "$pid_dir/cmdline" 2>/dev/null || true)
    if [[ ( -n "$exe_path" && "$exe_path" == "$INSTALL_DIR"* ) || "$cmdline" == *"$INSTALL_DIR"* ]]; then
        kill -9 "$pid" 2>/dev/null || true
    fi
done

if [[ "$MANIFEST_EXISTS" == "true" ]]; then
    # Targeted removal: only remove files listed in the install manifest
    write_info "Using install manifest for targeted removal..."
    REMOVED_COUNT=0
    while IFS= read -r file_path; do
        file_path="${file_path#"${file_path%%[![:space:]]*}"}"  # trim leading whitespace
        file_path="${file_path%"${file_path##*[![:space:]]}"}"  # trim trailing whitespace
        if [[ -n "$file_path" && -f "$file_path" ]]; then
            if rm -f "$file_path" 2>/dev/null; then
                REMOVED_COUNT=$((REMOVED_COUNT + 1))
            fi
        fi
    done < "$INSTALL_MANIFEST"
    # Remove the manifest itself
    rm -f "$INSTALL_MANIFEST" 2>/dev/null || true
    write_success "Removed $REMOVED_COUNT installed files via manifest"
    write_info "Any files you added to $INSTALL_DIR after installation have been preserved"
else
    # Full removal: remove everything (no manifest to guide us)
    write_warning "No manifest found - removing ALL files in $INSTALL_DIR"
    if rm -rf "$INSTALL_DIR" 2>/dev/null || sudo -n rm -rf "$INSTALL_DIR" 2>/dev/null; then
        write_success "Successfully removed: $INSTALL_DIR"
    else
        write_error "Failed to remove $INSTALL_DIR"
        write_info "You may need to close applications using files in this directory and try again"
        cd "$ORIG_DIR" 2>/dev/null || true
        exit 1
    fi
fi

# Clean up empty subdirectories (manifest-based removal preserves user-added files)
if [[ "$MANIFEST_EXISTS" == "true" && -d "$INSTALL_DIR" ]]; then
    write_info "Cleaning up empty subdirectories..."
    # Remove empty directories from deepest to shallowest
    find "$INSTALL_DIR" -type d -empty -delete 2>/dev/null || true
    # Check if root dir is now empty
    if [[ -z "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
        rmdir "$INSTALL_DIR" 2>/dev/null || true
        write_success "Removed empty installation directory: $INSTALL_DIR"
    else
        REMAINING=$(find "$INSTALL_DIR" -mindepth 1 2>/dev/null | head -5)
        write_info "Directory still contains preserved user-added files: $INSTALL_DIR"
        echo "$REMAINING"
    fi
fi

cd "$ORIG_DIR" 2>/dev/null || true

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
fi

echo ""
write_info "To reinstall PlannedEducation, run: install.sh"
echo ""
