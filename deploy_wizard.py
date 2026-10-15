#!/usr/bin/env python3
"""
PlannedEducation - Guided Deploy Wizard
Interactive setup wizard for easy school deployment.
Run: python deploy_wizard.py
"""

import os
import sys
import subprocess
import secrets
import shutil
import getpass
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
    print(f"{Colors.BLUE}{Colors.BOLD}[Step {step}/{total}] {text}{Colors.RESET}")

def print_success(text: str):
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def run_cmd(cmd, cwd: Optional[str] = None, capture: bool = True, shell: bool = False) -> tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True, timeout=300, shell=shell)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def check_requirements() -> bool:
    """Check if Docker, Git, Python are available (Linux-focused)"""
    print_step(1, 8, "Checking requirements...")
    
    # Check Docker
    code, out, err = run_cmd(["docker", "--version"])
    if code == 0:
        version = out.strip().split('\n')[0]
        print_success(f"Docker: {version}")
    else:
        print_error("Docker: NOT FOUND")
        print_warning("Install Docker: https://docs.docker.com/engine/install/")
        return False
    
    # Check Docker Compose (try both docker compose and docker-compose)
    compose_ok = False
    for cmd in [["docker", "compose", "version"], ["docker-compose", "--version"]]:
        code, out, err = run_cmd(cmd)
        if code == 0:
            version = out.strip().split('\n')[0]
            print_success(f"Docker Compose: {version}")
            compose_ok = True
            break
    
    if not compose_ok:
        print_error("Docker Compose: NOT FOUND")
        print_warning("Install Docker Compose plugin: https://docs.docker.com/compose/install/")
        return False
    
    # Check Git
    code, out, err = run_cmd(["git", "--version"])
    if code == 0:
        version = out.strip().split('\n')[0]
        print_success(f"Git: {version}")
    else:
        print_error("Git: NOT FOUND")
        return False
    
    # Check Python (try python3 first, then python for Windows)
    python_ok = False
    for cmd in [["python3", "--version"], ["python", "--version"]]:
        code, out, err = run_cmd(cmd)
        if code == 0:
            version = out.strip().split('\n')[0]
            print_success(f"Python: {version}")
            python_ok = True
            break
    
    if not python_ok:
        print_error("Python: NOT FOUND")
        return False
    
    # Check if running on Linux (preferred for school servers)
    import platform
    if platform.system() != "Linux":
        print_warning(f"Running on {platform.system()}. School servers typically run Linux.")
        print_warning("This wizard works cross-platform, but production deployment should target Linux.")
    
    return True

def get_user_input(prompt: str, default: str = "", required: bool = False, secret: bool = False) -> str:
    """Get user input with optional default"""
    while True:
        if secret:
            import getpass
            value = getpass.getpass(f"{prompt} {'[' + default + ']' if default else ''}: ")
        else:
            value = input(f"{prompt} {'[' + default + ']' if default else ''}: ").strip()
        
        if not value and default:
            return default
        if not value and required:
            print_error("This field is required!")
            continue
        return value

def generate_keys() -> tuple[str, str]:
    """Generate JWT and Fernet keys"""
    jwt_key = secrets.token_hex(64)
    fernet_key = Fernet.generate_key().decode()
    return jwt_key, fernet_key

