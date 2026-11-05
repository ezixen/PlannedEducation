import json
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/en/messages.json', 'r', encoding='utf-8') as f:
    en = json.load(f)

# Add settings.i18n keys
i18n_keys = {
    'settings.i18n.title': 'Language & Translation',
    'settings.i18n.desc': 'Configure language and translation display options',
    'settings.i18n.language': 'Language',
    'settings.i18n.language_hint': 'Changes take effect immediately. Translations are community-contributed.',
    'settings.i18n.show_numbers': 'Show Translation Numbers',
    'settings.i18n.show_numbers_desc': 'Display numbered badges on all translatable elements. Hover for context and jump-to functionality.',
    'settings.i18n.help_title': 'How Translation Numbers Work',
    'settings.i18n.help_1': 'Each translatable element has a unique number (e.g., <code>login.3</code> = "Email" field on login page)',
    'settings.i18n.help_2': 'Enable "Show Translation Numbers" to see badges on all translatable elements',
    'settings.i18n.help_3': 'Hover any numbered element to see its key, English text, and context',
    'settings.i18n.help_4': 'Click "Jump" in tooltip or press Enter on focused element to center it on screen',
    'settings.i18n.help_5': 'FAQ chatbot shows translation keys - click to jump directly to that element',
    'settings.i18n.help_6': 'Translators: use the key (e.g., <code>login.3</code>) to find and translate the correct text in locale files',
    'settings.i18n.translator_guide': 'Open Translator Context Guide (CONTEXT.md)',
    'settings.i18n.translator_guide_desc': 'Detailed context for every translation key: location, purpose, constraints, and screenshots.',
    'settings.i18n.contribute_title': 'Help Translate PlannedEducation',
    'settings.i18n.contribute_desc': 'Missing your language? Found a mistake? Contributions welcome!',
    'settings.i18n.contribute_github': 'View Locale Files on GitHub',
    'settings.i18n.contribute_issue': 'Report Translation Issue',
}

en.update(i18n_keys)

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/en/messages.json', 'w', encoding='utf-8') as f:
    json.dump(en, f, ensure_ascii=False, indent=2)
print('Added settings.i18n keys to English')