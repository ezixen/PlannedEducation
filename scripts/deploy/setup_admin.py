"""PlannedEducation - Initial Superadmin & School Setup Script.

Executed during deployment (install.ps1 / install.sh) to create or update
the primary Superadmin user and school record, generating 5 emergency
recovery codes.
"""

from __future__ import annotations

import os
import sys

# Ensure src/ is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_dir = os.path.join(repo_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Try loading .env from working directory or repo root if JWT_SECRET_KEY not set
if not os.environ.get("JWT_SECRET_KEY"):
    for env_path in [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(repo_root, ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"),
    ]:
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            break

# F-031: refuse predictable JWT / admin password defaults (fail closed).
_PREDICTABLE_PASSWORDS = {
    "",
    "AdminPassword123!",
    "ChangeMe123!",
    "changeme",
    "password",
    "admin",
}
_PREDICTABLE_JWT = {
    "",
    "temporary-setup-secret-key-32-chars-long!",
    "your-super-secret-jwt-key-change-in-production-min-64-chars",
}

if not os.environ.get("JWT_SECRET_KEY") or os.environ.get("JWT_SECRET_KEY") in _PREDICTABLE_JWT:
    print(
        "ERROR: JWT_SECRET_KEY must be set to a strong unique value before admin setup.",
        file=sys.stderr,
    )
    sys.exit(2)

from plannededucation.api import auth
from plannededucation.api.database import Base, SessionLocal, engine
from plannededucation.api.models import School, User, UserRole
from plannededucation.api.routes_auth import _encode_recovery_codes, get_password_hash


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        school_name = os.environ.get("PE_SCHOOL_NAME", "PlannedEducation School")
        if not db.query(School).first():
            db.add(School(name=school_name, address="Local Campus"))
            db.commit()

        email = os.environ.get("PE_ADMIN_EMAIL") or os.environ.get("ADMIN_EMAIL")
        pwd = os.environ.get("PE_ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD")
        name = os.environ.get("PE_ADMIN_NAME") or os.environ.get("ADMIN_NAME", "School Administrator")
        if not email:
            print("ERROR: PE_ADMIN_EMAIL / ADMIN_EMAIL is required.", file=sys.stderr)
            return 2
        if not pwd or pwd in _PREDICTABLE_PASSWORDS or len(pwd) < 12:
            print(
                "ERROR: PE_ADMIN_PASSWORD must be set to a strong unique password "
                "(min 12 chars; predictable defaults are rejected).",
                file=sys.stderr,
            )
            return 2
        uname = email.split("@")[0] or "admin"

        from plannededucation.api.schema_ensure import ensure_schema
        ensure_schema(engine)

        plain_recovery_codes = auth.generate_recovery_codes(count=5)
        hashed_codes = [auth.hash_recovery_code(c) for c in plain_recovery_codes]

        existing = db.query(User).filter((User.email == email) | (User.username == uname)).first()
        if existing:
            existing.email = email
            existing.hashed_password = get_password_hash(pwd)
            existing.full_name = name
            existing.role = UserRole.admin.value
            existing.is_admin = True
            existing.is_superadmin = True
            existing.is_active = True
            existing.force_password_reset = True
            existing.recovery_codes = _encode_recovery_codes(hashed_codes)
            # Invalidate any prior sessions for the bootstrap admin.
            existing.refresh_token_hash = None
            existing.refresh_token_expires = None
            db.commit()
            print(f"Updated existing Admin user: {email}")
        else:
            admin = User(
                username=uname,
                email=email,
                hashed_password=get_password_hash(pwd),
                full_name=name,
                role=UserRole.admin.value,
                is_admin=True,
                is_superadmin=True,
                is_active=True,
                force_password_reset=True,
                recovery_codes=_encode_recovery_codes(hashed_codes),
            )
            db.add(admin)
            db.commit()
            print(f"Created initial Admin user: {email}")

        print("\n" + "=" * 68)
        print("  [KEY] SUPERADMIN EMERGENCY RECOVERY CODES")
        print("=" * 68)
        for i, code in enumerate(plain_recovery_codes, 1):
            print(f"    Code {i}: {code}")
        print("=" * 68)
        print("  [!] CRITICAL NOTICE FOR ADMINISTRATOR:")
        print("  Store these 5 one-time recovery codes safely (print or write them down).")
        print("  Password is NOT written to disk by this script.")
        print("  If you lose your administrator password and recovery codes, you will")
        print("  be permanently locked out and may need to redeploy the whole system.")
        print("=" * 68 + "\n")

        # Recovery codes only — never the admin password (F-031).
        with open("admin_recovery_codes.tmp", "w", encoding="utf-8") as f:
            f.write("\n".join(plain_recovery_codes))
        try:
            os.chmod("admin_recovery_codes.tmp", 0o600)
        except OSError:
            pass

        return 0
    except Exception as e:
        print(f"Error creating admin user: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
