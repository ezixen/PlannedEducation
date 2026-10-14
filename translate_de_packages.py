import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)

translations = {
    'packages.1': 'Testpaket-Manager',
    'packages.2': 'Paket Exportieren',
    'packages.3': 'Paket Importieren',
    'packages.4': 'Paket Validieren',
    'packages.4.1': 'Ziehen Sie die .pepkg.json oder .pepkg.yaml Datei hierher',
    'packages.5': 'Export-Optionen',
    'packages.5.1': 'Antworten Einschließen',
    'packages.5.2': 'Bewertungsschemata Einschließen',
    'packages.5.3': 'Variablen Einschließen',
    'packages.5.4': 'Format',
    'packages.5.5': 'JSON',
    'packages.5.6': 'YAML',
    'packages.5.7': 'Komprimieren (gzip)',
    'packages.6': 'Exportieren',
    'packages.7': 'Importieren',
    'packages.8': 'Paket Gültig',
    'packages.8.1': 'Paket ist Gültig!',
    'packages.8.2': 'Paket-Validierung Fehlgeschlagen',
    'packages.9': 'Paket Importiert',
    'packages.9.1': 'Fragen Importiert',
    'packages.9.2': 'Bewertungsschemata Importiert',
    'packages.10': 'Meine Pakete',
    'packages.11': 'Noch Keine Pakete',
    'packages.12': 'Herunterladen',
    'packages.13': 'Löschen',
    'packages.14': 'Veröffentlichen',
    'packages.15': 'Veröffentlichung Rückgängig Machen',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)
de.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'w', encoding='utf-8') as f:
    json.dump(de, f, ensure_ascii=False, indent=2)
print('Updated packages section')