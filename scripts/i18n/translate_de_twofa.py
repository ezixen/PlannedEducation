import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)

translations = {
    'twofa.1': 'Zwei-Faktor-Authentifizierung',
    'twofa.2': 'QR-Code Scannen',
    'twofa.3': 'Geben Sie den 6-stelligen Code aus der Authenticator-App ein',
    'twofa.4': 'Verifizieren',
    'twofa.5': '2FA Aktiviert',
    'twofa.6': 'Wiederherstellungscodes',
    'twofa.7': 'Bewahren Sie diese Codes sicher auf',
    'twofa.8': 'Jeder Code kann nur einmal verwendet werden',
    'twofa.9': '2FA Deaktivieren',
    'twofa.10': 'Geben Sie den Wiederherstellungscode zur Deaktivierung ein',
    'twofa.11': '2FA Deaktiviert',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)
de.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'w', encoding='utf-8') as f:
    json.dump(de, f, ensure_ascii=False, indent=2)
print('Updated twofa section')