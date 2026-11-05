import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)

translations = {
    'settings.1': 'Einstellungen',
    'settings.2': 'Profil',
    'settings.3': 'Vollständiger Name',
    'settings.4': 'E-Mail',
    'settings.5': 'Benutzername',
    'settings.6': 'Passwort ändern',
    'settings.7': 'Aktuelles Passwort',
    'settings.8': 'Neues Passwort',
    'settings.8.1': 'Neues Passwort bestätigen',
    'settings.9': 'Passwort aktualisieren',
    'settings.10': 'Zwei-Faktor-Authentifizierung',
    'settings.10.1': '2FA Aktivieren',
    'settings.10.2': '2FA Deaktivieren',
    'settings.10.3': 'Wiederherstellungscodes',
    'settings.11': 'Passkeys',
    'settings.11.1': 'Passkey Registrieren',
    'settings.11.2': 'Registrierte Passkeys',
    'settings.12': 'AI-Schlüssel-Verwaltung',
    'settings.12.1': 'AI-Anbieter',
    'settings.12.2': 'Modell',
    'settings.12.3': 'API-Schlüssel',
    'settings.12.3.1': 'Geben Sie Ihren API-Schlüssel ein',
    'settings.12.4': 'Basis-URL (optional)',
    'settings.12.5': 'AI-Schlüssel Speichern',
    'settings.13': 'Erscheinungsbild',
    'settings.13.1': 'Thema',
    'settings.13.2': 'Rahmenradius',
    'settings.14': 'Benachrichtigungen',
    'settings.15': 'E-Mail-Benachrichtigungen',
    'settings.16': 'Push-Benachrichtigungen',
    'settings.17': 'Einstellungen Speichern',
    'settings.18': 'Einstellungen Gespeichert',
    'settings.19': 'Fehler beim Speichern',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)
de.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'w', encoding='utf-8') as f:
    json.dump(de, f, ensure_ascii=False, indent=2)
print('Updated settings section')