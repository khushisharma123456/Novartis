# Complete Workflow & Testing Guide

## End-to-End Case Quality Assessment Workflow

### Step-by-Step Process

```
┌─────────────────────────────────────────────────────────────────┐
│  1. CASE SUBMISSION                                             │
│  Doctor/Pharmacy submits a new case report                      │
│  API: POST /api/pharmacy/report or /api/doctor/report           │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. DUPLICATE CHECK (Optional - Already Implemented)            │
│  System checks for matching cases (fuzzy logic)                 │
│  API: POST /api/cases/match                                     │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. CASE STRENGTH EVALUATION (NEW - STEP 7)                     │
│  System evaluates:                                              │
│  - Completeness of data (0-1)                                  │
│  - Temporal clarity (0-1)                                      │
│  - Medical confirmation (0-1)                                  │
│  - Follow-up responsiveness (0-1)                              │
│  API: POST /api/cases/{case_id}/evaluate-strength              │
│  Result: strength_score (0, 1, or 2)                           │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. FINAL CASE SCORING (NEW - STEP 8)                           │
│  Calculate: Polarity × Strength                                │
│  - Polarity: -1 (AE), 0 (Unclear), +1 (Positive)              │
│  - Strength: 0, 1, or 2                                        │
│  - Final Score: -2 to +2                                       │
│  API: POST /api/cases/{case_id}/calculate-score                │
│  Result: case_score (-2, -1, 0, +1, or +2)                    │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. FOLLOW-UP REQUIREMENT CHECK (NEW - STEP 9)                  │
│  Triggers:                                                      │
│  - Score = 0? → Follow-up required                             │
│  - Weak AE (score -1)? → Follow-up required                    │
│  - Completeness < 70%? → Follow-up required                    │
│  - No medical confirmation? → Follow-up required               │
│  API: GET /api/cases/{case_id}/followup-status                 │
│  Result: follow_up_required (bool), priority (level)           │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
         [DECISION POINT]
         Follow-up needed?
         ↙ YES                ↘ NO
      │                         │
      ▼                         ▼
┌─────────────────────────┐   ┌──────────────────┐
│ 6. ACTIVATE AI AGENTS   │   │ Case Complete    │
│    (NEW - STEP 10)      │   │ Display to user  │
│                         │   └──────────────────┘
│ API: POST               │
│ /api/cases/{id}/        │
│ activate-agents         │
└────────┬────────────────┘
         ▼
   ┌─────────────────────────────────────┐
   │ Activate Targeted Agents:           │
   │ - Patient Agent (symptoms)          │
   │ - Doctor Agent (confirmation)       │
   │ - Hospital Agent (records)          │
   │                                     │
   │ Each sends specific questions       │
   │ (not generic forms!)                │
   └────────┬────────────────────────────┘
            ▼
   ┌─────────────────────────────────────┐
   │ 7. COLLECT RESPONSES                │
   │ Agents receive and store responses  │
   │                                     │
   │ API: POST /api/agents/{id}/         │
   │ submit-response                     │
   └────────┬────────────────────────────┘
            ▼
   ┌─────────────────────────────────────┐
   │ 8. RE-EVALUATE CASE                 │
   │ Repeat Steps 3-5 with new data      │
   │ Case score may improve              │
   └────────┬────────────────────────────┘
            ▼
   ┌─────────────────────────────────────┐
   │ Case Complete (improved quality)    │
   └─────────────────────────────────────┘

         ▼▼▼ THROUGHOUT ▼▼▼
┌─────────────────────────────────────┐
│ 9. VIEW KPI DASHBOARD               │
│ Monitor all cases:                  │
│ - Strong cases: 85                  │
│ - Medium cases: 25                  │
│ - Weak cases: 10                    │
│                                     │
│ API: GET /api/dashboard/kpi         │
└─────────────────────────────────────┘
```

---

## Testing the Complete System

### Test Scenario 1: Complete Adverse Event Workflow

