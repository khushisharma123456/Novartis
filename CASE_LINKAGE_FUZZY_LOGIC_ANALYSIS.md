# Case Linkage & Fuzzy Logic Analysis

## Summary
✅ **YES** - The application **DOES have a comprehensive case linkage model based on fuzzy logic** to prevent redundant data.

---

## 1. Database Model Support

### Patient Model (models.py)
The `Patient` model includes the following fields for case deduplication:

```python
# Case Linkage & Deduplication
linked_case_id = db.Column(db.String(20), db.ForeignKey('patient.id'), nullable=True)
match_score = db.Column(db.Float, nullable=True)  # Similarity score (0-1)
case_status = db.Column(db.String(20), default='Active')  # Active, Linked, Discarded
match_notes = db.Column(db.Text, nullable=True)  # Reason for linkage/discarding
```

**Case Status States:**
- `Active` - Original case
- `Linked` - Duplicate case linked to another case
- `Discarded` - Case marked as redundant/duplicate

---

## 2. Fuzzy Logic Implementation

### CaseMatchingEngine Class
Located in: `pv_backend/services/case_matching.py`

#### A. Similarity Scoring Breakdown (Weighted Average)

| Component | Weight | Method | Description |
|-----------|--------|--------|-------------|
| **Drug Name Match** | 40% | Exact Match | Must be identical drug |
| **Symptom Similarity** | 40% | Fuzzy String Match | Uses SequenceMatcher for text similarity |
| **Demographics** | 15% | Age + Gender | Age proximity (±10 years window) + Gender match |
| **Time Recency** | 5% | Temporal Proximity | Recent cases (within 30 days) weighted higher |

**Formula:**
```
Weighted Score = (Drug × 0.40) + (Symptoms × 0.40) + (Demographics × 0.15) + (Time × 0.05)
```

#### B. Individual Similarity Calculations

**1. Drug Name Matching (0 or 1.0)**
```python
drug_similarity = 1.0 if new_case_drug == existing_case_drug else 0.0
```
- Exact match required for this critical factor
- Case-insensitive comparison

**2. Symptom Similarity (0-1 fuzzy)**
```python
symptom_similarity = SequenceMatcher(None, text1, text2).ratio()
```
- Uses Python's SequenceMatcher for fuzzy text matching
- Normalized text (lowercase, stripped)
- Returns similarity coefficient between 0-1

**3. Age Similarity (0-1)**
```python
if age_diff <= 10 years:
    similarity = 1.0 - (age_diff / 20)
else:
    similarity = 0.5  # Low score for large age differences
```
- Maximum 10-year difference tolerance
- Linear degradation as age difference increases

**4. Gender Similarity**
```python
gender_similarity = 1.0 if genders_match else 0.5
```
- Exact match: 1.0
- Mismatch: 0.5 (slight penalty, not complete disqualification)

**5. Time Recency (0-1)**
```python
if days_diff <= 30:
    time_similarity = 1.0 - (days_diff / 30)
else:
    time_similarity = 0.2  # Older cases are less likely duplicates
```
- 30-day sliding window
- Recent cases (same day) score 1.0
- Cases older than 30 days score 0.2

---

## 3. Confidence Levels

Based on final similarity score:

| Score Range | Confidence Level |
|------------|-----------------|
| ≥ 0.9 | Very High |
| 0.75-0.89 | High |
| 0.6-0.74 | Medium |
| 0.4-0.59 | Low |
| < 0.4 | Very Low |

---

## 4. Automated Decision Logic

### Recommendation Engine
```
Score ≥ 0.90 → "DISCARD - Very likely duplicate"
Score 0.80-0.89 → "REVIEW - Likely duplicate"
Score < 0.80 → "ACCEPT - No matching cases found"
```

### Case Action Thresholds
```
Score ≥ 0.90 (auto_discard_threshold) → DISCARD
Score 0.80-0.89 → REVIEW (require manual confirmation)
Score < 0.80 → ACCEPT (new case)
```

---

## 5. API Endpoints for Case Management

### 1. Case Matching
**Endpoint:** `POST /api/cases/match`

**Request:**
```json
{
  "drugName": "Aspirin",
  "symptoms": "headache, dizziness",
  "age": 35,
  "gender": "Female",
  "threshold": 0.75
}
```

