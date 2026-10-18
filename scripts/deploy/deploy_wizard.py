#!/usr/bin/env python3
"""
PlannedEducation - Guided Deployment Wizard
Interactive setup wizard for school deployment (Native or Docker Compose).
Run: python deploy_wizard.py
"""

import os
import sys
import subprocess
import secrets
import shutil
import getpass
import platform
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_step(step: int, total: int, text: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}[Step {step}/{total}] {text}{Colors.RESET}")

def print_success(text: str):
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def run_cmd(cmd, cwd: Optional[Path] = None, capture: bool = True, shell: bool = False) -> tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr) with cross-platform binary resolution"""
    try:
        if isinstance(cmd, list) and not shell:
            # Resolve binary path on Windows / Linux via shutil.which
            exe = shutil.which(cmd[0])
            if exe:
                cmd = [exe] + cmd[1:]
        result = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True, timeout=300, shell=shell)
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def get_docker_compose_cmd() -> Optional[list[str]]:
    """Determine whether 'docker compose' or legacy 'docker-compose' is available"""
    if shutil.which("docker"):
        code, out, _ = run_cmd(["docker", "compose", "version"])
        if code == 0:
            return ["docker", "compose"]
    if shutil.which("docker-compose"):
        code, out, _ = run_cmd(["docker-compose", "--version"])
        if code == 0:
            return ["docker-compose"]
    return None

def check_requirements(mode: str) -> bool:
    """Check required dependencies for the selected deployment mode"""
    print_step(1, 8, "Checking system requirements...")
    
    # Check Python (required for both modes)
    python_ok = False
    for py_cmd in [sys.executable, "python3", "python"]:
        code, out, _ = run_cmd([py_cmd, "--version"])
        if code == 0:
            version = out.strip().split('\n')[0]
            print_success(f"Python: {version}")
            python_ok = True
            break
    if not python_ok:
        print_error("Python: NOT FOUND. Python 3.12+ is required.")
        return False

    # Check Git
    code, out, _ = run_cmd(["git", "--version"])
    if code == 0:
        version = out.strip().split('\n')[0]
        print_success(f"Git: {version}")
    else:
        print_warning("Git: Not found in PATH. Continuing anyway.")

    if mode == "docker":
        # Check Docker engine
        code, out, _ = run_cmd(["docker", "--version"])
        if code == 0:
            print_success(f"Docker: {out.strip().split('\n')[0]}")
        else:
            print_error("Docker: NOT FOUND.")
            print_warning("Install Docker Desktop or Docker Engine: https://docs.docker.com/engine/install/")
            return False

        # Check Docker Compose
        compose_cmd = get_docker_compose_cmd()
        if compose_cmd:
            code, out, _ = run_cmd(compose_cmd + ["version"] if compose_cmd[0] == "docker" else compose_cmd + ["--version"])
            print_success(f"Docker Compose: {' '.join(compose_cmd)} ({out.strip().splitlines()[0] if out else 'OK'})")
        else:
            print_error("Docker Compose: NOT FOUND.")
            print_warning("Please install Docker Compose plugin: https://docs.docker.com/compose/install/")
            return False
    else:
        # Native mode checks
        print_success("Native Mode: Zero container dependencies required.")
        # Check Node.js if frontend needs building
        code, out, _ = run_cmd(["node", "--version"])
        if code == 0:
            print_success(f"Node.js: {out.strip()}")
        else:
            print_warning("Node.js: Not found in PATH. Pre-built frontend will be used if available.")

    print_success("Requirements check passed!")
    return True

def get_user_input(prompt: str, default: str = "", required: bool = False, secret: bool = False) -> str:
    """Get user input with optional default and password masking"""
    while True:
        display_prompt = f"{prompt} [{default}]: " if default else f"{prompt}: "
        if secret:
            value = getpass.getpass(display_prompt)
        else:
            value = input(display_prompt).strip()
        
        if not value and default:
            return default
        if not value and required:
            print_error("This field is required!")
            continue
        return value

def generate_keys() -> tuple[str, str]:
    """Generate cryptographically secure JWT and Fernet keys"""
    jwt_key = secrets.token_hex(64)
    fernet_key = Fernet.generate_key().decode()
    return jwt_key, fernet_key

def setup_env_file(project_dir: Path, mode: str) -> bool:
    """Interactive environment (.env) configuration"""
    print_step(2, 8, "Configuring environment (.env)...")
    
    env_path = project_dir / ".env"
    env_example = project_dir / ".env.example"
    
    env_content = ""
    if env_example.exists():
        with open(env_example, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    print(f"\n{Colors.YELLOW}Configuring required credentials and domain settings.{Colors.RESET}")
    print("Press Enter to accept defaults.\n")
    
    # Generate cryptographic keys
    jwt_key, fernet_key = generate_keys()
    print_success("Generated JWT_SECRET_KEY (64-byte hex)")
    print_success("Generated AI_KEY_MASTER_SECRET (Fernet 32-byte urlsafe base64)")
    
    # Domain configuration
    domain = get_user_input("School domain (e.g. yourschool.edu or localhost)", "localhost", required=True)
    
    # Database configuration based on mode
    if mode == "native":
        print(f"\n{Colors.BOLD}Database Options (Native Mode):{Colors.RESET}")
        print("  1) SQLite (Zero configuration, file-based, fast)")
        print("  2) PostgreSQL (Self-hosted or external PostgreSQL server)")
        db_choice = get_user_input("Select database [1/2]", "1")
        if db_choice == "2":
            db_url = get_user_input(
                "PostgreSQL Database URL",
                "postgresql+psycopg://postgres:changeme@localhost:5432/plannededucation"
            )
        else:
            db_url = "sqlite:///./plannededucation.db"
            print_success(f"Using local SQLite database: {db_url}")
    else:
        # Docker Compose mode
        pg_password = secrets.token_urlsafe(24)
        db_url = f"postgresql://postgres:{pg_password}@postgres:5432/plannededucation"
    
    # Optional Google OAuth
    print(f"\n{Colors.BOLD}Optional: Google OAuth2 (for 'Login with Google'){Colors.RESET}")
    google_id = get_user_input("Google Client ID (leave blank to skip)", "")
    google_secret = ""
    if google_id:
        google_secret = get_user_input("Google Client Secret", "", secret=True)
    
    # Build or update .env lines
    lines = env_content.splitlines() if env_content else []
    settings = {
        'PLANNED_EDUCATION_ENV': 'production',
        'JWT_SECRET_KEY': jwt_key,
        'AI_KEY_MASTER_SECRET': fernet_key,
        'DATABASE_URL': db_url,
        'GOOGLE_CLIENT_ID': google_id or 'localhost',
        'GOOGLE_CLIENT_SECRET': google_secret,
        'ALLOWED_HOSTS': domain,
        'CORS_ORIGINS': f"http://{domain}:5173" if domain == "localhost" else f"https://{domain}",
        'WEBAUTHN_RP_ID': domain,
        'WEBAUTHN_ORIGIN': f"http://{domain}:5173" if domain == "localhost" else f"https://{domain}"
    }
    
    if mode == "docker":
        settings['POSTGRES_PASSWORD'] = pg_password
    
    output_lines = []
    seen = set()
    for line in lines:
        matched = False
        for key, val in settings.items():
            if line.startswith(f"{key}="):
                output_lines.append(f"{key}={val}")
                seen.add(key)
                matched = True
                break
        if not matched:
            output_lines.append(line)
            
    for key, val in settings.items():
        if key not in seen:
            output_lines.append(f"{key}={val}")
            
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines) + '\n')
        
    print_success(f".env configured at {env_path}")
    return True

def start_platform(project_dir: Path, mode: str) -> bool:
    """Build and start the application services"""
    print_step(3, 8, "Starting platform services...")
    
    if mode == "docker":
        compose_cmd = get_docker_compose_cmd() or ["docker", "compose"]
        cmd_str = " ".join(compose_cmd) + " up -d --build"
        print(f"{Colors.CYAN}Building and starting Docker containers ({cmd_str})...{Colors.RESET}")
        
        code, out, err = run_cmd(cmd_str, cwd=project_dir, capture=False, shell=True)
        if code != 0:
            print_error(f"Docker build failed: {err}")
            return False
            
        print_success("Docker containers built and running")
        print(f"{Colors.CYAN}Waiting 15s for services to stabilize...{Colors.RESET}")
        import time
        time.sleep(15)
        
        # Health check using urllib inside python container
        health_cmd = f"{' '.join(compose_cmd)} exec -T backend python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\""
        code, _, _ = run_cmd(health_cmd, cwd=project_dir, shell=True)
        if code == 0:
            print_success("Backend health check: OK")
        else:
            print_warning("Backend health check did not respond immediately, continuing...")
    else:
        # Native mode: verify frontend build
        dist_dir = project_dir / "web" / "apps" / "portal" / "dist"
        if not dist_dir.exists():
            print(f"{Colors.CYAN}Building frontend assets (npm run build)...{Colors.RESET}")
            portal_dir = project_dir / "web" / "apps" / "portal"
            code, _, err = run_cmd("npm run build", cwd=portal_dir, shell=True)
            if code == 0:
                print_success("Frontend build completed")
            else:
                print_warning(f"Frontend build note: {err}")
        else:
            print_success("Frontend pre-built distribution directory verified")
            
    return True

def init_database(project_dir: Path, mode: str) -> bool:
    """Initialize database tables via SQLAlchemy ORM"""
    print_step(4, 8, "Initializing database tables...")
    
    if mode == "docker":
        compose_cmd = get_docker_compose_cmd() or ["docker", "compose"]
        cmd = f"{' '.join(compose_cmd)} exec -T backend python -c \"from src.plannededucation.api.database import Base, engine; from src.plannededucation.api import models; Base.metadata.create_all(bind=engine); print('Database initialized')\""
        code, out, err = run_cmd(cmd, cwd=project_dir, shell=True)
    else:
        # In Native mode, invoke directly with current python
        python_exe = sys.executable
        py_code = "from src.plannededucation.api.database import Base, engine; from src.plannededucation.api import models; Base.metadata.create_all(bind=engine); print('Database initialized')"
        code, out, err = run_cmd([python_exe, "-c", py_code], cwd=project_dir)
        
    if code == 0:
        print_success("Database schema initialized")
        return True
    print_error(f"Database initialization failed: {err}")
    return False

def create_admin_user(project_dir: Path, mode: str) -> bool:
    """Create initial administrator user"""
    print_step(5, 8, "Creating Administrator account...")
    
    email = get_user_input("Admin email", "admin@yourschool.edu", required=True)
    username = get_user_input("Admin username", "admin", required=True)
    full_name = get_user_input("Admin full name", "School Administrator", required=True)
    password = get_user_input("Admin password (min 8 chars)", "ChangeMe123!", required=True, secret=True)
    
    email_esc = email.replace('"', '\\"').replace("'", "\\'")
    user_esc = username.replace('"', '\\"').replace("'", "\\'")
    name_esc = full_name.replace('"', '\\"').replace("'", "\\'")
    pass_esc = password.replace('"', '\\"').replace("'", "\\'")
    
    py_code = (
        f"from src.plannededucation.api.database import SessionLocal; "
        f"from src.plannededucation.api.models import User; "
        f"from src.plannededucation.api.routes_auth import get_password_hash; "
        f"db = SessionLocal(); "
        f"admin = User(email='{email_esc}', username='{user_esc}', full_name='{name_esc}', "
        f"hashed_password=get_password_hash('{pass_esc}'), role='admin', is_admin=True, is_active=True); "
        f"db.add(admin); db.commit(); print('Admin created: {email_esc}')"
    )
    
    if mode == "docker":
        compose_cmd = get_docker_compose_cmd() or ["docker", "compose"]
        cmd = f"{' '.join(compose_cmd)} exec -T backend python -c \"{py_code}\""
        code, out, err = run_cmd(cmd, cwd=project_dir, shell=True)
    else:
        python_exe = sys.executable
        code, out, err = run_cmd([python_exe, "-c", py_code], cwd=project_dir)
        
    if code == 0:
        print_success(f"Administrator account created: {email}")
        print_warning("IMPORTANT: Log in and change your password immediately after setup!")
        return True
        
    print_error(f"Admin creation failed: {err}")
    return False

def verify_deployment(project_dir: Path, mode: str) -> bool:
    """Verify service endpoints and platform health"""
    print_step(6, 8, "Verifying deployment...")
    
    if mode == "docker":
        compose_cmd = get_docker_compose_cmd() or ["docker", "compose"]
        checks = [
            ("Backend API", "curl -f http://localhost:8000/health"),
            ("Frontend HTTP", "curl -f http://localhost:80/"),
            ("PostgreSQL Database", f"{' '.join(compose_cmd)} exec -T postgres pg_isready -U postgres"),
            ("Redis Cache", f"{' '.join(compose_cmd)} exec -T redis redis-cli ping"),
        ]
    else:
        checks = [
            ("Backend API Health", "curl -f http://localhost:8000/health"),
        ]
        
    all_ok = True
    for name, cmd in checks:
        code, out, err = run_cmd(cmd, cwd=project_dir, shell=True)
        if code == 0:
            print_success(f"{name}: OK")
        else:
            print_warning(f"{name}: Service check not yet responding (may still be starting)")
            all_ok = False
            
    return all_ok

def show_next_steps(project_dir: Path, domain: str, mode: str):
    """Display final instructions, access URLs, and management commands"""
    print_step(7, 8, "Deployment Complete! 🎉")
    
    protocol = "https" if domain != "localhost" else "http"
    port = "" if domain != "localhost" else (":80" if mode == "docker" else ":5173")
    url = f"{protocol}://{domain}{port}"
    
    print(f"""
{Colors.GREEN}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║             PLANNEDEDUCATION DEPLOYED SUCCESSFULLY!       ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.BOLD}Platform Access URLs:{Colors.RESET}
  🌐 Web Portal:    {url}
  📚 REST API Docs: http://{domain}:8000/docs
  ❤️  Health Check:  http://{domain}:8000/health

