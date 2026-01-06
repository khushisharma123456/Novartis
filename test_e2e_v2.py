import requests
import json
import random

BASE = 'http://127.0.0.1:5000'
EMAIL = f'test_{random.randint(1,9999)}@medsafe.com'
PWD = 'password123'

s = requests.Session()

# 1. Register
print(f"Registering {EMAIL}...")
r = s.post(f'{BASE}/api/auth/register', json={
    'name': 'Dr E2E',
    'email': EMAIL,
    'password': PWD,
    'role': 'doctor'
})
print("Reg:", r.json())

# 2. Login
print("Logging in...")
r = s.post(f'{BASE}/api/auth/login', json={
    'email': EMAIL,
    'password': PWD
})
print("Login:", r.json())

# 3. Add Patient
print("Adding Patient...")
r = s.post(f'{BASE}/api/patients', json={
    'name': 'Patient Zero',
    'age': 45,
    'gender': 'Male',
    'drugName': 'TestDrug',
    'symptoms': 'Headache'
})
print(f"AddStatus: {r.status_code}")
print("AddResp:", r.text)
