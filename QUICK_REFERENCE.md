# Quick Reference - API Endpoints

## Complete System at a Glance

### 🎯 Core Endpoints

```
POST /api/cases/{case_id}/evaluate-strength
├─ Purpose: Evaluate case quality (Step 7)
├─ Evaluates: Completeness, Temporal Clarity, Medical Confirmation, Follow-up
├─ Returns: strength_score (0, 1, or 2), strength_level, breakdown
└─ Example: Strength: HIGH, Score: 2

POST /api/cases/{case_id}/calculate-score
├─ Purpose: Calculate final case score (Step 8)
├─ Formula: Polarity × Strength = Score (-2 to +2)
├─ Returns: case_score, interpretation, confidence
└─ Example: Score: -2 "Strong Adverse Event - Very High Confidence"

GET /api/cases/{case_id}/followup-status
├─ Purpose: Check if follow-up needed (Step 9)
├─ Returns: follow_up_required, triggers, priority
├─ Triggers: weak_ae, unclear_score, low_completeness, no_confirmation
└─ Example: follow_up_required: true, priority: high

POST /api/cases/{case_id}/activate-agents
├─ Purpose: Activate AI agents (Step 10)
├─ Agents: Patient (symptoms), Doctor (confirmation), Hospital (records)
├─ Returns: agents_activated, total_agents, total_questions
└─ Example: 2 agents activated with 13 targeted questions

GET /api/agents/{agent_id}/questions
├─ Purpose: Get agent's questions
├─ Returns: agent_type, role, questions array
└─ Example: 7 questions from Patient Agent

POST /api/agents/{agent_id}/submit-response
├─ Purpose: Submit responses to agent questions
├─ Params: responses (array of answers)
├─ Returns: success, agent_id, status: completed
└─ Example: Response recorded, case quality may improve

GET /api/dashboard/kpi
├─ Purpose: KPI Dashboard - Shows Strong vs Weak Cases
├─ Shows:
│  ├─ overview: total_cases, cases_evaluated, pending
│  ├─ strength_distribution: strong, medium, weak
│  ├─ case_score_distribution: -2, -1, 0, +1, +2 counts
│  ├─ followup_status: required, sent, received
│  ├─ quality_metrics: avg_completeness, temporal, confirmation
│  └─ trends: ratio, quality_trend
└─ Example:
   {
     "total_cases": 150,
     "strong": 85 (56.7%),
     "medium": 25 (16.7%),
     "weak": 10 (6.7%),
     "quality_trend": "Improving"
   }

GET /api/dashboard/case-details/{case_id}
├─ Purpose: Full case quality assessment details
├─ Shows: strength_evaluation, case_scoring, followup, agents
└─ Example: Complete case with all quality metrics

GET /api/cases/{case_id}/agents
├─ Purpose: Get all agents for a case
├─ Returns: active_agents, agents array
└─ Example: 2 active agents
```

---

## Case Scoring Scale

### Strength Score (Step 7)
```
0 = LOW    (Weak data quality)
1 = MEDIUM (Acceptable data quality)
2 = HIGH   (Strong data quality)
```

### Polarity (Step 8)
```
-1 = Adverse Event
 0 = Unclear/Cannot Determine
+1 = Positive/Non-Adverse
```

### Final Case Score (Step 8)
```
-2 = Strong Adverse Event       ← Risk!
-1 = Weak Adverse Event         ← Review needed
 0 = Cannot Assess              ← Follow-up required
+1 = Weak Positive              ← Likely safe
+2 = Strong Non-Adverse Event   ← Confirmed safe
```

### Follow-up Triggers (Step 9)
```
✓ case_score = 0                    → Follow-up needed
✓ Weak AE (score -1)                → Follow-up needed
✓ Completeness < 70%                → Follow-up needed
✓ No medical confirmation (AE)      → Follow-up needed
```

### Agent Types (Step 10)
```
PATIENT AGENT
├─ 7 questions about symptoms
├─ Symptom onset, resolution, medical visit
└─ Other medications, pre-existing conditions

DOCTOR AGENT
├─ 6 questions about medical assessment
├─ Clinical confirmation, treatment, severity
└─ Follow-up recommendations

HOSPITAL AGENT
├─ 6 questions about clinical records
├─ Diagnostic tests, imaging, clinical notes
└─ Hospital outcomes
```

