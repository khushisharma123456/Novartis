# Case Strength Evaluation & Scoring System - Implementation Analysis

## Executive Summary

❌ **NOT IMPLEMENTED** - Your current system does **NOT have** the comprehensive case strength evaluation and scoring system with AI agent orchestration that you've outlined in Steps 7-10.

Your system currently has:
- ✅ Case Linkage/Deduplication (fuzzy logic matching)
- ❌ Case Strength Evaluation
- ❌ Quality Assessment Scoring
- ❌ Follow-up Tracking
- ❌ AI Agent Orchestration

---

## What You HAVE vs. What's MISSING

### ✅ CURRENTLY IMPLEMENTED

**Case Linkage System:**
- `match_score` (0-1 similarity for duplicates)
- `case_status` (Active, Linked, Discarded)
- `match_notes` (reason for linkage)
- Fuzzy logic matching algorithm

**Case Data:**
```python
# Patient model contains:
- drug_name, symptoms, age, gender
- risk_level (Low, Medium, High)
- created_by, created_at
- recalled, recall_reason, recall_date
```

---

### ❌ MISSING COMPONENTS

#### 1. Case Strength Evaluation Fields

**Database Model Missing:**
```python
# NOT in Patient model - NEED TO ADD:
case_strength = db.Column(db.String(20))  # 'Low', 'Medium', 'High'
strength_score = db.Column(db.Integer)     # 0, 1, 2

# Strength Factors NOT tracked:
completeness_score = db.Column(db.Float)      # % of required fields filled
temporal_clarity_score = db.Column(db.Float)  # Is timeline clear?
medical_confirmation_score = db.Column(db.Float)  # Doctor confirmed?
followup_responsiveness_score = db.Column(db.Float)  # Response quality
```

---

#### 2. Final Case Scoring System

**NOT IMPLEMENTED:**
```python
# Missing calculation: Final Score = Polarity × Strength
case_score = db.Column(db.Integer)  # Range: -2 to +2

# Scoring examples NOT implemented:
# Strong AE → -2
# Weak AE → -1  
# Poor / unclear → 0
# Moderate positive → +1
# Strong positive → +2
```

**What's missing:**
- Polarity determination logic
- Strength × Polarity multiplication
- Confidence-weighted experience scoring

---

#### 3. Follow-up Tracking System

**NOT IMPLEMENTED:**
```python
# Missing follow-up management fields:
follow_up_required = db.Column(db.Boolean)
follow_up_sent = db.Column(db.Boolean)
response_received = db.Column(db.Boolean)
follow_up_date = db.Column(db.DateTime)
follow_up_response = db.Column(db.Text)

# Missing follow-up triggers:
# - case_score = 0 → Follow-up needed
# - strength_score < 1 (AE) → Follow-up needed
# - Missing mandatory fields → Follow-up needed
# - No doctor confirmation → Follow-up needed
```

---

#### 4. AI Agent Orchestration

**COMPLETELY MISSING:**
```python
# No Agent models or services exist:
class CaseAgent(db.Model):  # NOT EXISTS
    agent_type = db.Column(db.String(20))  # 'patient', 'doctor', 'hospital'
    assigned_case_id = db.Column(db.String(20))
    target_questions = db.Column(db.JSON)
    responses = db.Column(db.JSON)
    status = db.Column(db.String(20))  # 'active', 'completed'

# No agents for:
# - Patient Symptomatic Clarity Agent
# - Doctor Medical Confirmation Agent
# - Hospital Clinical Records Agent
# - Targeted Question Generation Service
```

---

## Complete Implementation Roadmap

### STEP 7: Case Strength Evaluation

**1. Database Schema Enhancement**

