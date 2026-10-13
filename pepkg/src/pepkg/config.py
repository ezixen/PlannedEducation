"""Configuration management for pepkg."""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration for pepkg CLI."""

    api_url: str = "http://localhost:8000"
    token: str | None = None
    verbose: bool = False
    config_path: Path | None = None

    # Computed fields
    config_data: dict[str, Any] = Field(default_factory=dict, exclude=True)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self._load_config_file()

    def _load_config_file(self) -> None:
        """Load configuration from file."""
        config_paths = []

        if self.config_path:
            config_paths.append(self.config_path)
        else:
            # Default config locations
            config_paths.extend([
                Path.cwd() / "pepkg.yaml",
                Path.cwd() / "pepkg.yml",
                Path.home() / ".config" / "pepkg" / "config.yaml",
                Path.home() / ".pepkg.yaml",
            ])

        for path in config_paths:
            if path.exists():
                try:
                    with open(path, "r") as f:
                        if path.suffix in (".yaml", ".yml"):
                            self.config_data = yaml.safe_load(f) or {}
                        else:
                            self.config_data = json.load(f)
                    break
                except Exception:
                    continue

        # Override with config file values if not set via CLI/env
        if "api_url" in self.config_data and not self.api_url:
            self.api_url = self.config_data["api_url"]
        if "token" in self.config_data and not self.token:
            self.token = self.config_data["token"]

    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"pepkg/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def save_token(self, token: str) -> None:
        """Save token to config file."""
        self.token = token
        if self.config_path:
            config_file = self.config_path
        else:
            config_dir = Path.home() / ".config" / "pepkg"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yaml"

        config_data = {}
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}

        config_data["token"] = token
        config_data["api_url"] = self.api_url

        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)

    def clear_token(self) -> None:
        """Clear stored token."""
        self.token = None
        if self.config_path:
            config_file = self.config_path
        else:
            config_file = Path.home() / ".config" / "pepkg" / "config.yaml"

        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}
            config_data.pop("token", None)
            with open(config_file, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False)