**Response:**
```json
{
  "success": true,
  "matches": [
    {
      "case_id": "PT-1234",
      "patient_name": "John Doe",
      "drug_name": "Aspirin",
      "symptoms": "headache, nausea",
      "similarity_score": 0.85,
      "confidence": "High",
      "breakdown": {
        "drug": 1.0,
        "symptoms": 0.82,
        "demographics": 0.7,
        "time_recency": 0.95
      }
    }
  ],
  "has_exact_match": false,
  "recommendation": "REVIEW - Likely duplicate",
  "action": "REVIEW"
}
```

### 2. Link Cases
**Endpoint:** `POST /api/cases/link`
- Links a new case to an existing case
- Stores match score and reasoning
- Updates case_status to "Linked"

### 3. Discard Case
**Endpoint:** `POST /api/cases/discard`
- Marks case as redundant
- Records reason for discarding
- Updates case_status to "Discarded"

### 4. Get Case Details
**Endpoint:** `GET /api/cases/<case_id>/details`
- Retrieves full case information including linkage data

---

## 6. Data Redundancy Prevention Features

### ✅ **What's Implemented**

1. **Automatic Duplicate Detection**
   - Before saving new case, system checks against existing cases
   - Provides similarity scores and recommendations

2. **Multi-Factor Matching**
   - Doesn't rely on single field (e.g., drug name only)
   - Combines drug, symptoms, demographics, time factors
   - More robust duplicate detection

3. **Configurable Thresholds**
   - Default threshold: 0.75 (75% similarity)
   - Can be adjusted per request
   - Allows flexibility for different use cases

4. **Manual Review Workflow**
   - Cases with 80-90% match require human review
   - Users can confirm if it's truly a duplicate
   - Cases above 90% auto-discarded with option to override

5. **Audit Trail**
   - Stores match score in database
   - Records linkage reason in match_notes
   - Tracks which case each duplicate links to

6. **Case Status Tracking**
   - Active: Original case
   - Linked: Confirmed duplicate
   - Discarded: Redundant case
   - Allows filtering out discarded cases in queries

---

## 7. Example Scenario

**New Case Submitted:**
- Drug: Aspirin
- Symptoms: "severe headache and dizziness"
- Age: 35
- Gender: Female

**Existing Similar Case:**
- Drug: Aspirin
- Symptoms: "headache and vertigo"
- Age: 34
- Gender: Female
- Created: 3 days ago

**Similarity Calculation:**
```
Drug Match: 1.0 × 0.40 = 0.40
Symptom Match: 0.78 × 0.40 = 0.312
Demographics: 0.95 × 0.15 = 0.1425
Time Recency: 0.9 × 0.05 = 0.045
────────────────────────
Total Score = 0.8895 (88.95%)
```

**Result:** 
- Confidence: High
- Action: REVIEW
- Decision: Require manual confirmation from pharmacovigilance officer

---

## 8. Key Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| Fuzzy Logic Matching | ✅ | SequenceMatcher-based text similarity |
| Multi-Factor Analysis | ✅ | Drug + Symptoms + Demographics + Time |
| Configurable Thresholds | ✅ | Default 0.75, adjustable per request |
| Automated Recommendations | ✅ | ACCEPT/REVIEW/DISCARD logic |
| Case Linking | ✅ | Stores parent-child relationships |
| Audit Trail | ✅ | Match scores and notes recorded |
| Database Support | ✅ | Models include all necessary fields |
| API Integration | ✅ | Full REST API for case management |

---

## 9. Code Location Reference

| Component | Location |
|-----------|----------|
| Database Models | [models.py](models.py#L50-L65) |
| Matching Engine | [pv_backend/services/case_matching.py](pv_backend/services/case_matching.py) |
| API Endpoints | [app.py](app.py#L837-L920) |
| Frontend Integration | Ready via REST APIs |

---

## Conclusion

The application has a **well-designed, production-ready case linkage system** that:
- ✅ Uses fuzzy logic for intelligent matching
- ✅ Prevents redundant data entry automatically
- ✅ Provides confidence-based recommendations
- ✅ Supports manual override when needed
- ✅ Maintains full audit trail of all linkages
- ✅ Is database-backed and API-exposed
