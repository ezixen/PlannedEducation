import json

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/ja/messages.json', 'r', encoding='utf-8') as f:
    ja = json.load(f)

translations = {
    'proctoring.1': 'プロクタリング',
    'proctoring.2': 'プロクタリングを有効化',
    'proctoring.3': 'カメラ',
    'proctoring.3.1': 'マイク',
    'proctoring.4': 'GDPR同意',
    'proctoring.4.1': '試験中のカメラとマイクによる監視に同意します',
    'proctoring.5': '同意する',
    'proctoring.6': '同意済み',
    'proctoring.7': '同意を取り消す',
    'proctoring.8': 'プロクタリングセッション',
    'proctoring.9': 'セッション開始',
    'proctoring.10': 'セッション終了',
    'proctoring.11': 'セッションイベント',
    'proctoring.12': '視線移動',
    'proctoring.13': '複数の顔',
    'proctoring.14': '背景音',
    'proctoring.15': 'タブ切り替え',
    'proctoring.16': 'SEB違反',
    'proctoring.17': 'アクティブなセッションなし',
    'proctoring.18': 'セッション終了',
}

with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/ja/messages.json', 'r', encoding='utf-8') as f:
    ja = json.load(f)
ja.update(translations)
with open('d:/Dev/PlannedEducation/web/apps/portal/src/locales/ja/messages.json', 'w', encoding='utf-8') as f:
    json.dump(ja, f, ensure_ascii=False, indent=2)
print('Updated proctoring section')