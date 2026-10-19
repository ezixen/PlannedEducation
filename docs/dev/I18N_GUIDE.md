# PlannedEducation i18n Translation Guide

## Overview

This document describes the internationalization (i18n) system for PlannedEducation, including how translations work, how to add new languages, and how to contribute translations.

## System Overview

PlannedEducation uses a **numbered key system** for translations with the format `page.element` (e.g., `login.1`, `dashboard.3`, `settings.12.3`). This allows:

- **Visual identification** of translatable elements on the UI
- **Easy synchronization** between English source and translations
- **Context-aware translation** with detailed context documentation
- **Visual toggle** for translation numbers in the UI

## File Structure

```
web/apps/portal/src/locales/
├── en/
│   ├── messages.json      # Source English translations (436 keys)
│   └── CONTEXT.md         # Detailed context for each key
├── hu/
│   └── messages.json      # Hungarian translations (436 keys)
├── es/
│   └── messages.json      # Spanish translations (to be created)
├── de/
│   └── messages.json      # German translations (to be created)
├── fr/
│   └── messages.json      # French translations (to be created)
├── ja/
│   └── messages.json      # Japanese translations (to be created)
├── zh/
│   └── messages.json      # Chinese translations (to be created)
└── CONTEXT.md             # Master context documentation
```

## Key Format

Keys follow the format: `page.element` where:
- `page` = page/section identifier (e.g., `login`, `dashboard`, `settings`, `exam_editor`)
- `element` = sequential number within that page (e.g., `1`, `2`, `3`, `10.1`, `10.2`)

Examples:
- `login.1` = "Planned Education" (page title)
- `login.3` = "Email address" (label)
- `settings.12.3` = "API Key" (sub-item under AI Key Management)

## Translation Rules

### 1. Keep in English (Do Not Translate)
- **Brand names**: "Planned Education", "Google", "GitHub", "OpenAI", "Ollama"
- **Technical terms**: API, URL, PDF, OAuth, JWT, JSON, YAML, HTML, CSS, JS, SQL, UUID, UUID, HTTP, HTTPS, REST, GraphQL, WebSocket, WebRTC, SEB, GDPR, OCR, STT, TTS, AI, LLM, RAG, RTP, RTCP, ICE, STUN, TURN, SDP, DTLS, SRTP, SRTCP, RTCP, RTP, RTCP
- **Proper nouns**: Planned Education, Google, GitHub, OpenAI, Ollama, OpenRouter, Anthropic, Claude, Gemini, ChatGPT, iCloud, Keychain, Windows Hello, Touch ID, Face ID, PIN
- **Units**: KB, MB, GB, TB, Hz, MHz, GHz, ms, s, min, h, d, px, em, rem, %, °C, °F
- **Format strings**: `{variable}`, `%s`, `%d`, `%f`, `%.2f`, `{0}`, `{1}`, `{count}`, `{name}`

### 2. Translate Naturally
- Use formal/informal appropriately for the target language
- Maintain consistent terminology across the application
- Consider cultural context and regional variations

### 3. Special Cases
- **Brand names**: Keep "Planned Education" in English
- **Technical acronyms**: Keep SEO, API, URL, PDF, OAuth, JWT, etc. in English
- **Units**: Keep KB, MB, GB, ms, s, min, h, etc. as-is
- **Placeholders**: Keep `{variable}`, `%s`, `%d` as-is

## File Structure

### English Source (`en/messages.json`)
The source of truth with all 436 keys in `page.element` format.

### Translation Files (`{locale}/messages.json`)
Each locale has its own `messages.json` with the same keys but translated values.

### Context Documentation (`CONTEXT.md`)
Detailed context for each key including:
- Page/section location
- UI element type (button, label, input, tooltip, etc.)
- Action/behavior description
- Constraints (length, variables, formatting)
- Screenshots (when available)

## Adding a New Language

### 1. Create Locale Directory
```bash
mkdir -p web/apps/portal/src/locales/{locale_code}
```

### 2. Copy English Messages as Template
```bash
cp web/apps/portal/src/locales/en/messages.json web/apps/portal/src/locales/{locale_code}/messages.json
```

### 3. Translate Values
Edit the new `messages.json` file, replacing English values with translations while keeping:
- **Keys identical** (must match exactly)
- **JSON structure** identical
- **Placeholders** intact (`{variable}`, `%s`, etc.)

### 4. Add Locale to Supported List
Update `src/contexts/I18nContext.tsx`:
```typescript
const AVAILABLE_LOCALES: Locale[] = ['en', 'hu', 'es', 'de', 'fr', 'ja', 'zh', 'your_new_locale'];
const LOCALE_NAMES: Record<Locale, string> = {
  // ... existing entries
  your_new_locale: 'Native Name',
};
```

### 5. Test the Translation
```bash
# Build frontend
cd web/apps/portal && npm run build

# Run tests
cd ../../.. && python -m pytest tests/ -v
```

## Translation Workflow for Contributors

### For Translators
1. **Fork the repository** on GitHub
2. **Create a new branch**: `git checkout -b translation/{locale_code}`
3. **Edit the translation file**: `web/apps/portal/src/locales/{locale_code}/messages.json`
4. **Test locally** (optional): Run the frontend and switch to your language
5. **Submit a Pull Request** with your translations

### For Reviewers
- Verify all keys are present (no missing keys)
- Check that placeholders are preserved
- Ensure translations are natural and culturally appropriate
- Verify technical terms are kept in English
- Check that placeholders like `{variable}`, `%s` are preserved

