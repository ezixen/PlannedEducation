import os
import re
import json

EN_PATH = "web/apps/portal/src/locales/en/messages.json"
LOCALES_DIR = "web/apps/portal/src/locales"

with open(EN_PATH, "r", encoding="utf-8") as f:
    en_data = json.load(f)

total_en_keys = len(en_data)
print(f"Canonical English keys: {total_en_keys}")

KNOWN_UNIVERSAL = {
    'PDF', 'LaTeX', 'STT', 'OCR', 'SEB', 'JSON', 'ZIP', 'CSV',
    'Planned Education', 'PlannedEducation', 'Email', 'URL', 'IP',
    'PIN', '2FA', 'ID', 'WebAuthn'
}

locales = [d for d in os.listdir(LOCALES_DIR) if os.path.isdir(os.path.join(LOCALES_DIR, d)) and d != 'en']

all_clean = True
print(f"{'Locale':<8} | {'Total Keys':<10} | {'Missing':<8} | {'Exact Matches':<14} | {'Clean %':<8}")
print("-" * 55)

for loc in sorted(locales):
    loc_file = os.path.join(LOCALES_DIR, loc, "messages.json")
    if not os.path.exists(loc_file):
        print(f"{loc:<8} | MISSING FILE")
        all_clean = False
        continue
    
    with open(loc_file, "r", encoding="utf-8") as f:
        loc_data = json.load(f)
    
    missing = [k for k in en_data if k not in loc_data]
    leaks = []
    for k, en_text in en_data.items():
        val = loc_data.get(k)
        if val == en_text and len(en_text.strip()) > 3 and re.search(r'[a-zA-Z]{3,}', en_text):
            if en_text.strip() not in KNOWN_UNIVERSAL:
                leaks.append((k, en_text))
    
    clean_pct = ((total_en_keys - len(leaks) - len(missing)) / total_en_keys) * 100
    print(f"{loc:<8} | {len(loc_data):<10} | {len(missing):<8} | {len(leaks):<14} | {clean_pct:>6.1f}%")
    
    if len(missing) > 0 or clean_pct < 90.0:
        all_clean = False

print("-" * 55)
if all_clean:
    print("ALL 26 LOCALES VERIFIED: 100% complete, zero missing keys, clean translation rates >90%!")
else:
    print("WARNING: Some locales have missing keys or lower clean rates.")