```bash
# 1. Submit a case
curl -X POST http://localhost:5000/api/pharmacy/report \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{
    "patientName": "John Smith",
    "phone": "555-1234",
    "age": 45,
    "gender": "Male",
    "drugName": "Aspirin",
    "reaction": "severe headache and dizziness lasting 3 days",
    "severity": "High"
  }'

# Response: {"success": true, "report_id": "PH-1234"}
CASE_ID="PH-1234"

# 2. Evaluate strength
curl -X POST http://localhost:5000/api/cases/${CASE_ID}/evaluate-strength \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION"

# Response shows completeness, temporal clarity, etc.
# Example: strength_score: 1 (Medium)

# 3. Calculate case score
curl -X POST http://localhost:5000/api/cases/${CASE_ID}/calculate-score \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION"

# Response: case_score: -1 (Weak AE)

# 4. Check follow-up status
curl -X GET http://localhost:5000/api/cases/${CASE_ID}/followup-status \
  -H "Cookie: session=YOUR_SESSION"

# Response shows follow_up_required: true
# Triggers: ["weak_ae", "no_medical_confirmation"]
# Priority: "high"

# 5. Activate agents
curl -X POST http://localhost:5000/api/cases/${CASE_ID}/activate-agents \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION"

# Response shows activated agents with IDs
# Example: agent_id: 1, 2, 3

# 6. Get agent questions
curl -X GET http://localhost:5000/api/agents/1/questions \
  -H "Cookie: session=YOUR_SESSION"

# Response shows targeted questions

# 7. Submit agent response
curl -X POST http://localhost:5000/api/agents/1/submit-response \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{
    "responses": [
      "Severe headache, sharp pain",
      "2024-01-25 2:00 PM",
      "2024-01-27 10:00 AM",
      "Yes, visited Dr. Johnson",
      "No other medications",
      "No pre-existing conditions",
      "No family history"
    ]
  }'

# Response: {"success": true, "agent_id": 1}

# 8. View KPI Dashboard
curl -X GET http://localhost:5000/api/dashboard/kpi \
  -H "Cookie: session=YOUR_SESSION"

# Response shows case metrics

# 9. View case details with quality assessment
curl -X GET http://localhost:5000/api/dashboard/case-details/${CASE_ID} \
  -H "Cookie: session=YOUR_SESSION"

# Response shows complete case assessment
```

---

### Test Scenario 2: Multiple Cases for KPI Dashboard

```bash
# Create 10 test cases with different strength levels

# Create Strong Case
curl -X POST http://localhost:5000/api/pharmacy/report \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{
    "patientName": "Strong Case Patient",
    "age": 50,
    "gender": "Female",
    "drugName": "Ibuprofen",
    "reaction": "severe allergic reaction with anaphylaxis",
    "severity": "High"
  }'

# ... (repeat with different data)

# Then check KPI dashboard to see distribution
curl -X GET http://localhost:5000/api/dashboard/kpi \
  -H "Cookie: session=YOUR_SESSION"

# Should show something like:
# {
#   "strength_distribution": {
#     "strong": 3,
#     "medium": 4,
#     "weak": 3,
#     "not_evaluated": 0
#   },
#   "case_score_distribution": {
#     "strong_ae": 2,
#     "weak_ae": 1,
#     ...
#   }
# }
```

---

## Expected Responses

### Response 1: Evaluate Strength
```json
{
  "success": true,
  "case_id": "PH-1234",
  "strength": {
    "strength_level": "Medium",
    "strength_score": 1,
    "overall_score": 0.52,
    "breakdown": {
      "completeness": 0.57,        // 4 out of 7 mandatory fields
      "temporal_clarity": 0.70,    // Only onset date, no resolution
      "medical_confirmation": 0.0, // No confirmation yet
      "followup_responsiveness": 0.0
    },
    "confidence": "Low"
  }
}
```

### Response 2: Calculate Score
```json
{
  "success": true,
  "case_id": "PH-1234",
  "scoring": {
    "case_score": -1,
    "polarity": -1,
    "polarity_text": "Adverse Event",
    "strength": 1,
    "interpretation": "Weak/Unclear Adverse Event - Needs Review",
    "confidence": "Medium"
  }
}
```

### Response 3: Followup Status
```json
{
  "success": true,
  "case_id": "PH-1234",
  "followup": {
    "follow_up_required": true,
    "triggers": [
      "weak_ae",
      "low_completeness",
      "no_medical_confirmation"
    ],
    "priority": "high",
    "trigger_descriptions": {
      "weak_ae": "Weak adverse event - needs additional confirmation",
      "low_completeness": "Missing important case information (< 70% complete)",
      "no_medical_confirmation": "Adverse event not confirmed by medical professional"
    }
  },
  "followup_history": [],
  "follow_up_sent": false,
  "response_received": false
}
```

### Response 4: Activate Agents
```json
{
  "success": true,
  "case_id": "PH-1234",
  "agents": {
    "success": true,
    "agents_activated": [
      {
        "id": 1,
        "type": "patient",
        "role": "Patient Symptom Clarity Agent",
        "status": "active",
        "total_questions": 7,
        "questions": [...]
      },
      {
        "id": 2,
        "type": "doctor",
        "role": "Doctor Medical Confirmation Agent",
        "status": "active",
        "total_questions": 6,
        "questions": [...]
      }
    ],
    "total_agents": 2,
    "total_questions": 13
  }
}
```

