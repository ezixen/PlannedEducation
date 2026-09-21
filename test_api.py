import requests
import json
res_reg = requests.post('http://localhost:8000/auth/register', json={'email': 'cors@test.com', 'username': 'corstest', 'password': 'abc', 'full_name': 'Cors'})
print(res_reg.text)
token = requests.post('http://localhost:8000/auth/token', data={'username': 'cors@test.com', 'password': 'abc'}).json()['access_token']
res = requests.post('http://localhost:8000/exams/', json={'title': 'Test', 'duration_minutes': 60}, headers={'Authorization': f'Bearer {token}'})
print(res.status_code)
print(res.text)
