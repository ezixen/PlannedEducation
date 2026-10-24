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
    "ai_grading.review": "Review & Grade",
    "ai_grading.status_ungraded": "Pending Review",
    "ai_grading.status_ai_graded": "AI Graded",
    "ai_grading.status_teacher_graded": "Teacher Graded",
    "ai_grading.status_returned": "Returned to Student",
    "ai_grading.status_pending_approval": "Pending Approval",
    "ai_grading.status_graded": "Graded",
    "ai_grading.upload_success": "Exam uploaded and registered for AI grading!",
    "ai_grading.upload_error": "Upload failed",
    "ai_grading.ai_grade_success": "AI grading completed and staged!",
    "ai_grading.return_success": "Exam returned to student!",
    "ocr.desc": "Extract text from handwritten exam images using Tesseract OCR. Supports math expressions and multiple languages.",
    "ocr.language_label": "Language",
    "ocr.confidence": "Confidence: {percent}%",
    "ocr.error": "Error: {error}",
    "ocr.no_text_detected": "(No text detected)",
    "ocr.select_image_first": "Please select an image first.",
    "ocr.completed_confidence": "OCR completed with {percent}% confidence",
    "ocr.processing_failed": "OCR processing failed."
}

# 1. Update en/messages.json
with open(EN_PATH, "r", encoding="utf-8") as f:
    en_data = json.load(f)

for k, v in NEW_KEYS.items():
    en_data[k] = v

with open(EN_PATH, "w", encoding="utf-8") as f:
    json.dump(en_data, f, ensure_ascii=False, indent=2)

print(f"Updated en/messages.json, total canonical keys: {len(en_data)}", flush=True)

LANG_CODES = {
    'ar': 'ar',
    'cn': 'zh-CN',
    'cs': 'cs',
    'da': 'da',
    'de': 'de',
    'el': 'el',
    'es': 'es',
    'fi': 'fi',
    'fr': 'fr',
    'he': 'iw',
    'hu': 'hu',
    'id': 'id',
    'it': 'it',
    'ja': 'ja',
    'ko': 'ko',
    'nl': 'nl',
    'no': 'no',
    'pl': 'pl',
    'pt': 'pt',
    'pt-BR': 'pt',
    'ru': 'ru',
    'sv': 'sv',
    'th': 'th',
    'tr': 'tr',
    'uk': 'uk',
    'vi': 'vi',
}

KNOWN_UNIVERSAL = {
    'PDF', 'LaTeX', 'STT', 'OCR', 'SEB', 'JSON', 'ZIP', 'CSV',
    'Planned Education', 'PlannedEducation', 'Email', 'URL', 'IP',
    'PIN', '2FA', 'ID', 'WebAuthn'
}

def translate_chunk(chunk, tl):
    combined = " ||| ".join(chunk)
    url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl={tl}&q={urllib.parse.quote(combined)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data[0] if isinstance(data[0], str) else data[0][0]
                parts = [p.strip() for p in re.split(r'\s*\|\|\|\s*|\s*｜｜｜\s*', raw_text)]
                if len(parts) == len(chunk):
                    return parts
                break
        except Exception as e:
            time.sleep(0.5 + attempt)
            
    # Fallback item-by-item
    res = []
    for s in chunk:
        try:
            single_url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl={tl}&q={urllib.parse.quote(s)}"
            s_req = urllib.request.Request(single_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(s_req, timeout=8) as r:
                d = json.loads(r.read().decode("utf-8"))
                t = d[0] if isinstance(d[0], str) else d[0][0]
                res.append(t.strip())
        except Exception:
            res.append(s)
        time.sleep(0.03)
    return res

def process_single_locale(locale):
    tl = LANG_CODES[locale]
    loc_file = os.path.join(LOCALES_DIR, locale, "messages.json")
    
    if not os.path.exists(loc_file):
        loc_data = {}
    else:
        with open(loc_file, "r", encoding="utf-8") as f:
            loc_data = json.load(f)

    # Find keys that need translation
    to_translate = []
    for k, en_text in en_data.items():
        curr = loc_data.get(k)
        is_leak = (curr == en_text and len(en_text.strip()) > 3 and re.search(r'[a-zA-Z]{3,}', en_text))
        if is_leak and en_text.strip() in KNOWN_UNIVERSAL:
            is_leak = False
        if not curr or is_leak:
            if en_text not in to_translate:
                to_translate.append(en_text)

    if not to_translate:
        print(f"[{locale:5s}] 100% complete (0 pending).", flush=True)
        return

    print(f"[{locale:5s}] Translating {len(to_translate)} strings...", flush=True)
    start = time.time()
    trans_map = {}
    BATCH = 15

    for i in range(0, len(to_translate), BATCH):
        chunk = to_translate[i:i + BATCH]
        parts = translate_chunk(chunk, tl)
        for orig, tr in zip(chunk, parts):
            trans_map[orig] = tr
        time.sleep(0.05)

    # Update dictionary
    for k, en_text in en_data.items():
        curr = loc_data.get(k)
        is_leak = (curr == en_text and len(en_text.strip()) > 3 and re.search(r'[a-zA-Z]{3,}', en_text))
        if is_leak and en_text.strip() in KNOWN_UNIVERSAL:
            is_leak = False
        
        if not curr or is_leak:
            loc_data[k] = trans_map.get(en_text, en_text)

    with open(loc_file, "w", encoding="utf-8") as f:
        json.dump(loc_data, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    print(f"[{locale:5s}] Finished {len(to_translate)} in {elapsed:.1f}s.", flush=True)

# Process all locales
for loc in sorted(LANG_CODES.keys()):
    process_single_locale(loc)

print("Translation check completed for all 26 locales.", flush=True)
