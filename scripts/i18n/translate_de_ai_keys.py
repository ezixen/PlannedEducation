import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)

translations = {
    'ai_keys.1': 'AI-Schlüssel-Verwaltung',
    'ai_keys.2': 'Konfigurieren Sie Ihren AI-Anbieter für Bewertung und Inhaltsgenerierung',
    'ai_keys.3': 'AI-Anbieter',
    'ai_keys.4': 'Modell',
    'ai_keys.5': 'API-Schlüssel',
    'ai_keys.6': 'Basis-URL (optional)',
    'ai_keys.7': 'AI-Schlüssel Speichern',
    'ai_keys.8': 'AI-Schlüssel Gespeichert',
    'ai_keys.9': 'Kein AI-Schlüssel Konfiguriert',
    'ai_keys.10': 'Unterstützte Anbieter',
    'ai_keys.11': 'Gemini (Google)',
    'ai_keys.12': 'OpenRouter',
    'ai_keys.13': 'Ollama (Lokal)',
    'ai_keys.14': 'OpenAI Kompatibel',
    'ai_keys.15': 'ChatGPT Sitzung',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)
de.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'w', encoding='utf-8') as f:
    json.dump(de, f, ensure_ascii=False, indent=2)
print('Updated ai_keys section')