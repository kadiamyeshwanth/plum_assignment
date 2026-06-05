# API Reference — Plum OPD Adjudication API

**Base URL (local):** `http://localhost:8000`  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)  
**Redoc:** `http://localhost:8000/redoc`

---

## Endpoints

### `GET /health`
Liveness check. Returns service status and total claims processed.

**Response:**
```json
{
  "status": "ok",
  "service": "Plum OPD Adjudication API",
  "version": "1.0.0",
  "timestamp": "2024-11-01T10:30:00.123456",
  "total_claims_processed": 5
}
```

---

### `POST /adjudicate`
Submit an OPD claim for adjudication. Core endpoint.

**Request Body:**
```json
{
  "case_id": "CLM_001",
  "member_id": "EMP001",
  "member_name": "Rajesh Kumar",
  "claim_amount": 1500,
  "treatment_date": "2024-11-01",
  "member_join_date": "2024-01-01",
  "hospital": "Apollo Hospitals",
  "cashless_request": false,
  "pre_auth_obtained": false,
  "previous_claims_same_day": 0,
  "documents": {
    "prescription": {
      "doctor_name": "Dr. Sharma",
      "doctor_reg": "KA/45678/2015",
      "diagnosis": "Viral fever",
      "medicines_prescribed": ["Paracetamol 650mg", "Vitamin C"],
      "tests_prescribed": ["CBC", "Dengue NS1"]
    },
    "bill": {
      "consultation_fee": 1000,
      "diagnostic_tests": 500
    }
  }
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `case_id` | string | No | Claim ID (default: CLM_XXXXX) |
| `member_id` | string | No | Employee ID |
| `member_name` | string | No | Member's full name |
| `claim_amount` | float | **Yes** | Total claimed amount in INR (> 0) |
| `treatment_date` | string | **Yes** | Treatment date (YYYY-MM-DD) |
| `member_join_date` | string | No | Policy start date for waiting period check (YYYY-MM-DD) |
| `hospital` | string | No | Hospital name (must match network list for cashless) |
| `cashless_request` | boolean | No | Whether this is a cashless claim (default: false) |
| `pre_auth_obtained` | boolean | No | Pre-authorization obtained for MRI/CT (default: false) |
| `previous_claims_same_day` | integer | No | Fraud signal: number of other claims same day (default: 0) |
| `documents.prescription` | object | No* | Prescription details (*required for approval) |
| `documents.bill` | object | No | Itemised bill with numeric amounts |

**Doctor Registration Format:**
- Standard: `STATE_CODE/NUMBER/YEAR` (e.g. `KA/45678/2015`, `MH/23456/2018`)
- AYUSH: `AYUR/STATE/NUMBER/YEAR` (e.g. `AYUR/KL/2345/2019`)

**Response — APPROVED:**
```json
{
  "claim_id": "CLM_001",
  "decision": "APPROVED",
  "approved_amount": 1350,
  "rejection_reasons": [],
  "confidence_score": 0.95,
  "notes": "Claim approved.",
  "next_steps": "Reimbursement will be processed within 5-7 business days.",
  "deductions": {
    "copay": 150
  }
}
```

**Response — REJECTED:**
```json
{
  "claim_id": "CLM_002",
  "decision": "REJECTED",
  "approved_amount": 0,
  "rejection_reasons": ["MISSING_DOCUMENTS"],
  "confidence_score": 1.0,
  "notes": "A prescription from a registered doctor is mandatory for OPD claims.",
  "next_steps": "Resubmit with a valid prescription from a registered medical practitioner."
}
```

**Response — PARTIAL:**
```json
{
  "claim_id": "CLM_003",
  "decision": "PARTIAL",
  "approved_amount": 8000,
  "rejection_reasons": [],
  "rejected_items": ["teeth_whitening - cosmetic dental procedure (excluded)"],
  "confidence_score": 0.92,
  "notes": "Claim partially approved. Some items are not covered.",
  "next_steps": "The approved amount will be reimbursed. Excluded items cannot be appealed unless policy is updated."
}
```

**Response — MANUAL_REVIEW:**
```json
{
  "claim_id": "CLM_004",
  "decision": "MANUAL_REVIEW",
  "approved_amount": 0,
  "rejection_reasons": [],
  "confidence_score": 0.65,
  "notes": "Claim flagged for human review due to unusual patterns.",
  "next_steps": "A claims officer will review your submission within 2 business days.",
  "flags": ["Multiple claims from same provider on same day"]
}
```

**Decision Types:**

| Decision | Meaning |
|----------|---------|
| `APPROVED` | Claim fully approved; reimbursement will be processed |
| `REJECTED` | Claim denied; see `rejection_reasons` |
| `PARTIAL` | Some items approved, some rejected; see `rejected_items` |
| `MANUAL_REVIEW` | Flagged for human review; see `flags` |

**Rejection Reason Codes:**

| Code | Meaning |
|------|---------|
| `MISSING_DOCUMENTS` | Required prescription not submitted |
| `DOCTOR_REG_INVALID` | Doctor registration format invalid |
| `WAITING_PERIOD` | Treatment during applicable waiting period |
| `PRE_AUTH_MISSING` | MRI/CT scan requires pre-authorization |
| `SERVICE_NOT_COVERED` | Treatment/item excluded from policy |
| `COSMETIC_PROCEDURE` | Cosmetic procedure not covered |
| `PER_CLAIM_EXCEEDED` | Claim exceeds ₹5,000 per-claim limit |
| `BELOW_MIN_AMOUNT` | Claim below ₹500 minimum |

---

### `GET /claims`

List recent adjudicated claims.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | integer | 20 | Number of claims to return (1–100) |

**Response:**
```json
{
  "total": 10,
  "returned": 5,
  "claims": [
    {
      "claim_id": "CLM_001",
      "input": { ... },
      "result": { ... },
      "submitted_at": "2024-11-01T10:30:00.123456"
    }
  ]
}
```

---

### `GET /claims/{claim_id}`

Retrieve a specific claim record.

**Path Parameters:**

| Param | Description |
|-------|-------------|
| `claim_id` | The claim ID string (e.g. `CLM_TC001`) |

**Response:** Same structure as individual item in `/claims` list.

**Error (404):**
```json
{
  "detail": "Claim 'CLM_NOTFOUND' not found."
}
```

---

### `GET /policy`

Return the active policy summary (read-only).

**Response:**
```json
{
  "policy_id": "PLUM_OPD_2024",
  "policy_name": "Plum OPD Advantage",
  "annual_limit": 50000,
  "per_claim_limit": 5000,
  "covered_categories": ["consultation_fees", "diagnostic_tests", "pharmacy", "dental", "vision", "alternative_medicine"],
  "exclusions": ["Cosmetic procedures", "Weight loss treatments", "..."],
  "network_hospitals": ["Apollo Hospitals", "Fortis Healthcare", "..."],
  "submission_deadline_days": 30,
  "minimum_claim_amount": 500
}
```

---

## Error Handling

All errors return standard HTTP status codes with a JSON body:

```json
{
  "detail": "Human-readable error description"
}
```

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 404 | Resource not found |
| 422 | Validation error (invalid request body) |
| 500 | Internal server error |
