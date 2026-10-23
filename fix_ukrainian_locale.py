import json

with open('web/apps/portal/src/locales/uk/messages.json', encoding='utf-8') as f:
    content = f.read()

# Replace Ukrainian quotes with regular quotes
content = content.replace('\u00ab', '"').replace('\u00bb', '"')

with open('web/apps/portal/src/locales/uk/messages.json', 'w', encoding='utf-8') as f:
    f.write(content)

# Validate
json.loads(content)
print('Ukrainian locale fixed and valid!')
