"""Portable admin/env settings export/import (no DB / crypto secrets)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from src.plannededucation.api import models
from src.plannededucation.api.database import SessionLocal
from src.plannededucation.api.deployment_config import (
    SETTINGS_BUNDLE_KIND,
    build_settings_bundle,
    parse_settings_bundle,
    write_settings_bundle_to_path,
)
from src.plannededucation.api.main import app

client = TestClient(app)


def _admin_headers() -> dict:
    email = f"cfg_admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"
    r = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": email.split("@")[0],
            "password": password,
            "full_name": "Config Admin",
            "role": "teacher",
        },
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]
    db = SessionLocal()
    try:
        u = db.query(models.User).filter(models.User.id == user_id).first()
        assert u is not None
        u.is_admin = True
        u.is_superadmin = True
        u.teacher_approved = True
        db.commit()
    finally:
        db.close()
    tok = client.post("/auth/token", data={"username": email, "password": password})
    assert tok.status_code == 200, tok.text
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


def test_settings_bundle_excludes_secrets():
    bundle = build_settings_bundle(include_smtp_password=False)
    assert bundle["kind"] == SETTINGS_BUNDLE_KIND
    blob = json.dumps(bundle)
    assert "JWT_SECRET" not in blob
    assert "DB_ENCRYPTION" not in blob
    assert "DATABASE_URL" not in blob
    assert "school_name" in bundle["settings"]


def test_export_and_import_via_api(tmp_path: Path):
    headers = _admin_headers()
    out = tmp_path / "pe-settings.json"
    # Relative path under project is required for resolve_settings_file_path safety
    # when not absolute — use absolute temp path.
    export = client.post(
        "/admin/config/export-file",
        headers=headers,
        json={"path": str(out), "include_smtp_password": False},
    )
    assert export.status_code == 200, export.text
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == SETTINGS_BUNDLE_KIND
    data["settings"]["school_name"] = "Imported School Config"
    out.write_text(json.dumps(data), encoding="utf-8")

    imported = client.post(
        "/admin/config/import-file",
        headers=headers,
        json={"path": str(out)},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["config"]["school_name"] == "Imported School Config"


def test_parse_rejects_secret_injection():
    schema = parse_settings_bundle(
        {
            "kind": SETTINGS_BUNDLE_KIND,
            "version": 1,
            "settings": {
                "school_name": "Safe School",
                "JWT_SECRET_KEY": "should-be-ignored",
                "DATABASE_URL": "sqlite:///evil.db",
            },
        }
    )
    assert schema.school_name == "Safe School"
    dumped = schema.model_dump()
    assert "JWT_SECRET_KEY" not in dumped
    assert "DATABASE_URL" not in dumped


def test_write_settings_roundtrip(tmp_path: Path):
    target = tmp_path / "roundtrip.peconfig"
    written = write_settings_bundle_to_path(str(target))
    assert written == target.resolve()
    assert target.is_file()
