import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)

translations = {
    'proctoring.1': 'Proctoring',
    'proctoring.2': 'Proctoring Aktivieren',
    'proctoring.3': 'Kamera',
    'proctoring.3.1': 'Mikrofon',
    'proctoring.4': 'DSGVO-Einwilligung',
    'proctoring.4.1': 'Ich stimme der Kamera- und Mikrofonüberwachung während Prüfungen zu',
    'proctoring.5': 'Einwilligung Geben',
    'proctoring.6': 'Einwilligung Erteilt',
    'proctoring.7': 'Einwilligung Widerrufen',
    'proctoring.8': 'Proctoring-Sitzung',
    'proctoring.9': 'Sitzung Starten',
    'proctoring.10': 'Sitzung Beenden',
    'proctoring.11': 'Sitzungsereignisse',
    'proctoring.12': 'Augenbewegung',
    'proctoring.13': 'Mehrere Gesichter',
    'proctoring.14': 'Hintergrund-Audio',
    'proctoring.15': 'Tab-Wechsel',
    'proctoring.16': 'SEB-Verletzung',
    'proctoring.17': 'Keine Aktive Sitzung',
    'proctoring.18': 'Sitzung Beendet',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'r', encoding='utf-8') as f:
    de = json.load(f)
de.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/de/messages.json', 'w', encoding='utf-8') as f:
    json.dump(de, f, ensure_ascii=False, indent=2)
print('Updated proctoring section')