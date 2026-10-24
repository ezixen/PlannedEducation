import json
import os

EN_PATH = "web/apps/portal/src/locales/en/messages.json"
TS_KEY_NUMBERS_PATH = "web/apps/portal/src/locales/keyNumbers.ts"
CONTEXT_PATHS = [
    "docs/dev/I18N_CONTEXT.md",
    "web/apps/portal/public/docs/dev/CONTEXT.md",
    "web/apps/portal/public/docs/dev/I18N_CONTEXT.md"
]

with open(EN_PATH, "r", encoding="utf-8") as f:
    en_data = json.load(f)

# Sort keys deterministically by category then key
sorted_keys = sorted(en_data.keys(), key=lambda k: (k.split('.')[0], k))

key_numbers = {}
for idx, key in enumerate(sorted_keys, start=1):
    key_numbers[key] = idx

# 1. Generate keyNumbers.ts
ts_lines = [
    "// Auto-generated key-to-number mapping for i18n translation system",
    "export const KEY_NUMBERS: Record<string, number> = {"
]
for k, num in key_numbers.items():
    safe_k = json.dumps(k)
    ts_lines.append(f"  {safe_k}: {num},")
ts_lines.append("};")
ts_lines.append("")
ts_lines.append("export function getKeyNumber(key: string): number | undefined {")
ts_lines.append("  return KEY_NUMBERS[key];")
ts_lines.append("}")
ts_lines.append("")

with open(TS_KEY_NUMBERS_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(ts_lines))
print(f"Generated {TS_KEY_NUMBERS_PATH} with {len(key_numbers)} entries")

# 2. Generate CONTEXT.md
md_lines = [
    "# PlannedEducation — Comprehensive Translation Context Guide (CONTEXT.md)",
    "",
    "This guide provides exact context, numbering, and descriptions for every translatable key in the PlannedEducation platform.",
    "Translators can enable **'Show Translation Numbers'** in Settings to view the exact `[#ID]` badge on each UI element,",
    "and cross-reference this document to ensure accurate, context-aware translations.",
    "",
    "## Key Index Format: `[#ID] category.element`",
    "- **#ID**: Unique numeric badge displayed in the UI when 'Show Translation Numbers' is active",
    "- **Key**: The identifier used in `web/apps/portal/src/locales/<locale>/messages.json`",
    "- **English**: Canonical source string",
    "- **Context**: Feature domain, target component, and display requirements",
    "",
    "---",
    ""
]

current_category = None
for k in sorted_keys:
    cat = k.split('.')[0]
    num = key_numbers[k]
    val = en_data[k]
    
    if cat != current_category:
        current_category = cat
        cat_title = cat.replace('_', ' ').capitalize()
        md_lines.append(f"## {cat_title} (`{cat}`)\n")
    
    # Generate helpful context description
    context_desc = f"Used in {cat.replace('_', ' ')} interface"
    if "button" in k or "btn" in k:
        context_desc = f"Action button in {cat.replace('_', ' ')} view"
    elif "title" in k or "header" in k:
        context_desc = f"Main heading / section header in {cat.replace('_', ' ')}"
    elif "desc" in k or "subtitle" in k or "hint" in k:
        context_desc = f"Descriptive paragraph or helper text in {cat.replace('_', ' ')}"
    elif "placeholder" in k:
        context_desc = f"Input placeholder text in {cat.replace('_', ' ')}"
    elif "label" in k:
        context_desc = f"Form input label in {cat.replace('_', ' ')}"
    elif "error" in k:
        context_desc = f"Validation or runtime error message in {cat.replace('_', ' ')}"
    elif "success" in k:
        context_desc = f"Confirmation / success alert message in {cat.replace('_', ' ')}"

    md_lines.append(f"### [#{num}] {k}")
    md_lines.append(f"**English:** {val}")
    md_lines.append(f"**Context:** {context_desc}\n")

context_content = "\n".join(md_lines)
for path in CONTEXT_PATHS:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(context_content)
    print(f"Generated {path} ({len(md_lines)} lines)")

print("All CONTEXT files and keyNumbers.ts generated successfully!")
