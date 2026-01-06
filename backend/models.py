from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) # In real app, hash this!
    role = db.Column(db.String(20), nullable=False) # 'doctor' or 'pharma'

# Association Table
doctor_patient = db.Table('doctor_patient',
    db.Column('doctor_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('patient_id', db.String(20), db.ForeignKey('patient.id'), primary_key=True)
)

class Patient(db.Model):
    id = db.Column(db.String(20), primary_key=True) # Custom ID like PT-1234
    
    # Many-to-Many with Doctors
    doctors = db.relationship('User', secondary=doctor_patient, backref=db.backref('patients', lazy=True))
    
    # Creator (Optional, for tracking who first made it)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Demographics
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    
    # Clinical
    drug_name = db.Column(db.String(100), nullable=False)
    symptoms = db.Column(db.Text, nullable=True)
    risk_level = db.Column(db.String(20), default='Low') # Low, Medium, High
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'age': self.age,
            'gender': self.gender,
            'drugName': self.drug_name,
            'symptoms': self.symptoms,
            'riskLevel': self.risk_level,
            'created_at': self.created_at.isoformat()
        }