```python
class Patient(db.Model):
    # ... existing fields ...
    
    # === STRENGTH EVALUATION FIELDS ===
    
    # Completeness Assessment
    completeness_score = db.Column(db.Float, default=0.0)  # 0-100%
    mandatory_fields_filled = db.Column(db.Integer, default=0)
    total_mandatory_fields = db.Column(db.Integer, default=10)
    
    # Temporal Clarity
    temporal_clarity_score = db.Column(db.Float, default=0.0)  # 0-1
    symptom_onset_date = db.Column(db.DateTime, nullable=True)
    symptom_resolution_date = db.Column(db.DateTime, nullable=True)
    has_clear_timeline = db.Column(db.Boolean, default=False)
    
    # Medical Confirmation
    medical_confirmation_score = db.Column(db.Float, default=0.0)  # 0-1
    doctor_confirmed = db.Column(db.Boolean, default=False)
    doctor_confirmation_date = db.Column(db.DateTime, nullable=True)
    hospital_confirmed = db.Column(db.Boolean, default=False)
    hospital_confirmation_date = db.Column(db.DateTime, nullable=True)
    
    # Follow-up Responsiveness
    followup_responsiveness_score = db.Column(db.Float, default=0.0)  # 0-1
    last_followup_date = db.Column(db.DateTime, nullable=True)
    followup_response_time_days = db.Column(db.Integer, nullable=True)
    followup_response_quality = db.Column(db.String(20))  # 'Poor', 'Fair', 'Good'
    
    # Overall Strength
    strength_level = db.Column(db.String(20), default='Low')  # Low, Medium, High
    strength_score = db.Column(db.Integer, default=0)  # 0, 1, 2
    
    # === STEP 8: CASE SCORING ===
    polarity = db.Column(db.Integer, default=-1)  # -1 (AE), 0 (unclear), +1 (positive)
    case_score = db.Column(db.Integer)  # -2 to +2
```

---

### STEP 8: Final Case Scoring Service

**Create:** `pv_backend/services/case_scoring.py`

```python
class CaseScoringEngine:
    """
    Calculates case quality score based on strength and polarity
    Final Score = Polarity × Strength
    """
    
    MANDATORY_FIELDS = [
        'name', 'age', 'gender', 'drug_name', 
        'symptoms', 'created_at', 'created_by'
    ]
    
    def evaluate_case_strength(self, case):
        """
        Step 7: Evaluate data quality
        Returns strength_level (Low/Medium/High) and score (0/1/2)
        """
        completeness = self.evaluate_completeness(case)
        temporal = self.evaluate_temporal_clarity(case)
        medical = self.evaluate_medical_confirmation(case)
        followup = self.evaluate_followup_responsiveness(case)
        
        # Weighted average
        strength_score = (
            completeness * 0.3 +
            temporal * 0.3 +
            medical * 0.2 +
            followup * 0.2
        )
        
        # Map to levels
        if strength_score >= 0.67:
            return 'High', 2
        elif strength_score >= 0.33:
            return 'Medium', 1
        else:
            return 'Low', 0
    
    def evaluate_completeness(self, case):
        """Check % of mandatory fields filled"""
        filled = sum(1 for field in self.MANDATORY_FIELDS 
                     if getattr(case, field, None))
        return filled / len(self.MANDATORY_FIELDS)
    
    def evaluate_temporal_clarity(self, case):
        """Check if timeline is clear"""
        if case.symptom_onset_date and case.symptom_resolution_date:
            return 1.0
        elif case.symptom_onset_date:
            return 0.7
        elif case.created_at:
            return 0.5
        return 0.0
    
    def evaluate_medical_confirmation(self, case):
        """Check if confirmed by doctor/hospital"""
        if case.hospital_confirmed:
            return 1.0
        elif case.doctor_confirmed:
            return 0.7
        return 0.0
    
    def evaluate_followup_responsiveness(self, case):
        """Check follow-up response quality"""
        if case.followup_response_quality == 'Good':
            return 1.0
        elif case.followup_response_quality == 'Fair':
            return 0.6
        elif case.followup_response_quality == 'Poor':
            return 0.2
        return 0.0
    
    def determine_polarity(self, case):
        """
        Determine if case is:
        -1: Adverse Event (negative)
         0: Unclear / Inconclusive
        +1: Positive / Non-adverse
        """
        # Logic: AE if risk_level High/Medium
        if case.risk_level in ['High', 'Medium']:
            return -1
        elif case.risk_level == 'Low':
            return 1
        else:
            return 0
    
    def calculate_final_score(self, case):
        """
        Step 8: Calculate Final Score = Polarity × Strength
        
        Results:
        -2: Strong AE (High confidence negative event)
        -1: Weak AE (Low-medium confidence adverse event)
         0: Poor/Unclear (cannot assess)
        +1: Moderate positive (some evidence of non-adverse)
        +2: Strong positive (high confidence non-adverse)
        """
        strength_level, strength_score = self.evaluate_case_strength(case)
        polarity = self.determine_polarity(case)
        
        final_score = polarity * strength_score
        
        return {
            'case_score': final_score,
            'polarity': polarity,
            'strength': strength_score,
            'strength_level': strength_level,
            'interpretation': self.interpret_score(final_score)
        }
    
    def interpret_score(self, score):
        """Convert score to readable interpretation"""
        interpretations = {
            -2: 'Strong Adverse Event - High Confidence',
            -1: 'Weak/Unclear Adverse Event - Needs Review',
             0: 'Cannot Assess - Missing Critical Data',
            +1: 'Likely Non-Adverse - Needs Confirmation',
            +2: 'Strong Non-Adverse Event - High Confidence'
        }
        return interpretations.get(score, 'Unknown')
```

