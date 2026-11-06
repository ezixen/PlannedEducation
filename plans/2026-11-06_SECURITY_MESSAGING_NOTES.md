# Security & messaging truth — 2026-11-06

## Encryption model (current)

| Layer | What | Mechanism |
|-------|------|-----------|
| Auth secrets | `totp_secret`, `recovery_codes`, `webauthn_*` | Fernet field encryption when `DATABASE_ENCRYPTION=true` |
| Chats | `DirectMessage.content`, `TeacherLoungeMessage.content` | Fernet field encryption |
| Notifications | `InAppNotification.message`, `action_payload` | Fernet field encryption |
| OCR review text | `original_text`, `corrected_text`, … | Fernet field encryption |
| AI provider keys | `ai_api_key_encrypted` | Separate Fernet via `AI_KEY_MASTER_SECRET` |
| Lookup PII | `email`, `username`, `full_name` | **Not** field-encrypted (required for SQL equality login filters); protected by host/DB ACLs + optional SQLCipher for SQLite files |
| Passwords | `hashed_password` | Argon2id (never reversible) |

## Installer / env truth

- `install.ps1` / `install.sh` now emit `DATABASE_ENCRYPTION=true` and a **distinct** `DB_ENCRYPTION_MASTER_KEY`.
- `.env.example` documents the same.
- Keys must differ: JWT ≠ AI Fernet ≠ DB Fernet.

## Messaging policy truth

- Student↔student DMs forbidden.
- Student→teacher DMs disabled until teacher enables `allow_student_dms`.
- Teachers' Lounge directory lists approved teachers + admins with `is_visible_in_teacher_dm`.
- Superadmin sets always-visible `admin_support_email`.

## OWASP-aligned controls (existing)

- A01 access control on DM/lounge/aide routes
- A02 secure defaults / CSP / TrustedHost in API
- A03 pip-audit + npm audit in CI
- A04 Argon2id, Fernet, short-lived JWT
- A07 Google SSO + TOTP + passkeys + recovery codes + rate limits on auth paths
- A09 structured logs; secrets not logged