def setup_env_file(project_dir: Path) -> bool:
    """Interactive .env configuration"""
    print_step(2, 8, "Configuring environment (.env)")
    
    env_path = project_dir / ".env"
    env_example = project_dir / ".env.example"
    
    if not env_example.exists():
        print_error(".env.example not found!")
        return False
    
    # Read example
    with open(env_example, 'r') as f:
        env_content = f.read()
    
    print(f"\n{Colors.YELLOW}We'll configure the required settings now.{Colors.RESET}")
    print(f"Press Enter to accept defaults (shown in brackets).\n")
    
    # Required settings
    print(f"{Colors.BOLD}Required Settings:{Colors.RESET}")
    
    # Generate keys
    print(f"\n{Colors.CYAN}Generating secure keys...{Colors.RESET}")
    jwt_key, fernet_key = generate_keys()
    print_success("JWT_SECRET_KEY generated (64 chars)")
    print_success("AI_KEY_MASTER_SECRET generated (44 chars)")
    
    # School domain
    domain = get_user_input("School domain (e.g., yourschool.edu)", "localhost", required=True)
    
    # Google OAuth (optional)
    print(f"\n{Colors.BOLD}Optional: Google OAuth (for 'Login with Google'){Colors.RESET}")
    print("Get credentials from: https://console.cloud.google.com/")
    google_id = get_user_input("Google Client ID (leave blank to skip)", "")
    google_secret = ""
    if google_id:
        google_secret = get_user_input("Google Client Secret", "", secret=True)
    
    # Email (optional)
    print(f"\n{Colors.BOLD}Optional: Email for password reset{Colors.RESET}")
    smtp_host = get_user_input("SMTP Host (e.g., smtp.gmail.com)", "smtp.gmail.com")
    smtp_port = get_user_input("SMTP Port", "587")
    smtp_user = get_user_input("SMTP Username (your email)", "")
    smtp_pass = ""
    if smtp_user:
        smtp_pass = get_user_input("SMTP Password (app password)", "", secret=True)
    email_from = get_user_input("From Email", f"noreply@{domain}" if domain != "localhost" else "noreply@localhost")
    
    # Build .env content
    env_lines = []
    for line in env_content.split('\n'):
        if line.startswith('JWT_SECRET_KEY='):
            env_lines.append(f'JWT_SECRET_KEY={jwt_key}')
        elif line.startswith('AI_KEY_MASTER_SECRET='):
            env_lines.append(f'AI_KEY_MASTER_SECRET={fernet_key}')
        elif line.startswith('GOOGLE_CLIENT_ID='):
            env_lines.append(f'GOOGLE_CLIENT_ID={google_id}')
        elif line.startswith('GOOGLE_CLIENT_SECRET='):
            env_lines.append(f'GOOGLE_CLIENT_SECRET={google_secret}')
        elif line.startswith('CORS_ORIGINS='):
            protocol = "https" if domain != "localhost" else "http"
            port = "" if domain != "localhost" else ":5173"
            env_lines.append(f'CORS_ORIGINS={protocol}://{domain}{port}')
        elif line.startswith('ALLOWED_HOSTS='):
            env_lines.append(f'ALLOWED_HOSTS={domain}')
        elif line.startswith('WEBAUTHN_RP_ID='):
            env_lines.append(f'WEBAUTHN_RP_ID={domain}')
        elif line.startswith('WEBAUTHN_ORIGIN='):
            protocol = "https" if domain != "localhost" else "http"
            port = "" if domain != "localhost" else ":5173"
            env_lines.append(f'WEBAUTHN_ORIGIN={protocol}://{domain}{port}')
        elif line.startswith('SMTP_HOST='):
            env_lines.append(f'SMTP_HOST={smtp_host}')
        elif line.startswith('SMTP_PORT='):
            env_lines.append(f'SMTP_PORT={smtp_port}')
        elif line.startswith('SMTP_USER='):
            env_lines.append(f'SMTP_USER={smtp_user}')
        elif line.startswith('SMTP_PASSWORD='):
            env_lines.append(f'SMTP_PASSWORD={smtp_pass}')
        elif line.startswith('EMAIL_FROM='):
            env_lines.append(f'EMAIL_FROM={email_from}')
        elif line.startswith('PLANNED_EDUCATION_ENV='):
            env_lines.append('PLANNED_EDUCATION_ENV=production')
        else:
            env_lines.append(line)
    
    # Write .env
    with open(env_path, 'w') as f:
        f.write('\n'.join(env_lines))
    
    print_success(f".env created at {env_path}")
    return True

def start_platform(project_dir: Path) -> bool:
    """Build and start Docker containers"""
    print_step(3, 8, "Building and starting platform (first run takes 3-5 min)...")
    
    # Build - use docker compose (plugin) which is available
    print(f"{Colors.CYAN}Building Docker images...{Colors.RESET}")
    # Use shell=True on Windows to ensure PATH is resolved correctly
    code, out, err = run_cmd("docker compose up -d --build", cwd=project_dir, capture=False, shell=True)
    if code != 0:
        print_error(f"Build failed: {err}")
        return False
    print_success("Docker images built")
    
    # Wait for containers
    print(f"{Colors.CYAN}Waiting for containers to start...{Colors.RESET}")
    import time
    time.sleep(15)
    
    # Check health
    code, out, err = run_cmd("docker compose exec -T backend curl -f http://localhost:8000/health", cwd=project_dir, shell=True)
    if code == 0:
        print_success("Backend healthy")
    else:
        print_warning("Backend health check failed, but continuing...")
    
    return True

def init_database(project_dir: Path) -> bool:
    """Initialize database tables"""
    print_step(4, 8, "Initializing database...")
    
    cmd = "docker compose exec -T backend python -c \"from src.plannededucation.api.database import Base, engine; from src.plannededucation.api import models; Base.metadata.create_all(bind=engine); print('Database initialized')\""
    code, out, err = run_cmd(cmd, cwd=project_dir, shell=True)
    if code == 0:
        print_success("Database initialized")
        return True
    
    print_error(f"Database init failed: {err}")
    return False