---

### STEP 9: Follow-up Tracking Service

**Create:** `pv_backend/services/followup_tracking.py`

```python
class FollowUpTracker:
    """
    Manages follow-up requests, tracking, and responses
    """
    
    FOLLOWUP_TRIGGERS = {
        'score_zero': {'condition': 'case_score == 0', 'priority': 'high'},
        'low_strength_ae': {'condition': 'strength_score < 1 and polarity < 0', 'priority': 'high'},
        'missing_fields': {'condition': 'completeness < 0.7', 'priority': 'medium'},
        'no_confirmation': {'condition': 'not doctor_confirmed and not hospital_confirmed', 'priority': 'medium'}
    }
    
    def check_followup_triggers(self, case):
        """
        Step 9: Determine if follow-up is needed
        """
        triggers = []
        
        if case.case_score == 0:
            triggers.append('score_zero')
        
        if case.strength_score < 1 and case.polarity < 0:
            triggers.append('low_strength_ae')
        
        if case.completeness_score < 0.7:
            triggers.append('missing_fields')
        
        if not case.doctor_confirmed and not case.hospital_confirmed:
            triggers.append('no_confirmation')
        
        return {
            'follow_up_required': len(triggers) > 0,
            'triggers': triggers,
            'priority': max(
                [self.FOLLOWUP_TRIGGERS[t]['priority'] for t in triggers],
                default='low'
            )
        }
    
    def create_followup(self, case_id, trigger_reasons):
        """Create follow-up request"""
        followup = FollowUp(
            case_id=case_id,
            reason=', '.join(trigger_reasons),
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(followup)
        db.session.commit()
        return followup

class FollowUp(db.Model):
    """Track all follow-up activities"""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.String(20), db.ForeignKey('patient.id'))
    reason = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20))  # pending, in_progress, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    response = db.Column(db.Text, nullable=True)
    
    case = db.relationship('Patient', backref=db.backref('followups'))
    assigned_user = db.relationship('User', backref=db.backref('assigned_followups'))
```

---

### STEP 10: AI Agent Orchestration

**Create:** `pv_backend/services/ai_agent_orchestration.py`

