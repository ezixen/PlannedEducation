import json
import os

locales_dir = 'web/apps/portal/src/locales'
chat_title_translations = {
    'ar': 'دردشة مع الطلاب',
    'cn': '与学生聊天',
    'cs': 'Chat se studenty',
    'da': 'Chat med studerende',
    'de': 'Chat mit Schülern',
    'el': 'Συνομιλία με μαθητές',
    'en': 'Chat with Students',
    'es': 'Chat con estudiantes',
    'fi': 'Keskustelu opiskelijoiden kanssa',
    'fr': 'Discuter avec les étudiants',
    'he': 'צ\'אט עם תלמידים',
    'hu': 'Beszélgetés tanulókkal',
    'id': 'Obrolan dengan siswa',
    'it': 'Chat con gli studenti',
    'ja': '生徒とチャット',
    'ko': '학생과 채팅',
    'nl': 'Chat met studenten',
    'no': 'Chat med studenter',
    'pl': 'Czat z uczniami',
    'pt': 'Conversar com alunos',
    'pt-BR': 'Conversar com alunos',
    'ru': 'Чат с учениками',
    'sv': 'Chatta med studenter',
    'th': 'แชทกับนักเรียน',
    'tr': 'Öğrencilerle sohbet',
    'uk': 'Чат зі студентами',
    'vi': 'Trò chuyện với học sinh',
}

for locale in sorted(os.listdir(locales_dir)):
    filepath = os.path.join(locales_dir, locale, 'messages.json')
    if not os.path.exists(filepath):
        continue
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)
    
    # Add chat_title after opening_tests
    new_data = {}
    for key, value in data.items():
        new_data[key] = value
        if key == 'teacher_dashboard.opening_tests':
            new_data['teacher_dashboard.chat_title'] = chat_title_translations.get(locale, 'Chat with Students')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f'{locale}: Added chat_title')

print('Done!')
