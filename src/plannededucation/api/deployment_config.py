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
    smtp_password: str | None = Field(default=None, max_length=256)
    smtp_use_tls: bool = Field(default=True)
    smtp_use_ssl: bool = Field(default=False)
    email_from: str = Field(default="PlannedEducation <noreply@localhost>", max_length=128)


class DeploymentConfigResponse(DeploymentConfigSchema):
    config_file_path: str
    last_modified: str | None = None
    restart_required: bool = False


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
    }

    # If deployment.json exists, overlay its values
    if json_path.is_file():
        try:
            with open(json_path, encoding="utf-8") as f:
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
    config_data["updated_at"] = datetime.now(UTC).isoformat()

    # Write to config/deployment.json
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    # Reconstruct CORS origins automatically if domain or ports were adjusted
    domain = new_config.domain.strip()
    frontend_port = new_config.frontend_port
    api_port = new_config.api_port

    # Build CORS origins list ensuring domain, localhost, 127.0.0.1 and ports are present
    user_cors = [o.strip() for o in new_config.cors_origins.split(",") if o.strip()]
    origins_set = set(user_cors)
    origins_set.add(f"http://{domain}:{frontend_port}")
    origins_set.add(f"http://localhost:{frontend_port}")
    origins_set.add(f"http://127.0.0.1:{frontend_port}")
    if domain != "localhost" and domain != "127.0.0.1":
        origins_set.add(f"https://{domain}")
        origins_set.add(f"http://{domain}")

    cors_str = ",".join(sorted(origins_set))
    config_data["cors_origins"] = cors_str

    # Update .env
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
        "SMTP_PASSWORD": new_config.smtp_password or "",
        "SMTP_USE_TLS": "true" if new_config.smtp_use_tls else "false",
        "SMTP_USE_SSL": "true" if new_config.smtp_use_ssl else "false",
        "EMAIL_FROM": new_config.email_from,
    }
    update_env_file(env_path, env_updates)

    # Return full state
    config_data["config_file_path"] = str(json_path)
    config_data["last_modified"] = config_data["updated_at"]
    config_data["restart_required"] = True
    return config_data

