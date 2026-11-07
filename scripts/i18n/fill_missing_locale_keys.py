"""
Translate missing keys from en/messages.json into every non-EN locale.

Uses the same free Google Translate endpoint as translate_all_eu_languages.py.
Only fills keys that are absent; does not overwrite existing translations.
Skips when --en-fill is set (copies English instead of translating).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EN_PATH = ROOT / "web" / "apps" / "portal" / "src" / "locales" / "en" / "messages.json"
LOCALES_DIR = ROOT / "web" / "apps" / "portal" / "src" / "locales"

# Locale folder -> Google Translate target code
LANG_CODES = {
    "ar": "ar",
    "bg": "bg",
    "cn": "zh-CN",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "el": "el",
    "es": "es",
    "et": "et",
    "fi": "fi",
    "fr": "fr",
    "ga": "ga",
    "he": "iw",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "it": "it",
    "ja": "ja",
    "ko": "ko",
    "lt": "lt",
    "lv": "lv",
    "mt": "mt",
    "nl": "nl",
    "no": "no",
    "pl": "pl",
    "pt": "pt",
    "pt-BR": "pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl": "sl",
    "sv": "sv",
    "th": "th",
    "tr": "tr",
    "uk": "uk",
    "vi": "vi",
}

KNOWN_UNIVERSAL = {
    "PDF",
    "LaTeX",
    "STT",
    "OCR",
    "SEB",
    "JSON",
    "ZIP",
    "CSV",
    "Planned Education",
    "PlannedEducation",
    "Email",
    "URL",
    "IP",
    "PIN",
    "2FA",
    "ID",
    "WebAuthn",
}


def translate_chunk_api(chunk: list[str], target_lang: str) -> dict[str, str]:
    res: dict[str, str] = {}
    if not chunk:
        return res
    combined = " ||| ".join(chunk)
    url = (
        "https://clients5.google.com/translate_a/t"
        f"?client=dict-chrome-ex&sl=en&tl={target_lang}&q={urllib.parse.quote(combined)}"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            raw = data[0] if isinstance(data[0], str) else data[0][0]
            parts = [p.strip() for p in re.split(r"\s*\|{2,3}\s*|\s*｜{2,3}｜*\s*", raw)]
            if len(parts) == len(chunk):
                for orig, trans in zip(chunk, parts):
                    res[orig] = trans
                return res
    except Exception as exc:  # noqa: BLE001
        print(f"  chunk translate failed ({target_lang}): {exc}", flush=True)

    for s in chunk:
        s_clean = s.strip()
        if s_clean in KNOWN_UNIVERSAL or not s_clean:
            res[s] = s
            continue
        try:
            s_url = (
                "https://clients5.google.com/translate_a/t"
                f"?client=dict-chrome-ex&sl=en&tl={target_lang}&q={urllib.parse.quote(s)}"
            )
            s_req = urllib.request.Request(s_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(s_req, timeout=8) as r:
                d = json.loads(r.read().decode("utf-8"))
                val = d[0] if isinstance(d[0], str) else d[0][0]
                res[s] = val.strip()
        except Exception:
            res[s] = s
        time.sleep(0.02)
    return res


def fill_locale(loc: str, tl: str, en_data: dict[str, str], en_fill: bool) -> tuple[str, int]:
    loc_file = LOCALES_DIR / loc / "messages.json"
    if not loc_file.exists():
        return loc, 0
    loc_data = json.loads(loc_file.read_text(encoding="utf-8"))
    missing = [k for k in en_data if k not in loc_data]
    if not missing:
        print(f"[{loc}] up to date ({len(loc_data)} keys)", flush=True)
        return loc, 0

    print(f"[{loc}] filling {len(missing)} missing keys via {'EN-fill' if en_fill else tl}…", flush=True)
    batch = 25
    for i in range(0, len(missing), batch):
        chunk_keys = missing[i : i + batch]
        chunk_vals = [en_data[k] for k in chunk_keys]
        if en_fill:
            t_map = {v: v for v in chunk_vals}
        else:
            t_map = translate_chunk_api(chunk_vals, tl)
        for k, val in zip(chunk_keys, chunk_vals):
            loc_data[k] = t_map.get(val, val)
        done = min(i + batch, len(missing))
        pct = int(done / len(missing) * 100)
        print(f"  [{loc}] {done}/{len(missing)} ({pct}%)", flush=True)
        loc_file.write_text(
            json.dumps(loc_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        time.sleep(0.05)

    print(f"[{loc}] done — {len(loc_data)} keys", flush=True)
    return loc, len(missing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--en-fill", action="store_true", help="Copy EN text instead of translating")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--only", nargs="*", help="Optional locale folder names to process")
    args = parser.parse_args()

    en_data = json.loads(EN_PATH.read_text(encoding="utf-8"))
    targets = {
        loc: tl
        for loc, tl in LANG_CODES.items()
        if (not args.only or loc in args.only) and (LOCALES_DIR / loc / "messages.json").exists()
    }

    print(
        f"[PROGRESS] Filling missing keys for {len(targets)} locales "
        f"(EN keys={len(en_data)}, workers={args.workers})",
        flush=True,
    )
    start = time.time()
    total_filled = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {
            ex.submit(fill_locale, loc, tl, en_data, args.en_fill): loc
            for loc, tl in sorted(targets.items())
        }
        for fut in concurrent.futures.as_completed(futs):
            loc = futs[fut]
            try:
                _, n = fut.result()
                total_filled += n
            except Exception as exc:  # noqa: BLE001
                print(f"[{loc}] ERROR: {exc}", file=sys.stderr, flush=True)

    elapsed = time.time() - start
    print(
        f"[PROGRESS] Complete: filled keys across locales in {elapsed:.1f}s "
        f"(sum of missing slots={total_filled})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
