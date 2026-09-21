import requests
token = requests.post('http://localhost:8000/auth/token', data={'username': 'teacher3@test.com', 'password': 'password123'}).json()['access_token']
me = requests.get('http://localhost:8000/auth/me', headers={'Authorization': f'Bearer {token}'})
print('Me:', me.status_code, me.text)
