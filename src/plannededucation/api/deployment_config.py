"""
Deployment Configuration Management for PlannedEducation.
Handles loading, saving, and synchronizing deployment settings between
config/deployment.json and the root .env file.
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("plannededucation")


class DeploymentConfigSchema(BaseModel):
    school_name: str = Field(default="PlannedEducation School", min_length=1, max_length=128)
    domain: str = Field(default="localhost", min_length=1, max_length=255)
    api_port: int = Field(default=8000, ge=1, le=65535)
    frontend_port: int = Field(default=5173, ge=1, le=65535)
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5175",
        max_length=2048,
    )
    allowed_hosts: str = Field(default="localhost,127.0.0.1", max_length=1024)
    environment: str = Field(default="development", pattern=r"^(development|production|staging|test)$")
    allow_dev_seb_bypass: bool = Field(default=True)
    anonymizer_enabled: bool = Field(default=True)
    anonymizer_language: str = Field(default="en", max_length=10)

    # Outgoing Email / SMTP (Optional - in-app notifications operate 100% offline without SMTP)
    smtp_host: str | None = Field(default=None, max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str | None = Field(default=None, max_length=128)
    # None / omitted => preserve existing .env password (F-041 patch semantics).
    # Empty string => explicitly clear the stored password.
    smtp_password: str | None = Field(default=None, max_length=256)
    smtp_use_tls: bool = Field(default=True)
    smtp_use_ssl: bool = Field(default=False)
    email_from: str = Field(default="PlannedEducation <noreply@localhost>", max_length=128)

    # School header branding (persisted in deployment.json)
    header_mode: str | None = Field(default=None, max_length=32)
    header_image_url: str | None = Field(default=None, max_length=1024)

    # Database Backup Configuration
    backup_location: str = Field(default="backups", max_length=512, description="Directory for database backups")
    backup_frequency_days: int = Field(default=1, ge=1, le=365, description="Automatic backup frequency in days (default: 1 day)")
    backup_retention_days: int = Field(default=30, ge=1, le=3650, description="Retention period for automatic backups in days (default: 30 days)")
    backup_time: str = Field(default="22:00", pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Time of day for automatic backups in 24h format (default: 22:00)")

    # Support Email for Teachers (set by superadmin, visible to all teachers in the Lounge)
    admin_support_email: str | None = Field(default=None, max_length=256, description="Admin support email visible to all teachers")

    # Home-exam / remote proctoring platform gate (superadmin). Default OFF —
    # classroom modules stay free of webcam/mic/gaze unless explicitly enabled.
    home_exam_proctoring_enabled: bool = Field(
        default=False,
        description="When false, teachers cannot enable home-exam webcam/mic/gaze proctoring",
    )


class DeploymentConfigResponse(BaseModel):
    school_name: str
    domain: str
    api_port: int
    frontend_port: int
    cors_origins: str
    allowed_hosts: str
    environment: str
    allow_dev_seb_bypass: bool
    anonymizer_enabled: bool
    anonymizer_language: str
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    # smtp_password intentionally excluded from API response
    smtp_password_configured: bool = False
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    email_from: str
    header_mode: str | None = None
    header_image_url: str | None = None
    config_file_path: str
    last_modified: str | None = None
    restart_required: bool = False
    backup_location: str = "backups"
    backup_frequency_days: int = 1
    backup_retention_days: int = 30
    backup_time: str = "22:00"
    admin_support_email: str | None = None
    home_exam_proctoring_enabled: bool = False


def find_project_root() -> Path:
    """Find the project root containing .env, config/, or src/."""
    current = Path.cwd().resolve()
    # Check current working directory first
    if (current / "src" / "plannededucation").is_dir() or (current / ".env").is_file():
        return current
    # Search parent directories
    for parent in current.parents:
        if (parent / "src" / "plannededucation").is_dir() or (parent / ".env").is_file():
            return parent
    return current


def get_config_dir() -> Path:
    """Get the path to the config directory, creating it if needed."""
    root = find_project_root()
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_deployment_json_path() -> Path:
    """Path to config/deployment.json."""
    return get_config_dir() / "deployment.json"


def get_env_path() -> Path:
    """Path to the root .env file."""
    return find_project_root() / ".env"


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse key-value pairs from a .env file."""
    env_vars: dict[str, str] = {}
    if not env_path.is_file():
        return env_vars
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    env_vars[key] = val
    except Exception as exc:
        logger.warning(f"Could not parse .env file {env_path}: {exc}")
    return env_vars


