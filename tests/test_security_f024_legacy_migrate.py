"""F-024 residual: legacy plaintext archive re-encryption."""

from __future__ import annotations

import os

# Must be set before archive_utils imports key material.
os.environ.setdefault("PLANNED_EDUCATION_ENV", "test")
os.environ.setdefault(
    "ARCHIVE_MASTER_KEY",
    "v7CWWAUDs24iDP13c4m6urdnXYqap8u-uvoRyWlZMKk=",
)


def test_reencrypt_legacy_plaintext_round_trip():
    import asyncio

    from src.plannededucation.api.archive_utils import (
        ARCHIVE_ENCRYPTION_ALGORITHM,
        compress_data,
        decrypt_archive_data,
        get_archive_master_key,
        reencrypt_legacy_plaintext_row,
    )

    async def _run():
        key = get_archive_master_key(require=True)
        compressed = compress_data(b'{"submissionId":"legacy-1","answers":{}}')
        legacy_hex = compressed.hex()

        updated = await reencrypt_legacy_plaintext_row(legacy_hex, master_key=key)
        assert updated["encryption_algorithm"] == ARCHIVE_ENCRYPTION_ALGORITHM
        assert updated["encryption_iv"]
        assert updated["encryption_salt"]
        assert updated["compressed_data"] != legacy_hex

        plaintext = await decrypt_archive_data(
            bytes.fromhex(updated["compressed_data"]),
            bytes.fromhex(updated["encryption_iv"]),
            bytes.fromhex(updated["encryption_salt"]),
            key,
        )
        assert plaintext == compressed

    asyncio.run(_run())