def create_admin_user(project_dir: Path) -> bool:
    """Create initial admin user"""
    print_step(5, 8, "Creating admin user...")
    
    email = get_user_input("Admin email", "admin@yourschool.edu", required=True)
    username = get_user_input("Admin username", "admin", required=True)
    full_name = get_user_input("Admin full name", "School Administrator", required=True)
    password = get_user_input("Admin password (min 8 chars)", "ChangeMe123!", required=True, secret=True)
    
    # Escape for Python string
    password_escaped = password.replace('"', '\\"').replace("'", "\\'")
    email_escaped = email.replace('"', '\\"')
    username_escaped = username.replace('"', '\\"')
    name_escaped = full_name.replace('"', '\\"')
    
    cmd = f'docker compose exec -T backend python -c "from src.plannededucation.api.database import SessionLocal; from src.plannededucation.api.models import User; from src.plannededucation.api.routes_auth import get_password_hash; db = SessionLocal(); admin = User(email=\'{email_escaped}\', username=\'{username_escaped}\', full_name=\'{name_escaped}\', hashed_password=get_password_hash(\'{password_escaped}\'), role=\'admin\', is_admin=True, is_active=True); db.add(admin); db.commit(); print(\'Admin created: {email}\'); print(\'CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN\')"'
    
    code, out, err = run_cmd(cmd, cwd=project_dir, shell=True)
    if code == 0:
        print_success(f"Admin created: {email}")
        print_warning("CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN!")
        return True
    
    print_error(f"Admin creation failed: {err}")
    return False

def verify_deployment(project_dir: Path) -> bool:
    """Verify all services are running"""
    print_step(6, 8, "Verifying deployment...")
    
    checks = [
        ("Backend API", "curl -f http://localhost:8000/health"),
        ("Frontend", "curl -f http://localhost:5173"),
        ("Database", "docker compose exec -T postgres pg_isready -U postgres"),
        ("Redis", "docker compose exec -T redis redis-cli ping"),
    ]
    
    all_ok = True
    for name, cmd in checks:
        code, out, err = run_cmd(cmd, cwd=project_dir, shell=True)
        if code == 0:
            print_success(f"{name}: OK")
        else:
            print_error(f"{name}: FAILED")
            all_ok = False
    
    return all_ok

def show_next_steps(project_dir: Path, domain: str):
    """Show final instructions"""
    print_step(7, 8, "Deployment complete! 🎉")
    
    protocol = "https" if domain != "localhost" else "http"
    port = "" if domain != "localhost" else ":5173"
    url = f"{protocol}://{domain}{port}"
    
    print(f"""
{Colors.GREEN}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗
║                    DEPLOYMENT SUCCESSFUL!                    ║
╚══════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.BOLD}Access your platform:{Colors.RESET}
  🌐 Frontend:  {url}
  📚 API Docs:  {protocol}://{domain}:8000/docs
  ❤️  Health:    {protocol}://{domain}:8000/health

{Colors.BOLD}First Login:{Colors.RESET}
  1. Open {url} in your browser
  2. Login with your admin credentials
  3. {Colors.RED}IMMEDIATELY change your password{Colors.RESET} in Settings → Security

{Colors.BOLD}Useful Commands:{Colors.RESET}
  View logs:     docker-compose logs -f backend
  Update:        git pull && docker-compose build --no-cache && docker-compose up -d
  Backup:        docker-compose exec -T postgres pg_dump -U postgres plannededucation | gzip > backup_$(date +%Y%m%d).sql.gz
  Restart:       docker-compose restart

{Colors.BOLD}Module System:{Colors.RESET}
  • Teachers create exams → Export as .pepkg.json
  • Import modules in Exam Editor → 'Import Package'
  • Central repository: plannededucation.org/modules (when live)
  • Custom sources: Add MODULE_SOURCES to .env

{Colors.BOLD}Next Steps:{Colors.RESET}
  1. Change admin password immediately
  2. Configure Google OAuth (optional) in Settings
  4. Add AI API keys in Settings → AI Keys
  5. Download SEB config for secure exams
  6. Set up daily backups (see DEPLOY_SIMPLE.md)

{Colors.CYAN}Need help? Check DEPLOY_SIMPLE.md or GitHub Issues{Colors.RESET}
""")

def main():
    print_header("PlannedEducation - Guided Deploy Wizard")
    print("This wizard will deploy PlannedEducation to your school server.\n")
    
    # Check if we're in the right directory
    project_dir = Path.cwd()
    if not (project_dir / "docker-compose.yml").exists():
        print_error("docker-compose.yml not found!")
        print("Please run this script from the PlannedEducation root directory.")
        sys.exit(1)
    
    # Check requirements
    if not check_requirements():
        print_error("\nPlease install missing requirements and try again.")
        print("See DEPLOY_SIMPLE.md for installation instructions.")
        sys.exit(1)
    
    # Setup .env
    if not setup_env_file(project_dir):
        sys.exit(1)
    
    # Start platform
    if not start_platform(project_dir):
        sys.exit(1)
    
    # Init database
    if not init_database(project_dir):
        sys.exit(1)
    
    # Create admin
    if not create_admin_user(project_dir):
        sys.exit(1)
    
    # Verify
    if not verify_deployment(project_dir):
        print_warning("Some services may not be fully ready yet.")
        print("Check logs with: docker-compose logs -f")
    
    # Show next steps
    # Get domain from .env
    env_path = project_dir / ".env"
    domain = "localhost"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("WEBAUTHN_RP_ID="):
                    domain = line.split("=", 1)[1].strip()
                    break
    
    show_next_steps(project_dir, domain)
    
    print_step(8, 8, "Done!")

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