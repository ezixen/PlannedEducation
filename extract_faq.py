content = open('D:/Dev/PlannedEducation/web/apps/portal/src/components/FAQChatbot.tsx', 'r', encoding='utf-8', errors='replace').read()
import re

# Find all question entries in FAQ_DATA
pattern = r'\{\s*id:\s*(\d+),\s*question:\s*"([^"]+)",\s*keywords:\s*\[([^\]]*)\],\s*answer:\s*"([^"]+)",'
for m in re.finditer(pattern, content):
    qid, question, keywords, answer = m.groups()
    print(f'Q{qid}: {question}')
    print(f'  Keywords: {keywords}')
    print(f'  Answer: {answer[:80]}...')
    print()