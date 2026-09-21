import requests
res_reg = requests.post('http://localhost:8000/auth/register', json={'email': 'teacher3@test.com', 'username': 'teacher3', 'password': 'password123', 'full_name': 'Teacher 3'})
print('Reg:', res_reg.status_code, res_reg.text)
token = requests.post('http://localhost:8000/auth/token', data={'username': 'teacher3@test.com', 'password': 'password123'})
print('Token:', token.status_code, token.text)
