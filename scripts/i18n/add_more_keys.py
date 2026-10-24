import os
import re
import json
import time
import urllib.request
import urllib.parse
import sys

EN_PATH = "web/apps/portal/src/locales/en/messages.json"
LOCALES_DIR = "web/apps/portal/src/locales"

NEW_KEYS = {
    "common.cancel": "Cancel",
    "ai_grading.digitized_extracted_text": "Digitized Extracted Text:",
    "ai_grading.no_text_extracted": "(No text extracted)",
    "ai_grading.step_by_step_solution": "Step-by-Step Correct Solution:",
    "ai_grading.score_out_of_10": "(out of 10):",
    "ai_grading.chip_great_work": "Great work!",
    "ai_grading.chip_check_algebra": "Check algebra in step 2",
    "ai_grading.chip_review_units": "Review physical units",
    "ai_grading.chip_clear_derivation": "Clear derivation",
    "ai_grading.chip_partial_credit": "Partial credit",
    "ai_grading.no_image_photo": "No image photo attached for this submission.",
    "ai_grading.supported_formats_desc": "Supports photos from mobile cameras, scans, PNG, JPG, JPEG, and PDF.",
    "ai_grading.students_count": "{count} students",
    "ai_grading.submissions_approved_success": "{count} submissions approved!",
    "ai_grading.approve_error": "Error approving submissions",
    "student_dashboard.score_pts": "{score} / 10 pts",
    "student_dashboard.graded": "Graded",
    "parent.no_feedback": "No feedback recorded yet."
}

# 1. Update en/messages.json
with open(EN_PATH, "r", encoding="utf-8") as f:
    en_data = json.load(f)

for k, v in NEW_KEYS.items():
    en_data[k] = v

with open(EN_PATH, "w", encoding="utf-8") as f:
    json.dump(en_data, f, ensure_ascii=False, indent=2)

print(f"Updated en/messages.json, total keys: {len(en_data)}", flush=True)

LANG_CODES = {
    'ar': 'ar', 'cn': 'zh-CN', 'cs': 'cs', 'da': 'da', 'de': 'de', 'el': 'el',
    'es': 'es', 'fi': 'fi', 'fr': 'fr', 'he': 'iw', 'hu': 'hu', 'id': 'id',
    'it': 'it', 'ja': 'ja', 'ko': 'ko', 'nl': 'nl', 'no': 'no', 'pl': 'pl',
    'pt': 'pt', 'pt-BR': 'pt', 'ru': 'ru', 'sv': 'sv', 'th': 'th', 'tr': 'tr',
    'uk': 'uk', 'vi': 'vi',
}

def translate_strings(strings, tl):
    res = {}
    combined = " ||| ".join(strings)
    url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl={tl}&q={urllib.parse.quote(combined)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data[0] if isinstance(data[0], str) else data[0][0]
            parts = [p.strip() for p in re.split(r'\s*\|\|\|\s*|\s*｜｜｜\s*', raw)]
            if len(parts) == len(strings):
                for orig, trans in zip(strings, parts):
                    res[orig] = trans
                return res
    except Exception:
        pass

    # fallback per item
    for s in strings:
        try:
            single_url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl={tl}&q={urllib.parse.quote(s)}"
            s_req = urllib.request.Request(single_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(s_req, timeout=6) as r:
                d = json.loads(r.read().decode("utf-8"))
                t = d[0] if isinstance(d[0], str) else d[0][0]
                res[s] = t.strip()
        except Exception:
            res[s] = s
        time.sleep(0.02)
    return res

strings_to_translate = list(NEW_KEYS.values())

for locale, tl in LANG_CODES.items():
    loc_file = os.path.join(LOCALES_DIR, locale, "messages.json")
    if os.path.exists(loc_file):
        with open(loc_file, "r", encoding="utf-8") as f:
            loc_data = json.load(f)
    else:
        loc_data = {}

    missing_keys = [k for k in NEW_KEYS if k not in loc_data]
    if missing_keys:
        t_map = translate_strings([NEW_KEYS[k] for k in missing_keys], tl)
        for k in missing_keys:
            en_val = NEW_KEYS[k]
            loc_data[k] = t_map.get(en_val, en_val)

        with open(loc_file, "w", encoding="utf-8") as f:
            json.dump(loc_data, f, ensure_ascii=False, indent=2)
        print(f"[{locale}] Added {len(missing_keys)} translated keys.")
    else:
        print(f"[{locale}] Up to date.")

print("All locales updated!")