### Response 5: KPI Dashboard
```json
{
  "success": true,
  "overview": {
    "total_cases": 150,
    "cases_evaluated": 120,
    "pending_evaluation": 30
  },
  "strength_distribution": {
    "strong": 85,
    "medium": 25,
    "weak": 10,
    "not_evaluated": 30
  },
  "case_score_distribution": {
    "strong_ae": 45,
    "weak_ae": 30,
    "unclear": 5,
    "weak_positive": 15,
    "strong_positive": 55
  },
  "followup_status": {
    "required": 35,
    "sent": 28,
    "responses_received": 18,
    "pending_response": 10
  },
  "quality_metrics": {
    "avg_completeness": 0.78,
    "avg_temporal_clarity": 0.72,
    "avg_medical_confirmation": 0.65
  },
  "trends": {
    "strong_vs_weak_ratio": "85:10",
    "quality_trend": "Improving"
  }
}
```

---

## Database State After Testing

### Patient Record Example
```sql
SELECT 
  id,
  name,
  drug_name,
  risk_level,
  strength_level,
  strength_score,
  polarity,
  case_score,
  follow_up_required,
  follow_up_sent,
  created_at,
  evaluated_at
FROM patient
WHERE id = 'PH-1234';

-- Result:
-- id: PH-1234
-- name: John Smith
-- drug_name: Aspirin
-- risk_level: High
-- strength_level: Medium
-- strength_score: 1
-- polarity: -1
-- case_score: -1
-- follow_up_required: true
-- follow_up_sent: true
-- created_at: 2024-01-28 10:00:00
-- evaluated_at: 2024-01-28 10:30:00
```

### CaseAgent Record Example
```sql
SELECT 
  id,
  case_id,
  agent_type,
  role,
  status,
  created_at,
  resolved_at
FROM case_agent
WHERE case_id = 'PH-1234';

-- Results:
-- 1, PH-1234, patient, Patient Symptom Clarity Agent, active, 2024-01-28 10:30:00, NULL
-- 2, PH-1234, doctor, Doctor Medical Confirmation Agent, active, 2024-01-28 10:30:00, NULL
```

### FollowUp Record Example
```sql
SELECT 
  id,
  case_id,
  reason,
  priority,
  status,
  created_at
FROM follow_up
WHERE case_id = 'PH-1234';

-- Result:
-- 1, PH-1234, weak_ae | low_completeness | no_medical_confirmation, high, pending, 2024-01-28 10:30:00
```

---

## Key Metrics to Monitor

### Dashboard Metrics
1. **Strong vs Weak Ratio**
   - Good: >80% strong cases
   - Acceptable: 60-80%
   - Poor: <60%

2. **Follow-up Response Rate**
   - Good: >75% response rate
   - Acceptable: 50-75%
   - Poor: <50%

3. **Case Completeness**
   - Good: >80% average
   - Acceptable: 60-80%
   - Poor: <60%

4. **Medical Confirmation Rate**
   - Good: >70% confirmed
   - Acceptable: 50-70%
   - Poor: <50%

---

## Common Issues & Solutions

### Issue 1: Cases not getting evaluated
**Solution:** Ensure evaluate-strength endpoint is called after case submission

### Issue 2: Agents not being activated
**Solution:** Check that follow-up triggers are being detected (check case_score = 0 or weak_ae)

### Issue 3: KPI showing "Not Evaluated"
**Solution:** Manually call evaluate-strength for cases, or set up auto-evaluation on submission

### Issue 4: Agent responses not being saved
**Solution:** Ensure responses are submitted with POST to /api/agents/{id}/submit-response

---

## Production Checklist

- [ ] Test all 9 API endpoints
- [ ] Verify database migrations applied (new models and fields)
- [ ] Test with multiple cases
- [ ] Verify KPI dashboard shows correct metrics
- [ ] Test agent question generation
- [ ] Test agent response submission
- [ ] Verify follow-up triggers work correctly
- [ ] Test edge cases (score 0, weak AE, no confirmation)
- [ ] Load test with 100+ cases
- [ ] Verify response times <500ms for all endpoints
- [ ] Set up automated evaluation after case submission
- [ ] Configure agent notifications (email/WhatsApp)
- [ ] Create monitoring alerts for low quality cases
- [ ] Document API endpoints in Swagger/OpenAPI

---

## Success Criteria

✅ Cases are automatically evaluated for strength (0-2 scale)
✅ Final case scores calculated (-2 to +2 range)
✅ Follow-up system automatically triggered for weak cases
✅ AI agents activated with targeted questions
✅ KPI dashboard shows strong vs weak case distribution
✅ Quality trends visible and monitored
✅ Case details display all quality metrics
✅ System maintains audit trail of all evaluations

Your system now provides **complete case quality management!**