## Helper Scripts

### Translation Coverage Check
```bash
# Check translation coverage for a locale
python scripts/i18n/check_translation_coverage.py --locale hu
```

### Generate Missing Keys Report
```bash
# Generate missing keys report
python scripts/i18n/check_translation_coverage.py --locale es --report-only
```

### Validate JSON Syntax
```bash
# Validate JSON syntax for all locale files
python -m json.tool web/apps/portal/src/locales/*/messages.json > /dev/null
```

## Translation Guidelines by Language

### Spanish (es)
- Use formal "usted" form for UI text
- Use "usted" form for buttons and labels
- Regional: Prefer neutral Latin American Spanish

### German (de)
- Use formal "Sie" form
- Compound words are common (e.g., "Passwortverwaltung")
- Formal address for UI elements

### French (fr)
- Use formal "vous" form
- Accents and diacritics must be correct
- Gender agreement for nouns/adjectives

### Japanese (ja)
- Use polite form (desu/masu)
- Katakana for technical terms
- Kanji for common words, hiragana for particles

### Chinese (zh)
- Simplified characters for mainland China
- Traditional characters for Taiwan/Hong Kong (separate locale if needed)
- Formal tone for UI

## Quality Assurance

### Automated Checks
- All keys present in each locale
- No missing translations
- Placeholders preserved
- JSON syntax valid
- No duplicate keys

### Manual Review
- Native speaker review for each language
- Context-aware translation verification
- UI testing with each language
- Accessibility check (screen readers, etc.)

## Context Documentation

The `CONTEXT.md` file provides detailed context for each translation key:
- **Page/Section**: Where the text appears
- **Element Type**: Button, label, input, tooltip, error message, etc.
- **Action/Behavior**: What happens when clicked/used
- **Constraints**: Character limits, variable placeholders, formatting
- **Related Keys**: Related translation keys

## Adding New Translation Keys

### For Developers
1. **Add key to English source**: Add new key to `en/messages.json`
2. **Update CONTEXT.md**: Add context documentation
3. **Run key extraction**: `python scripts/i18n/extract_keys.py`
4. **Update all locale files**: Run `python scripts/i18n/sync_locales.py`

### Key Naming Convention
- Use `page.element` format
- Page names: lowercase, singular (login, register, dashboard, settings)
- Element numbers: sequential integers, sub-elements with decimal (10.1, 10.2)
- Group related items under same page prefix

## Testing Translations

### Local Testing
```bash
# Start frontend with specific locale
cd web/apps/portal
npm run dev -- --locale=hu
```

### Automated Testing
```bash
# Run i18n tests
python -m pytest tests/test_i18n.py -v
```

## Contributing Translations

### Pull Request Template
```markdown
## Translation: [Language Name] ([locale_code])

### Changes
- Added/updated translations for [number] keys
- Language: [Language Name] ([locale_code])

### Checklist
- [ ] All 436 keys translated
- [ ] Placeholders preserved ({variable}, %s, etc.)
- [ ] Technical terms kept in English
- [ ] Brand names kept in English
- [ ] JSON syntax valid
- [ ] No missing keys
- [ ] Tested in browser

### Screenshots (optional)
- Screenshots of UI in target language
```

## Maintenance

### Regular Tasks
- Monthly: Check for new keys in English source
- Quarterly: Review translation quality with native speakers
- Per release: Verify all locales have complete translations

### Deprecation Process
1. Mark deprecated keys with `_deprecated` suffix
2. Keep for 2 major versions
3. Remove after deprecation period

## Resources

### Useful Links
- [Unicode CLDR](https://cldr.unicode.org/) - Locale data
- [Unicode CLDR Charts](https://cldr.unicode.org/index/charts) - Locale charts
- [W3C Internationalization](https://www.w3.org/International/) - Best practices
- [Mozilla L10n Guide](https://developer.mozilla.org/en-US/docs/Mozilla/Localization) - Best practices

### Tools
- [Poedit](https://poedit.net/) - PO file editor
- [Lokalise](https://lokalise.com/) - Translation management
- [Crowdin](https://crowdin.com/) - Translation management platform
- [Weblate](https://weblate.org/) - Web-based translation platform

---

## Quick Reference

### Commands
```bash
# Check translation coverage
python scripts/i18n/check_translation_coverage.py --locale es

# Validate all locale files
python -m json.tool web/apps/portal/src/locales/*/messages.json > /dev/null

# Build frontend with locale
cd web/apps/portal && npm run build -- --locale=es

# Run i18n tests
python -m pytest tests/test_i18n.py -v
```

### File Locations
```
web/apps/portal/src/locales/
├── en/messages.json          # Source (436 keys)
├── en/CONTEXT.md             # Context documentation
├── hu/messages.json          # Hungarian (complete)
├── es/messages.json          # Spanish (to be created)
├── de/messages.json          # German (to be created)
├── fr/messages.json          # French (to be created)
├── ja/messages.json          # Japanese (to be created)
├── zh/messages.json          # Chinese (to be created)
└── CONTEXT.md                # Master context doc
```

### Key Files
- `src/contexts/I18nContext.tsx` - Locale management
- `src/components/I18nNumber.tsx` - Visual number badges
- `src/components/I18nSettings.tsx` - Settings UI
- `src/components/I18nNumber.css` - Styles
- `src/utils/i18n.ts` - Translation utilities (if exists)

---

*Last updated: 2026-10-14*
*Version: 1.0*