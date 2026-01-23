# Pharmacovigilance Backend Service

## Overview

This is a Flask-based backend service for Post-Marketing Surveillance (PMS) / Pharmacovigilance system. It collects, stores, normalizes, and manages post-marketing drug experience data from:

- **Doctors** - Clinical observations with medical context
- **Hospitals** - Institutional reports
- **Pharmacies** - Sale/dispensing data (requires verification)
- **AI Agents** - Follow-up responses

## Scoring Logic

Each case has a score between **-2 and +2**:

| Score | Meaning |
|-------|---------|
| -2 | Strong, well-documented Adverse Event |
| -1 | Weak/incomplete Adverse Event |
| 0 | Poor or unclear data |
| +1 | Moderate positive/no-AE experience |
| +2 | Strong, confirmed positive experience |

**Formula:** `Score = Polarity × Strength`

- **Polarity**: AE=-1, NO_AE=+1, UNCLEAR=0
- **Strength**: 0, 1, or 2 (based on data completeness)

## Project Structure

```
pv_backend/
├── __init__.py
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
│
├── models/             # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py                 # User authentication & roles
│   ├── reporter.py             # Reporter information
│   ├── experience_event.py     # Raw submission events
│   ├── normalized_experience.py # Normalized/structured data
│   ├── case_master.py          # Case records (drug+patient)
│   ├── case_score_history.py   # Score evolution tracking
│   ├── adverse_event.py        # Detailed AE information
│   ├── follow_up_request.py    # Follow-up tracking
│   ├── medical_validation.py   # Medical review records
│   ├── case_linking_log.py     # Case linking decisions
│   └── audit_log.py            # Comprehensive audit trail
│
├── auth/               # Authentication
│   ├── __init__.py     # JWT utilities & decorators
│   └── routes.py       # Auth API endpoints
│
├── services/           # Business logic
│   ├── __init__.py
│   ├── normalization_service.py  # Event normalization
│   ├── case_linking_service.py   # Case linking logic
│   ├── scoring_service.py        # Score calculation
│   ├── followup_service.py       # Follow-up management
│   └── audit_service.py          # Audit logging
│
└── routes/             # API routes
    ├── __init__.py
    ├── submission_routes.py  # /submit/* endpoints
    ├── case_routes.py        # /cases/* endpoints
    └── followup_routes.py    # /followups/* endpoints
```

## API Endpoints

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/login` | Login and get JWT tokens |
| POST | `/refresh` | Refresh access token |
| GET | `/me` | Get current user info |
| POST | `/verify-pharmacy/<id>` | Verify pharmacy (admin) |
| GET | `/unverified-pharmacies` | List unverified pharmacies (admin) |

### Submissions (`/api/submit`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/doctor` | Doctor clinical observation |
| POST | `/hospital` | Hospital/institutional report |
| POST | `/pharmacy` | Pharmacy sale/dispensing data |

### Cases (`/api/cases`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List cases with filters |
| GET | `/<id>` | Get case details |
| GET | `/<id>/score` | Get score history |
| POST | `/<id>/score/override` | Override case score |
| GET | `/<id>/follow-ups` | Get case follow-ups |
| PUT | `/<id>/status` | Update case status |
| GET | `/<id>/audit` | Get case audit log |

### Follow-ups (`/api/followups`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List follow-ups |
| GET | `/pending` | List pending follow-ups |
| GET | `/<id>` | Get follow-up details |
| POST | `/<id>/assign` | Assign follow-up |
| POST | `/<id>/complete` | Complete with response |
| POST | `/<id>/cancel` | Cancel follow-up |

## Setup

1. Install dependencies:
```bash
pip install -r pv_backend/requirements.txt
```

2. Set environment variables (optional):
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/pv_db
export SECRET_KEY=your-secret-key
export JWT_SECRET_KEY=your-jwt-secret
```

3. Run the server:
```bash
cd pv_backend
python app.py
```

The server runs on `http://localhost:5001` by default.

## User Roles

| Role | Description | Verification |
|------|-------------|--------------|
| DOCTOR | Can submit clinical observations | Not required |
| HOSPITAL | Can submit institutional reports | Not required |
| PHARMACY | Can submit dispensing data | Required |
| ADMIN | Full system access | Not required |

## Data Flow

1. **Submission** → Creates `ExperienceEvent`
2. **Normalization** → Creates `NormalizedExperience` with polarity/strength
3. **Case Linking** → Links to existing `CaseMaster` or creates new
4. **Scoring** → Updates `CaseScoreHistory` and `CaseMaster.current_score`
5. **Follow-up** → Creates `FollowUpRequest` if data is incomplete

## Compliance

- **No hard deletes** - All records use soft delete
- **Full audit trail** - Every action logged to `AuditLog`
- **Human override** - All automated decisions can be overridden
- **Idempotent APIs** - Duplicate submissions return same result