def update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """
    Update or append key-value pairs in the .env file preserving existing comments.
    """
    existing_lines: list[str] = []
    if env_path.is_file():
        try:
            with open(env_path, encoding="utf-8") as f:
                existing_lines = f.readlines()
        except Exception as exc:
            logger.warning(f"Could not read existing .env: {exc}")

    keys_updated = set()
    new_lines: list[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                keys_updated.add(k)
                continue
        new_lines.append(line if line.endswith("\n") else f"{line}\n")

    # Append any keys that were not already in the file
    for k, v in updates.items():
        if k not in keys_updated:
            new_lines.append(f"{k}={v}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as exc:
        logger.error(f"Failed to write .env file {env_path}: {exc}")
        raise


def load_deployment_config() -> dict[str, Any]:
    """
    Load deployment configuration from config/deployment.json or fallback to .env / os.environ.
    """
    json_path = get_deployment_json_path()
    env_path = get_env_path()
    env_vars = parse_env_file(env_path)

    # Defaults
    config: dict[str, Any] = {
        "school_name": os.getenv("PE_SCHOOL_NAME", env_vars.get("PE_SCHOOL_NAME", "PlannedEducation School")),
        "domain": os.getenv("DOMAIN", env_vars.get("DOMAIN", "localhost")),
        "api_port": int(os.getenv("PORT", env_vars.get("PORT", "8000"))),
        "frontend_port": int(os.getenv("FRONTEND_PORT", env_vars.get("FRONTEND_PORT", "5173"))),
        "cors_origins": os.getenv(
            "CORS_ORIGINS",
            env_vars.get(
                "CORS_ORIGINS",
                "http://localhost:5173,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5175",
            ),
        ),
        "allowed_hosts": os.getenv("ALLOWED_HOSTS", env_vars.get("ALLOWED_HOSTS", "localhost,127.0.0.1")),
        "environment": os.getenv("ENVIRONMENT", env_vars.get("ENVIRONMENT", "development")),
        "allow_dev_seb_bypass": os.getenv("ALLOW_DEV_SEB_BYPASS", env_vars.get("ALLOW_DEV_SEB_BYPASS", "true")).lower() == "true",
        "anonymizer_enabled": os.getenv("ANONYMIZER_ENABLED", env_vars.get("ANONYMIZER_ENABLED", "true")).lower() == "true",
        "anonymizer_language": os.getenv("ANONYMIZER_LANGUAGE", env_vars.get("ANONYMIZER_LANGUAGE", "en")),
        # Outgoing Email / SMTP
        "smtp_host": os.getenv("SMTP_HOST", env_vars.get("SMTP_HOST")),
        "smtp_port": int(os.getenv("SMTP_PORT", env_vars.get("SMTP_PORT", "587"))),
        "smtp_user": os.getenv("SMTP_USER", env_vars.get("SMTP_USER")),
        "smtp_password": os.getenv("SMTP_PASSWORD", env_vars.get("SMTP_PASSWORD")),
        "smtp_use_tls": os.getenv("SMTP_USE_TLS", env_vars.get("SMTP_USE_TLS", "true")).lower() in ("true", "1", "yes"),
        "smtp_use_ssl": os.getenv("SMTP_USE_SSL", env_vars.get("SMTP_USE_SSL", "false")).lower() in ("true", "1", "yes"),
        "email_from": os.getenv("EMAIL_FROM", env_vars.get("EMAIL_FROM", "PlannedEducation <noreply@localhost>")),
        "header_mode": None,
        "header_image_url": None,
        # Database Backup Configuration
        "backup_location": os.getenv("BACKUP_LOCATION", env_vars.get("BACKUP_LOCATION", "backups")),
        "backup_frequency_days": int(os.getenv("BACKUP_FREQUENCY_DAYS", env_vars.get("BACKUP_FREQUENCY_DAYS", "1"))),
        "backup_retention_days": int(os.getenv("BACKUP_RETENTION_DAYS", env_vars.get("BACKUP_RETENTION_DAYS", "30"))),
        "backup_time": os.getenv("BACKUP_TIME", env_vars.get("BACKUP_TIME", "22:00")),
        "admin_support_email": os.getenv("ADMIN_SUPPORT_EMAIL", env_vars.get("ADMIN_SUPPORT_EMAIL")),
        "home_exam_proctoring_enabled": os.getenv(
            "HOME_EXAM_PROCTORING_ENABLED",
            env_vars.get("HOME_EXAM_PROCTORING_ENABLED", "false"),
        ).lower()
        in ("true", "1", "yes"),
    }

    # If deployment.json exists, overlay its values
    if json_path.is_file():
        try:
            with open(json_path, encoding="utf-8-sig") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if k in config:
                            config[k] = v
        except Exception as exc:
            logger.warning(f"Could not load deployment.json: {exc}")

    return config


def save_deployment_config(new_config: DeploymentConfigSchema) -> dict[str, Any]:
    """
    Save new deployment configuration to config/deployment.json and synchronize .env.
    """
    json_path = get_deployment_json_path()
    env_path = get_env_path()

    config_data = new_config.model_dump()
    # Remove sensitive SMTP password from deployment.json (stored in .env only)
    smtp_password = config_data.pop("smtp_password", None)
    config_data["updated_at"] = datetime.now(UTC).isoformat()

    # Reconstruct CORS before writing either file so sources stay aligned (F-041).
    domain = new_config.domain.strip()
    frontend_port = new_config.frontend_port
    api_port = new_config.api_port

    user_cors = [o.strip() for o in new_config.cors_origins.split(",") if o.strip()]
    origins_set = set(user_cors)
    origins_set.add(f"http://{domain}:{frontend_port}")
    origins_set.add(f"http://localhost:{frontend_port}")
    origins_set.add(f"http://127.0.0.1:{frontend_port}")
    if domain not in {"localhost", "127.0.0.1"}:
        origins_set.add(f"https://{domain}")
        if new_config.environment != "production":
            origins_set.add(f"http://{domain}")

    cors_str = ",".join(sorted(origins_set))
    config_data["cors_origins"] = cors_str

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    env_updates = {
        "PE_SCHOOL_NAME": new_config.school_name,
        "DOMAIN": domain,
        "PORT": str(api_port),
        "FRONTEND_PORT": str(frontend_port),
        "CORS_ORIGINS": cors_str,
        "ALLOWED_HOSTS": new_config.allowed_hosts,
        "ENVIRONMENT": new_config.environment,
        "PLANNED_EDUCATION_ENV": new_config.environment,
        "ALLOW_DEV_SEB_BYPASS": "true" if new_config.allow_dev_seb_bypass else "false",
        "ANONYMIZER_ENABLED": "true" if new_config.anonymizer_enabled else "false",
        "ANONYMIZER_LANGUAGE": new_config.anonymizer_language,
        "SMTP_HOST": new_config.smtp_host or "",
        "SMTP_PORT": str(new_config.smtp_port),
        "SMTP_USER": new_config.smtp_user or "",
        "SMTP_USE_TLS": "true" if new_config.smtp_use_tls else "false",
        "SMTP_USE_SSL": "true" if new_config.smtp_use_ssl else "false",
        "EMAIL_FROM": new_config.email_from,
        "BACKUP_LOCATION": new_config.backup_location,
        "BACKUP_FREQUENCY_DAYS": str(new_config.backup_frequency_days),
        "BACKUP_RETENTION_DAYS": str(new_config.backup_retention_days),
        "BACKUP_TIME": new_config.backup_time,
        "ADMIN_SUPPORT_EMAIL": new_config.admin_support_email or "",
        "HOME_EXAM_PROCTORING_ENABLED": (
            "true" if new_config.home_exam_proctoring_enabled else "false"
        ),
    }
    # Patch semantics: omit password => preserve; empty string => clear (F-041).
    if smtp_password is not None:
        env_updates["SMTP_PASSWORD"] = smtp_password
    update_env_file(env_path, env_updates)

    config_data["smtp_password_configured"] = bool(
        smtp_password if smtp_password is not None else os.getenv("SMTP_PASSWORD")
    )
    config_data["config_file_path"] = str(json_path)
    config_data["last_modified"] = config_data["updated_at"]
    config_data["restart_required"] = True
    return config_data


# ── Portable admin env settings bundle (no DB / secrets / teacher data) ───────

SETTINGS_BUNDLE_KIND = "plannededucation.admin_env_settings"
SETTINGS_BUNDLE_VERSION = 1

# Explicit allowlist — never JWT/DB encryption/database URL/user dumps.
_SETTINGS_EXPORT_FIELDS: tuple[str, ...] = (
    "school_name",
    "domain",
    "api_port",
    "frontend_port",
    "cors_origins",
    "allowed_hosts",
    "environment",
    "allow_dev_seb_bypass",
    "anonymizer_enabled",
    "anonymizer_language",
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "smtp_use_tls",
    "smtp_use_ssl",
    "email_from",
    "header_mode",
    "header_image_url",
    "backup_location",
    "backup_frequency_days",
    "backup_retention_days",
    "backup_time",
    "admin_support_email",
    "home_exam_proctoring_enabled",
)


def build_settings_bundle(*, include_smtp_password: bool = False) -> dict[str, Any]:
    """Build a portable JSON document of admin/env settings for clean reinstalls."""
    cfg = load_deployment_config()
    settings: dict[str, Any] = {key: cfg.get(key) for key in _SETTINGS_EXPORT_FIELDS}
    smtp_password = cfg.get("smtp_password")
    if include_smtp_password and smtp_password:
        settings["smtp_password"] = smtp_password
    else:
        settings["smtp_password_configured"] = bool(smtp_password)
    return {
        "kind": SETTINGS_BUNDLE_KIND,
        "version": SETTINGS_BUNDLE_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "notes": (
            "Admin/env settings only. Does not include database files, JWT secrets, "
            "DB encryption keys, or teacher/student data. Place this file on a clean "
            "install (PE_SETTINGS_FILE / -SettingsFile) or import via Admin → Deployment."
        ),
        "settings": settings,
    }


def parse_settings_bundle(raw: dict[str, Any]) -> DeploymentConfigSchema:
    """Validate a portable settings document into DeploymentConfigSchema."""
    if not isinstance(raw, dict):
        raise ValueError("Settings file must be a JSON object")
    payload = raw.get("settings") if isinstance(raw.get("settings"), dict) else raw
    if not isinstance(payload, dict):
        raise ValueError("Settings payload missing")
    # Drop unknown / secret keys that must never be imported from this file.
    forbidden = {
        "jwt_secret_key",
        "JWT_SECRET_KEY",
        "database_url",
        "DATABASE_URL",
        "db_encryption_master_key",
        "DB_ENCRYPTION_MASTER_KEY",
        "ai_key_master_secret",
        "AI_KEY_MASTER_SECRET",
        "encryption_key",
        "ENCRYPTION_KEY",
        "backup_master_key",
        "BACKUP_MASTER_KEY",
        "archive_master_key",
        "ARCHIVE_MASTER_KEY",
    }
    cleaned = {
        k: v
        for k, v in payload.items()
        if k in _SETTINGS_EXPORT_FIELDS or k == "smtp_password"
    }
    for key in forbidden:
        cleaned.pop(key, None)
    # Merge onto current so omitted fields keep existing values on partial imports.
    current = load_deployment_config()
    merged = {**current, **cleaned}
    # Never let a settings file wipe SMTP password unless explicitly provided.
    if "smtp_password" not in cleaned:
        merged["smtp_password"] = None
    return DeploymentConfigSchema(**merged)


def resolve_settings_file_path(path_str: str) -> Path:
    """
    Resolve a settings file path for admin export/import.

    Relative paths are under the project root. Absolute paths are allowed for
    operator-chosen locations (USB / backup folder). Reject empty / null paths
    and parent-escape when relative.
    """
    raw = (path_str or "").strip()
    if not raw or "\x00" in raw:
        raise ValueError("Settings path is required")
    root = find_project_root().resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        # Block sneaky relative escapes (e.g. ..\\..\\Windows\\System32)
        candidate = (root / candidate).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("Relative settings path must stay inside the install directory")
    else:
        candidate = candidate.resolve()
    if candidate.suffix.lower() not in {".json", ".peconfig"}:
        raise ValueError("Settings file must use .json or .peconfig extension")
    return candidate


def write_settings_bundle_to_path(
    path_str: str, *, include_smtp_password: bool = False
) -> Path:
    target = resolve_settings_file_path(path_str)
    target.parent.mkdir(parents=True, exist_ok=True)
    bundle = build_settings_bundle(include_smtp_password=include_smtp_password)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
        f.write("\n")
    return target


def read_settings_bundle_from_path(path_str: str) -> dict[str, Any]:
    target = resolve_settings_file_path(path_str)
    if not target.is_file():
        raise FileNotFoundError(f"Settings file not found: {target}")
    with open(target, encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Settings file must contain a JSON object")
    return data


def apply_settings_bundle_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply a portable settings document to deployment.json + .env (non-secret keys)."""
    schema = parse_settings_bundle(raw)
    return save_deployment_config(schema)

