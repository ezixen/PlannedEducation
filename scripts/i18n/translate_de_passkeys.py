import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)

translations = {
    'passkeys.1': 'Passkeys',
    'passkeys.2': 'Passkey Registrieren',
    'passkeys.3': 'Verwenden Sie die Biometrie Ihres Geräts (Fingerabdruck, Face ID) oder PIN',
    'passkeys.4': 'Registrierte Passkeys',
    'passkeys.5': 'Erstellt',
    'passkeys.6': 'Zuletzt Verwendet',
    'passkeys.7': 'Löschen',
    'passkeys.7.1': 'Sind Sie sicher, dass Sie diesen Passkey löschen möchten?',
    'passkeys.8': 'Noch keine Passkeys registriert',
    'passkeys.9': 'Passkeys synchronisieren sich geräteübergreifend über iCloud Keychain oder Google Passwort-Manager',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)
de.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'w', encoding='utf-8') as f:
    json.dump(de, f, ensure_ascii=False, indent=2)
print('Updated passkeys section')