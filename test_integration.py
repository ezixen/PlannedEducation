import os
os.environ['DATABASE_URL'] = 'sqlite:///./test_final.db'
os.environ['PLANNED_EDUCATION_ENV'] = 'development'
os.environ['ALLOW_DEV_AUTH'] = 'true'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-final-check'
os.environ['CORS_ORIGINS'] = 'http://localhost:5173'
os.environ['AI_KEY_MASTER_SECRET'] = 'test-fernet-key-for-final-check-32-bytes-long!!'

from fastapi.testclient import TestClient
from src.plannededucation.api.main import app

client = TestClient(app)

# Test 1: Register teacher
print('Test 1: Register teacher...')
r = client.post('/auth/register', json={
    'email': 'teacher@test.com',
    'username': 'teacher1',
    'password': 'Secure1234!',
    'full_name': 'Test Teacher'
})
assert r.status_code == 201, f'Register failed: {r.text}'
print('  OK')

# Test 2: Login
print('Test 2: Login...')
r = client.post('/auth/token', data={'username': 'teacher1', 'password': 'Secure1234!'})
assert r.status_code == 200, f'Login failed: {r.text}'
tokens = r.json()
access_token = tokens['access_token']
refresh_token = tokens['refresh_token']
print('  OK - Got access + refresh tokens')

# Test 3: Refresh token
print('Test 3: Refresh token...')
r = client.post('/auth/refresh', json={'refresh_token': refresh_token})
assert r.status_code == 200, f'Refresh failed: {r.text}'
new_tokens = r.json()
assert 'access_token' in new_tokens and 'refresh_token' in new_tokens
print('  OK - Got new token pair')

# Test 4: AI Key management
print('Test 4: AI Key management...')
headers = {'Authorization': 'Bearer ' + access_token}
r = client.get('/auth/ai-key', headers=headers)
assert r.status_code == 200, f'Get AI key failed: {r.text}'
print('  OK - Get AI key')

r = client.put('/auth/ai-key', headers=headers, json={
    'ai_provider': 'gemini',
    'ai_model_name': 'gemini-2.5-flash',
    'ai_api_key': 'test-api-key-123'
})
assert r.status_code == 200, f'Update AI key failed: {r.text}'
print('  OK - Update AI key')

r = client.get('/auth/ai-key', headers=headers)
assert r.status_code == 200
data = r.json()
assert data['has_api_key'] == True
assert data['ai_provider'] == 'gemini'
print('  OK - AI key persisted and encrypted')

# Test 5: 2FA setup
print('Test 5: 2FA setup...')
r = client.post('/auth/2fa/setup', headers=headers)
assert r.status_code == 200, f'2FA setup failed: {r.text}'
data = r.json()
assert 'secret' in data and 'qr_code_uri' in data and 'recovery_codes' in data
assert len(data['recovery_codes']) == 5
print('  OK - 2FA setup with 5 recovery codes')

# Test 6: Exam creation
print('Test 6: Exam creation...')
r = client.post('/exams/', headers=headers, json={
    'title': 'Test Exam',
    'description': 'Test Description',
    'duration_minutes': 60
})
assert r.status_code == 200, f'Exam creation failed: {r.text}'
exam = r.json()
exam_id = exam['id']
print('  OK - Exam created: ' + exam_id)

# Test 7: Question creation
print('Test 7: Question creation...')
r = client.post('/exams/' + exam_id + '/questions', headers=headers, json={
    'question_type': 'multiple_choice',
    'text': 'What is 2+2?',
    'options_json': '[\"3\", \"4\", \"5\", \"6\"]',
    'correct_answer': '4',
    'points': 5
})
assert r.status_code == 200, f'Question creation failed: {r.text}'
print('  OK - Question created')

# Test 8: Anonymizer
print('Test 8: Anonymizer...')
r = client.get('/anonymizer/exams/' + exam_id + '/submissions', headers=headers)
assert r.status_code == 200, f'Anonymizer failed: {r.text}'
print('  OK - Anonymizer endpoint works')

print()
print('=== ALL INTEGRATION TESTS PASSED ===')