```python
class AgentOrchestrator:
    """
    Manages AI agents that improve case quality
    """
    
    AGENT_TYPES = {
        'patient': {
            'role': 'Symptom Clarity Agent',
            'questions': [
                'What are your exact symptoms in detail?',
                'When did symptoms start?',
                'When did symptoms resolve?',
                'Did you visit a doctor?',
                'Any medical tests done?'
            ]
        },
        'doctor': {
            'role': 'Medical Confirmation Agent',
            'questions': [
                'Can you clinically confirm this adverse event?',
                'What is your professional assessment?',
                'Any relevant medical history?',
                'Recommended follow-up?'
            ]
        },
        'hospital': {
            'role': 'Clinical Records Agent',
            'questions': [
                'Are there hospital records confirming this?',
                'Lab results available?',
                'Imaging or diagnostic confirmation?',
                'Clinical notes?'
            ]
        }
    }
    
    def activate_agents(self, case, triggers):
        """
        Activate appropriate agents based on case needs
        """
        agents_to_activate = []
        
        if 'missing_fields' in triggers or 'low_strength_ae' in triggers:
            agents_to_activate.append(('patient', case.created_by))
        
        if 'no_confirmation' in triggers:
            agents_to_activate.append(('doctor', case.doctors[0].id if case.doctors else None))
        
        if 'hospital_records' in triggers:
            agents_to_activate.append(('hospital', case.recalled_by))
        
        created_agents = []
        for agent_type, recipient_id in agents_to_activate:
            if recipient_id:
                agent = self.create_agent(case.id, agent_type, recipient_id)
                created_agents.append(agent)
        
        return created_agents
    
    def create_agent(self, case_id, agent_type, recipient_id):
        """Create and send AI agent"""
        agent_config = self.AGENT_TYPES[agent_type]
        
        agent = CaseAgent(
            case_id=case_id,
            agent_type=agent_type,
            role=agent_config['role'],
            target_questions=agent_config['questions'],
            recipient_id=recipient_id,
            status='active',
            created_at=datetime.utcnow()
        )
        
        db.session.add(agent)
        db.session.commit()
        
        # Send targeted questions
        self.send_agent_questions(agent)
        
        return agent
    
    def send_agent_questions(self, agent):
        """Send intelligent, targeted questions NOT generic forms"""
        # Example: Don't ask generic form, ask specific follow-up questions
        questions = agent.target_questions
        
        # Could integrate with WhatsApp/Email API
        message = f"""
        Hello! We need to clarify your {agent.agent_type} case report.
        
        {chr(10).join([f"{i+1}. {q}" for i, q in enumerate(questions[:3])])}
        
        Your response helps us better assess this case.
        """
        
        # Send via appropriate channel
        return message

class CaseAgent(db.Model):
    """Track AI agents for case improvement"""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.String(20), db.ForeignKey('patient.id'))
    agent_type = db.Column(db.String(20))  # patient, doctor, hospital
    role = db.Column(db.String(100))
    target_questions = db.Column(db.JSON)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20))  # active, completed, failed
    responses = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    case = db.relationship('Patient', backref=db.backref('agents'))
    recipient = db.relationship('User', backref=db.backref('assigned_agents'))
```

---

## API Endpoints Needed

### 1. Evaluate Case Strength
```
POST /api/cases/{case_id}/evaluate-strength

Response:
{
  "case_id": "PT-1234",
  "strength": {
    "level": "High",
    "score": 2,
    "completeness": 0.95,
    "temporal_clarity": 0.85,
    "medical_confirmation": 1.0,
    "followup_responsiveness": 0.75
  }
}
```

### 2. Calculate Case Score
```
POST /api/cases/{case_id}/calculate-score

Response:
{
  "case_score": -2,
  "polarity": -1,
  "strength": 2,
  "interpretation": "Strong Adverse Event - High Confidence",
  "confidence_level": "Very High"
}
```

### 3. Check Follow-up Triggers
```
GET /api/cases/{case_id}/followup-status

Response:
{
  "follow_up_required": true,
  "triggers": ["score_zero", "no_confirmation"],
  "priority": "high",
  "follow_up_sent": true,
  "response_received": false
}
```

### 4. Activate Agents
```
POST /api/cases/{case_id}/activate-agents

Response:
{
  "agents_activated": [
    {
      "id": 1,
      "type": "patient",
      "role": "Symptom Clarity Agent",
      "status": "active",
      "questions_sent": 5
    }
  ]
}
```

---

## Implementation Priority

### Phase 1 (Week 1-2): Foundation
1. ✅ Add new fields to Patient model
2. ✅ Create CaseScoringEngine service
3. ✅ Implement strength evaluation
4. ✅ Add API endpoints for scoring

### Phase 2 (Week 3): Follow-up System
1. ✅ Create FollowUp model
2. ✅ Implement FollowUpTracker
3. ✅ Add follow-up check endpoints
4. ✅ Create follow-up notification system

### Phase 3 (Week 4): AI Agents
1. ✅ Create CaseAgent model
2. ✅ Implement AgentOrchestrator
3. ✅ Add agent activation endpoints
4. ✅ Integrate with messaging (WhatsApp/Email)

---

## Summary

| Feature | Status | Impact |
|---------|--------|--------|
| Case Strength Evaluation | ❌ MISSING | **CRITICAL** |
| Quality Scoring (Polarity × Strength) | ❌ MISSING | **CRITICAL** |
| Follow-up Tracking | ❌ MISSING | **HIGH** |
| AI Agent Orchestration | ❌ MISSING | **HIGH** |
| Targeted Question Generation | ❌ MISSING | **MEDIUM** |
| Response Quality Assessment | ❌ MISSING | **MEDIUM** |

Your system needs comprehensive implementation of Steps 7-10 to achieve complete case quality management.