{Colors.BOLD}First Administrator Login:{Colors.RESET}
  1. Open {url} in your browser
  2. Sign in with the administrator credentials created in Step 5
  3. {Colors.RED}Change your temporary password{Colors.RESET} in Settings → Security

{Colors.BOLD}Useful Service Commands:{Colors.RESET}""")

    if mode == "docker":
        print("""  View logs:     docker compose logs -f backend
  Update:        git pull && docker compose build --no-cache && docker compose up -d
  Restart:       docker compose restart
  Stop:          docker compose down""")
    else:
        print(f"""  Start Backend: python -m uvicorn src.plannededucation.api.main:app --host 0.0.0.0 --port 8000
  Run Frontend:  cd web/apps/portal && npm run preview (or host 'dist/' via Nginx/Caddy/IIS)
  Update:        git pull && pip install -r src/requirements.txt && cd web/apps/portal && npm run build""")

    print(f"""
{Colors.CYAN}Need guidance? Refer to docs/admin/DEPLOYMENT_GUIDE.md or docs/admin/INSTALL_COMPATIBILITY.md{Colors.RESET}
""")

def main():
    print_header("PlannedEducation - Guided Deployment Wizard")
    print("Welcome! This wizard deploys PlannedEducation for your school or organization.\n")
    
    # Detect project root whether run from repo root or scripts/deploy/
    script_dir = Path(__file__).resolve().parent
    candidates = [Path.cwd(), script_dir.parent.parent, script_dir.parent]
    project_dir = Path.cwd()
    for c in candidates:
        if (c / "src" / "plannededucation").exists():
            project_dir = c
            break

    if not (project_dir / "src" / "plannededucation").exists():
        print_error("PlannedEducation source directory not found!")
        print("Please run this script from the root directory of PlannedEducation.")
        sys.exit(1)
        
    print(f"{Colors.BOLD}Choose Deployment Mode:{Colors.RESET}")
    print("  1) Native Deployment (Recommended if no Docker: runs directly on host, ultra-lightweight)")
    print("  2) Docker Compose Deployment (Recommended for container isolation with Postgres + Redis)")
    mode_input = get_user_input("Select mode [1/2]", "1")
    mode = "docker" if mode_input == "2" else "native"
    
    if mode == "docker":
        print_success("Mode: Docker Compose Selected")
    else:
        print_success("Mode: Native Deployment Selected")
        
    if not check_requirements(mode):
        print_error("\nRequirements check failed. Please install missing software and try again.")
        sys.exit(1)
        
    if not setup_env_file(project_dir, mode):
        sys.exit(1)
        
    if not start_platform(project_dir, mode):
        sys.exit(1)
        
    if not init_database(project_dir, mode):
        sys.exit(1)
        
    if not create_admin_user(project_dir, mode):
        sys.exit(1)
        
    verify_deployment(project_dir, mode)
    
    # Read configured domain
    domain = "localhost"
    env_path = project_dir / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("ALLOWED_HOSTS="):
                    domain = line.split("=", 1)[1].strip()
                    break
                    
    show_next_steps(project_dir, domain, mode)
    print_step(8, 8, "All deployment steps completed successfully!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Deployment cancelled by user.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)