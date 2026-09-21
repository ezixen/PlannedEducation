import requests
token = requests.post('http://localhost:8000/auth/token', data={'username': 'teacher2@test.com', 'password': 'password123'})
print('Token:', token.status_code, token.text)
