"""Focused regression tests for F-021–F-024 security remediations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.plannededucation.api import database, models
from src.plannededucation.api.archive_utils import (
    ArchiveManager,
    get_archive_master_key,
)
from src.plannededucation.api.main import app
from src.plannededucation.api.url_safety import (
    UnsafeURLError,
    assert_resolution_still_safe,
    resolve_public_ips,
    validate_ai_base_url,
    validate_outbound_url,
    validate_package_source_url,
)

client = TestClient(app)


def _register(email: str, username: str, role: str = "teacher") -> tuple[str, dict]:
    client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "Password123!",
            "role": role,
            "full_name": username,
        },
    )
    db = next(database.get_db())
    user = db.query(models.User).filter_by(email=email).first()
    assert user is not None
    if role == "teacher":
        user.teacher_approved = True
        db.commit()
    token = client.post(
        "/auth/token", data={"username": email, "password": "Password123!"}
    ).json()["access_token"]
    return user.id, {"Authorization": f"Bearer {token}"}


# ── F-022 URL safety ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/secret",
        "http://localhost:11434",
        "https://10.0.0.5/api",
        "https://192.168.1.1/",
        "https://172.16.0.1/",
        "https://169.254.169.254/latest/meta-data/",
        "file:///etc/passwd",
        "https://user:pass@evil.example/path",
        "https://evil.example/?api_key=exfil",
    ],
)
def test_f022_blocks_ssrf_and_exfil_urls(url: str):
    with pytest.raises(UnsafeURLError):
        validate_outbound_url(url, allow_loopback=False, allowed_schemes=("http", "https"))


def test_f022_allows_public_https_and_ollama_loopback():
    assert validate_package_source_url("https://example.com/modules.json").startswith("https://")
    assert validate_ai_base_url("http://127.0.0.1:11434", provider="ollama")
    with pytest.raises(UnsafeURLError):
        validate_ai_base_url("http://127.0.0.1:11434", provider="openai")
    with pytest.raises(UnsafeURLError):
        validate_ai_base_url("https://10.1.2.3/v1", provider="custom")


def test_f022_ai_key_endpoint_rejects_private_base_url():
    _, headers = _register("f022_ai@test.com", "f022_ai", role="teacher")
    res = client.put(
        "/auth/ai-key",
        json={
            "ai_provider": "openai",
            "ai_api_key": "sk-test",
            "ai_base_url": "http://127.0.0.1:9",
        },
        headers=headers,
    )
    assert res.status_code == 422


def test_f022_package_source_rejects_metadata_url():
    _, headers = _register("f022_admin@test.com", "f022_admin", role="teacher")
    db = next(database.get_db())
    admin = db.query(models.User).filter_by(email="f022_admin@test.com").first()
    admin.is_admin = True
    db.commit()

    res = client.post(
        "/packages/sources",
        json={
            "name": "evil",
            "url": "https://169.254.169.254/latest/meta-data/",
            "source_type": "custom",
        },
        headers=headers,
    )
    assert res.status_code == 422


def test_f022_resolve_public_ips_blocks_private_literal():
    with pytest.raises(UnsafeURLError):
        resolve_public_ips("10.0.0.1")
    with pytest.raises(UnsafeURLError):
        resolve_public_ips("169.254.169.254")
    assert resolve_public_ips("127.0.0.1", allow_loopback=True) == ["127.0.0.1"]


def test_f022_validate_returns_ips_for_literal_public(monkeypatch):
    # Literal public IP — no DNS needed.
    url, ips = validate_outbound_url(
        "https://8.8.8.8/path",
        return_ips=True,
    )
    assert url.startswith("https://")
    assert ips == ["8.8.8.8"]


def test_f022_dns_rebind_rejected_when_ips_change(monkeypatch):
    """Connect-time re-resolve must reject when validated public IPs no longer overlap."""
    hostname = "rebind.example.test"

    monkeypatch.setattr(
        "src.plannededucation.api.url_safety.resolve_public_ips",
        lambda host, *, allow_loopback=False: ["198.51.100.20"],
    )

    # Validated earlier as 203.0.113.10; re-resolve now points elsewhere (rebinding).
    with pytest.raises(UnsafeURLError, match="DNS rebinding"):
        assert_resolution_still_safe(hostname, allowed_ips=["203.0.113.10"])


def test_f022_dns_rebind_rejects_private_after_re_resolve(monkeypatch):
    """Re-resolve that yields a private IP must fail closed even if previously public."""

    def _private_only(hostname, *, allow_loopback=False):
        raise UnsafeURLError("URL resolves to a blocked address")

    monkeypatch.setattr(
        "src.plannededucation.api.url_safety.resolve_public_ips",
        _private_only,
    )
    with pytest.raises(UnsafeURLError, match="blocked"):
        assert_resolution_still_safe(
            "evil.example",
            allowed_ips=["203.0.113.10"],
        )


def test_f022_assert_resolution_accepts_overlapping_ip(monkeypatch):
    monkeypatch.setattr(
        "src.plannededucation.api.url_safety.resolve_public_ips",
        lambda hostname, *, allow_loopback=False: ["203.0.113.10", "203.0.113.11"],
    )
    pinned = assert_resolution_still_safe(
        "ok.example",
        allowed_ips=["203.0.113.10"],
    )
    assert pinned == ["203.0.113.10"]


# ── F-021 uploads ────────────────────────────────────────────────────────────


def test_f021_upload_uses_opaque_name_and_rejects_traversal(tmp_path, monkeypatch):
    from src.plannededucation.api import routes_ai

    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    monkeypatch.setattr(routes_ai, "UPLOAD_DIR", upload_root)

    teacher_id, headers = _register("f021_t@test.com", "f021_t", role="teacher")
    _, other_headers = _register("f021_other@test.com", "f021_other", role="teacher")

    # Path-traversal-looking client name must not escape the owner dir.
    files = {
        "file": ("../../etc/passwd.png", b"\x89PNG\r\n\x1a\n" + b"x" * 32, "image/png"),
    }
    data = {"teacher_id": teacher_id}
    res = client.post("/ai/grade/upload", files=files, data=data, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    opaque = body["image_filename"]
    assert opaque
    assert ".." not in opaque
    assert opaque != "../../etc/passwd.png"
    assert Path(opaque).name == opaque

    owner_dir = upload_root / teacher_id
    assert owner_dir.is_dir()
    saved = list(owner_dir.glob("*"))
    assert len(saved) == 1
    assert saved[0].name == opaque
    # Nothing written at upload root as a traversal target
    assert not (upload_root / "passwd.png").exists()
    assert not (tmp_path / "etc").exists()

    # Owner can fetch; other teacher cannot.
    ok = client.get(f"/ai/grade/image/{opaque}", headers=headers)
    assert ok.status_code == 200
    denied = client.get(f"/ai/grade/image/{opaque}", headers=other_headers)
    assert denied.status_code in (403, 404)


def test_f021_bulk_upload_caps_file_count(tmp_path, monkeypatch):
    from src.plannededucation.api import routes_ai

    monkeypatch.setattr(routes_ai, "UPLOAD_DIR", tmp_path / "bulk")
    monkeypatch.setattr(routes_ai, "MAX_AI_BULK_FILES", 2)
    (tmp_path / "bulk").mkdir()

    teacher_id, headers = _register("f021_bulk@test.com", "f021_bulk", role="teacher")
    tiny = b"\x89PNG\r\n\x1a\n" + b"0" * 16
    files = [
        ("files", ("a.png", tiny, "image/png")),
        ("files", ("b.png", tiny, "image/png")),
        ("files", ("c.png", tiny, "image/png")),
    ]
    res = client.post(
        "/ai/grade/bulk-upload",
        files=files,
        data={"teacher_id": teacher_id, "subject": "math", "ai_correction_enabled": "false"},
        headers=headers,
    )
    assert res.status_code == 413


# ── F-023 path containment ───────────────────────────────────────────────────


def test_f023_curriculum_import_rejects_path_traversal(monkeypatch, tmp_path):
    from src.plannededucation.api import routes_packages

    modules = tmp_path / "modules"
    modules.mkdir()
    # Build a checksum-valid curriculum package (matches _validate_package_structure).
    from src.plannededucation.api.routes_packages import _calculate_checksum

    pkg = {
        "metadata": {
            "id": "m1",
            "name": "Module One",
            "version": "1.0.0",
            "author": "tester",
            "author_id": "tester-id",
            "language": "en",
            "checksum": "",
        },
        "exam": {"title": "T", "duration_minutes": 10},
        "questions": [
            {
                "id": "q1",
                "question_type": "essay",
                "text": "Q",
                "correct_answer": "A",
                "points": 1,
            }
        ],
    }
    pkg_copy = {**pkg, "metadata": {**pkg["metadata"], "checksum": ""}}
    pkg["metadata"]["checksum"] = _calculate_checksum(pkg_copy)
    (modules / "ok.json").write_text(json.dumps(pkg), encoding="utf-8")
    # Sibling secret outside modules root
    secret = tmp_path / "secret.json"
    secret.write_text('{"exam":{"title":"leak"}}', encoding="utf-8")

    monkeypatch.setattr(routes_packages, "MODULES_DIR", modules)

    _, headers = _register("f023_t@test.com", "f023_t", role="teacher")

    # Prefix-collision / traversal must 404
    bad = client.post(
        "/packages/curriculum/import",
        json={"path": "../secret.json"},
        headers=headers,
    )
    assert bad.status_code in (400, 404)

    good = client.post(
        "/packages/curriculum/import",
        json={"path": "ok.json"},
        headers=headers,
    )
    assert good.status_code == 200, good.text
    assert good.json()["success"] is True


def test_f023_ensure_under_modules_root_helper(tmp_path, monkeypatch):
    from fastapi import HTTPException

    from src.plannededucation.api import routes_packages

    root = tmp_path / "modules"
    root.mkdir()
    monkeypatch.setattr(routes_packages, "MODULES_DIR", root)

    inside = routes_packages._ensure_under_modules_root(root / "a" / "b.json")
    assert inside.is_relative_to(root.resolve())

    with pytest.raises(HTTPException):
        routes_packages._ensure_under_modules_root(tmp_path / "outside.json")


# ── F-024 archive encryption ─────────────────────────────────────────────────


def test_f024_archive_encrypts_and_round_trips(tmp_path, monkeypatch):
    import asyncio

    monkeypatch.setenv(
        "ARCHIVE_MASTER_KEY",
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    )
    # Reset ephemeral cache if any
    import src.plannededucation.api.archive_utils as au

    au._EPHEMERAL_ARCHIVE_KEY = None

    mgr = ArchiveManager(str(tmp_path / "archive"))
    key = get_archive_master_key(require=True)
    sealed = {
        "submissionId": "sub-f024",
        "examId": "exam-1",
        "studentId": "stu-1",
        "answers": [{"question_id": "q1", "student_response": "secret answer PII"}],
    }

    async def _run():
        meta = await mgr.archive_submission(
            sealed,
            teacher_username="teacher1",
            student_username="student1",
            master_key=key,
            require_encryption=True,
        )
        assert meta["encryption_algorithm"] == "AES-GCM"
        assert meta["encryption_iv"]
        assert meta["encryption_salt"]
        assert meta["compressed_data"]
        assert meta["compressed_data"] != meta["archive_hash"]

        # Raw file must not contain plaintext
        file_path = mgr.get_archive_file_path(meta["archive_path"])
        raw_text = file_path.read_text()
        assert "secret answer PII" not in raw_text
        assert "student_response" not in raw_text

        restored = await mgr.restore_submission(
            meta["archive_path"],
            master_key=key,
            encryption_algorithm=meta["encryption_algorithm"],
            encryption_iv=meta["encryption_iv"],
            encryption_salt=meta["encryption_salt"],
            compressed_data_hex=meta["compressed_data"],
        )
        assert restored["answers"][0]["student_response"] == "secret answer PII"

        # Wrong key must fail
        with pytest.raises(Exception):
            await mgr.restore_submission(
                meta["archive_path"],
                master_key=b"\x00" * 32,
                encryption_algorithm=meta["encryption_algorithm"],
                encryption_iv=meta["encryption_iv"],
                encryption_salt=meta["encryption_salt"],
                compressed_data_hex=meta["compressed_data"],
            )

    asyncio.run(_run())


def test_f024_approve_stores_ciphertext_not_hash():
    teacher_id, t_headers = _register("f024_t@test.com", "f024_t", role="teacher")
    student_id, s_headers = _register("f024_s@test.com", "f024_s", role="student")

    exam = client.post(
        "/exams",
        json={"title": "F024 Exam", "description": "enc", "duration_minutes": 30},
        headers=t_headers,
    )
    assert exam.status_code in (200, 201), exam.text
    exam_id = exam.json()["id"]

    q = client.post(
        f"/exams/{exam_id}/questions",
        json={
            "question_type": "essay",
            "text": "Explain",
            "correct_answer": "Because",
            "points": 5,
        },
        headers=t_headers,
    )
    assert q.status_code in (200, 201), q.text
    q_id = q.json()["id"]

    assert client.post(f"/exams/{exam_id}/start", headers=s_headers).status_code == 200
    submit = client.post(
        f"/exams/{exam_id}/submit",
        json={"answers": [{"question_id": q_id, "response": "Because plaintext"}]},
        headers=s_headers,
    )
    assert submit.status_code == 200, submit.text

    subs = client.get(
        f"/archive/teacher/class-submissions?exam_id={exam_id}", headers=t_headers
    )
    assert subs.status_code == 200
    sub_id = next(s["submission_id"] for s in subs.json() if s["exam_id"] == exam_id)

    # Skip AI-grade (Presidio) — approve with an explicit score override.
    approve = client.post(
        "/archive/teacher/approve",
        json={
            "submission_ids": [sub_id],
            "overrides": {sub_id: {"score": 5.0, "feedback": "ok"}},
        },
        headers=t_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json().get("encryption_algorithm") == "AES-GCM"

    db = next(database.get_db())
    archived = (
        db.query(models.ArchivedSubmission)
        .filter(models.ArchivedSubmission.submission_id == sub_id)
        .first()
    )
    assert archived is not None
    assert archived.encryption_algorithm == "AES-GCM"
    assert archived.encryption_iv
    assert archived.encryption_salt
    assert archived.compressed_data
    assert archived.compressed_data != archived.archive_hash
    assert "Because plaintext" not in archived.compressed_data
