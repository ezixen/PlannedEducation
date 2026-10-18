import requests, sys

BASE = 'http://localhost:8000'

# 1. Register
r = requests.post(f'{BASE}/auth/register', json={'email': 'smoke@test.com', 'username': 'smoketest', 'password': 'Smoke123!', 'full_name': 'Smoke Test'})
assert r.status_code == 201, f'Register failed: {r.status_code} {r.text}'
print('PASS register')

# 2. Weak password rejected
r = requests.post(f'{BASE}/auth/register', json={'email': 'weak@test.com', 'username': 'weakuser', 'password': 'abc', 'full_name': 'Weak'})
assert r.status_code == 422, f'Expected 422, got {r.status_code} {r.text}'
print('PASS weak password rejected')

# 3. Login
r = requests.post(f'{BASE}/auth/token', data={'username': 'smoke@test.com', 'password': 'Smoke123!'})
assert r.status_code == 200, f'Login failed: {r.status_code} {r.text}'
token = r.json()['access_token']
print('PASS login')

headers = {'Authorization': f'Bearer {token}'}

# 4. /auth/me
r = requests.get(f'{BASE}/auth/me', headers=headers)
assert r.status_code == 200, f'me failed: {r.status_code}'
me = r.json()
assert 'hashed_password' not in me, 'FAIL: hashed_password leaked!'
assert 'ai_api_key' not in me, 'FAIL: ai_api_key leaked!'
print('PASS /auth/me (no sensitive data leaked)')

# 5. Create exam
r = requests.post(f'{BASE}/exams/', json={'title': 'Smoke Exam', 'duration_minutes': 45}, headers=headers)
assert r.status_code == 201, f'Create exam failed: {r.status_code} {r.text}'
exam_id = r.json()['id']
print('PASS create exam')

# 6. Public listing has no correct_answer
r = requests.get(f'{BASE}/exams/', headers=headers)
assert r.status_code == 200
for exam in r.json():
    assert 'questions' not in exam, 'FAIL: /exams/ leaked questions!'
print('PASS exam listing has no question data')

# 7. /exams/mine returns full data for owner
r = requests.get(f'{BASE}/exams/mine', headers=headers)
assert r.status_code == 200
assert len(r.json()) >= 1
print('PASS /exams/mine returns owner exams')

# 8. Second user cannot access exam full detail
r2 = requests.post(f'{BASE}/auth/register', json={'email': 'other@test.com', 'username': 'otheruser', 'password': 'Other123!', 'full_name': 'Other'})
assert r2.status_code == 201
tok2 = requests.post(f'{BASE}/auth/token', data={'username': 'other@test.com', 'password': 'Other123!'}).json()['access_token']
h2 = {'Authorization': f'Bearer {tok2}'}
r_idor = requests.get(f'{BASE}/exams/{exam_id}', headers=h2)
assert r_idor.status_code == 403, f'FAIL: IDOR on /exams/{{exam_id}} - got {r_idor.status_code}'
print('PASS IDOR protection: non-owner gets 403 on exam detail')

print()
print('All smoke tests passed!')