---

## Response Examples

### Strength Evaluation Response
```json
{
  "strength_level": "High",
  "strength_score": 2,
  "breakdown": {
    "completeness": 0.95,
    "temporal_clarity": 0.85,
    "medical_confirmation": 1.0,
    "followup_responsiveness": 0.75
  }
}
```

### Case Score Response
```json
{
  "case_score": -2,
  "polarity": -1,
  "strength": 2,
  "interpretation": "Strong Adverse Event - Very High Confidence",
  "confidence": "Very High"
}
```

### KPI Dashboard Response (KEY!)
```json
{
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
  }
}
```

---

## Database Fields Added

### Patient Model
```
STRENGTH EVALUATION (Step 7):
  completeness_score
  temporal_clarity_score
  medical_confirmation_score
  followup_responsiveness_score
  strength_level (Low/Medium/High)
  strength_score (0/1/2)

FINAL SCORING (Step 8):
  polarity (-1/0/+1)
  case_score (-2 to +2)
  case_score_interpretation

FOLLOW-UP (Step 9):
  follow_up_required (bool)
  follow_up_sent (bool)
  follow_up_date
  follow_up_response

TIMESTAMPS:
  evaluated_at
  case_score_calculated_at
```

### New Models
```
CaseAgent:
  id, case_id, agent_type, role, target_questions,
  recipient_id, status, responses, created_at

FollowUp:
  id, case_id, reason, assigned_to, status, priority,
  created_at, resolved_at, response
```

---

## Quick Start

### 1. Evaluate Case
```bash
curl -X POST http://localhost:5000/api/cases/PT-1234/evaluate-strength \
  -H "Cookie: session=YOUR_SESSION"
```

### 2. Calculate Score
```bash
curl -X POST http://localhost:5000/api/cases/PT-1234/calculate-score \
  -H "Cookie: session=YOUR_SESSION"
```

### 3. Check Follow-up
```bash
curl -X GET http://localhost:5000/api/cases/PT-1234/followup-status \
  -H "Cookie: session=YOUR_SESSION"
```

### 4. Activate Agents
```bash
curl -X POST http://localhost:5000/api/cases/PT-1234/activate-agents \
  -H "Cookie: session=YOUR_SESSION"
```

### 5. View KPI Dashboard
```bash
curl -X GET http://localhost:5000/api/dashboard/kpi \
  -H "Cookie: session=YOUR_SESSION"
```

---

## Key Metrics to Monitor

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Strong Cases % | >80% | 60-80% | <60% |
| Avg Completeness | >80% | 60-80% | <60% |
| Medical Confirmation | >70% | 50-70% | <50% |
| Follow-up Response | >75% | 50-75% | <50% |
| Strong vs Weak Ratio | 85:10 | 70:20 | 50:30 |

---

## Files Reference

**Services:**
- `pv_backend/services/case_scoring.py` - CaseScoringEngine
- `pv_backend/services/quality_agent.py` - QualityAgentOrchestrator, FollowUpManager

**Models:**
- `models.py` - Patient (updated), CaseAgent, FollowUp

**Routes:**
- `app.py` - 9 new endpoints

**Documentation:**
- `IMPLEMENTATION_COMPLETE_SUMMARY.md` - Full summary
- `QUALITY_AGENT_IMPLEMENTATION_GUIDE.md` - Detailed guide
- `FRONTEND_INTEGRATION_GUIDE.md` - UI/UX guide
- `TESTING_AND_WORKFLOW_GUIDE.md` - Testing guide
- `QUICK_REFERENCE.md` - This file!

---

## Success Indicators

✅ Cases evaluated automatically
✅ Strength scores calculated
✅ Final scores determined (-2 to +2)
✅ Follow-ups triggered for weak cases
✅ Agents activated with targeted questions
✅ KPI dashboard shows quality metrics
✅ Strong vs weak cases visible
✅ Quality trends monitored

**Your system is production-ready!**
