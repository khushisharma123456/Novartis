from backend.app import app, db, Patient, User
from flask import session

# Setup Context
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medsafe.db'

with app.app_context():
    # Ensure a user exists
    user = User.query.first()
    if not user:
        user = User(name='Debug Doc', email='debug@doc.com', password='pwd', role='doctor')
        db.session.add(user)
        db.session.commit()
    
    print(f"Using User: {user.id}")

    # Mock Request
    with app.test_request_context('/api/patients', method='POST', json={
        'name': 'Debug Patient',
        'age': 30,
        'gender': 'Male',
        'drugName': 'DebugDrug',
        'symptoms': 'DebugSys',
        'phone': '123'
    }):
        # Mock Session
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = user.id
                sess['role'] = 'doctor'
            
            # Call Endpoint logic manually or via client
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
