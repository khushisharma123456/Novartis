import sys
import os
sys.path.append(os.getcwd())

from app import app, db, Patient, User
from flask import session

# Setup Context
app.config['TESTING'] = True

with app.app_context():
    # Ensure a user exists
    user = User.query.first()
    if not user:
        user = User(name='Debug Doc', email='debug@doc.com', password='pwd', role='doctor')
        db.session.add(user)
        db.session.commit()
    
    print(f"Using User: {user.id}")

    # Mock Session
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['role'] = 'doctor'
        
        # Call Endpoint
        print("Sending POST request...")
        resp = client.post('/api/patients', json={
                'name': 'Debug Patient',
                'age': 30,
                'gender': 'Male',
                'drugName': 'DebugDrug',
                'symptoms': 'DebugSys',
                'phone': '123'
            })
        
        print(f"Response: {resp.status_code}")
        print(resp.get_json())
