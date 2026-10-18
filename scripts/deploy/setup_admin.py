"""PlannedEducation - Initial Superadmin & School Setup Script.

Executed during deployment (install.ps1 / install.sh) to create or update
the primary Superadmin user and school record, generating 5 emergency
recovery codes.
"""

from __future__ import annotations

import hashlib
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
    if not os.environ.get("JWT_SECRET_KEY"):
        os.environ.setdefault("JWT_SECRET_KEY", "temporary-setup-secret-key-32-chars-long!")

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

        email = os.environ.get("PE_ADMIN_EMAIL", "admin@yourschool.edu")
        pwd = os.environ.get("PE_ADMIN_PASSWORD", "AdminPassword123!")
        name = os.environ.get("PE_ADMIN_NAME", "School Administrator")
        uname = email.split("@")[0] or "admin"

        plain_recovery_codes = auth.generate_recovery_codes(count=5)
        hashed_codes = [hashlib.sha256(c.encode()).hexdigest() for c in plain_recovery_codes]

        existing = db.query(User).filter((User.email == email) | (User.username == uname)).first()
        if existing:
            existing.email = email
            existing.hashed_password = get_password_hash(pwd)
            existing.full_name = name
            existing.role = UserRole.admin.value
            existing.is_admin = True
            existing.is_active = True
            existing.recovery_codes = _encode_recovery_codes(hashed_codes)
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
                is_active=True,
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
        print("  If you lose your administrator password and recovery codes, you will")
        print("  be permanently locked out and may need to redeploy the whole system,")
        print("  as direct database injection is blocked for security.")
        print("=" * 68 + "\n")

        with open("admin_recovery_codes.tmp", "w", encoding="utf-8") as f:
            f.write("\n".join(plain_recovery_codes))

        return 0
    except Exception as e:
        print(f"Error creating admin user: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
