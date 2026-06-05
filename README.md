# Plum OPD Claim Adjudication Tool
### AI Automation Engineer Intern Assignment — Submission

An AI-powered full-stack web application that automates the adjudication (approval/rejection) of OPD insurance claims. Processes medical documents, validates against policy terms, and makes intelligent decisions with confidence scoring and clear reasoning.

---

## Quick Start (2 steps, no dependencies for basic mode)

### Option A — Zero-install (stdlib server)
```bash
cd mvp_backend
python simple_server.py
# Server runs at http://localhost:8000
```

### Option B — Full FastAPI (recommended)
```bash
cd mvp_backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Then open `mvp_frontend/index.html` in your browser.

> 💡 The API status indicator in the top-right corner of the UI will turn **green** when connected.

---

## Features

### Core Functionality ✅
| Feature | Status | Notes |
|---------|--------|-------|
| Document validation | ✅ | Doctor reg format, prescription completeness, bill validation |
| Waiting period checks | ✅ | Initial 30d, Diabetes 90d, Hypertension 90d, Joint 730d |
| Coverage verification | ✅ | Per-category sub-limits, exclusion lists |
| Per-claim limit enforcement | ✅ | ₹5,000 cap with proper category handling |
| Partial approval | ✅ | Itemised approval/rejection with reasons |
| Fraud detection | ✅ | Multiple same-day claims, high-value flagging |
| Manual review routing | ✅ | Confidence < 70%, fraud flags, >₹25,000 |
| Cashless network claims | ✅ | 20% consultation discount for network hospitals |
| Co-pay calculation | ✅ | 10% on consultation portion |
| Minimum claim amount | ✅ | ₹500 threshold |

### API Endpoints ✅
| Endpoint | Description |
|----------|-------------|
| `POST /adjudicate` | Submit and adjudicate a claim |
| `GET /claims` | List all claims (paginated) |
| `GET /claims/{id}` | Get specific claim by ID |
| `GET /policy` | Active policy summary |
| `GET /health` | Liveness check |
| `GET /docs` | Auto-generated Swagger UI |

### User Interface ✅
- 🌙 **Dark premium UI** with Plum purple accent
- **3-step guided form** (Claim Info → Prescription → Bill Items)
- **Tag-based inputs** for medicines and tests
- **Itemised bill builder** with real-time total
- **8 pre-loaded test scenarios** (one click to load any test case)
- **Live claims history** panel with session tracking
- **Animated decision result** with confidence score bar
- **Session stats dashboard** (Total / Approved / Rejected / Review)
- **API health indicator** in header

### Bonus Features ✅
- Confidence scores on all decisions
- `next_steps` guidance on every decision
- LLM/OCR integration stubs with clear `# INTEGRATION NOTE` markers
- LLM extraction prompt template ready for GPT-4o / Claude

---

## Project Structure

```
plum_intern_assignment/
│
├── mvp_backend/
│   ├── app.py              # FastAPI application (CORS, 5 endpoints)
│   ├── decision_engine.py  # 5-step rule-based adjudication engine
│   ├── extractor.py        # Mock AI/OCR document extraction + validation
│   ├── models.py           # Pydantic v2 type-safe models
│   ├── storage.py          # In-memory claims store (DB-ready interface)
│   ├── simple_server.py    # Zero-dependency stdlib HTTP server
│   ├── run_tests.py        # Test harness for test_cases.json
│   └── requirements.txt    # Python dependencies
│
├── mvp_frontend/
│   └── index.html          # Professional single-page UI (zero build step)
│
├── docs/
│   ├── ARCHITECTURE.md     # System architecture + Mermaid diagrams
│   ├── API.md              # Full API reference
│   └── ASSUMPTIONS.md      # All design decisions documented
│
├── policy_terms.json        # Insurance policy configuration
├── adjudication_rules.md    # Business logic reference
└── test_cases.json          # 10 test scenarios with expected outputs
```

---

## Running the Test Suite

```bash
cd mvp_backend
python run_tests.py
```

Expected output (all 10 test cases):
```
✅ TC001 Simple Consultation - Approved
✅ TC002 Dental Treatment - Partial Approval
✅ TC003 Limit Exceeded - Rejected
✅ TC004 Missing Documents - Rejected
✅ TC005 Pre-existing Condition - Waiting Period
✅ TC006 Alternative Medicine - Approved
✅ TC007 Diagnostic Tests - Pre-auth Required
✅ TC008 Fraud Detection - Manual Review
✅ TC009 Excluded Treatment - Rejected
✅ TC010 Network Hospital - Cashless Approved
Passed 10/10 test cases
```

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Vanilla HTML/CSS/JS | Zero build step, instantly runnable, reviewers can open directly |
| API | FastAPI (Python) | Auto-generates OpenAPI docs; async-ready; Pydantic integration |
| Validation | Pydantic v2 | Type safety + input validation critical for financial/claims data |
| Rule Engine | Pure Python | Deterministic, auditable, testable — essential for insurance domain |
| Storage | In-memory dict | Zero-dependency MVP; clean interface for DB swap |
| Fonts | Google Fonts (Inter) | Professional, readable, free |

---

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system diagram.

**High-level flow:**
```
User (Browser)
  → POST /adjudicate
  → extractor.py (validates docs, simulates LLM extraction)
  → decision_engine.py (5-step rule engine)
  → storage.py (persist)
  → AdjudicationResult JSON
  → Frontend renders decision
```

---

## AI Integration

The `extractor.py` module contains:
1. **Doctor registration validation** — regex patterns for MCI and AYUSH formats
2. **Document completeness checks** — required fields for prescription and bill
3. **Confidence scoring** — field-level extraction confidence
4. **LLM integration stubs** marked with `# INTEGRATION NOTE`:
   - `extract_text_from_image()` — plug in Tesseract/Google Vision
   - `build_llm_extraction_prompt()` — ready-to-use GPT-4o prompt for structured field extraction

---

## Assumptions

See [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) for the complete list.

Key ones:
- Co-pay applies to consultation portion only (not entire bill)
- Network discount applies to consultation portion only
- Waiting period skipped if `member_join_date` not provided
- MRI pre-auth required for claims > ₹10,000
- Annual limit tracking requires persistent DB (not implemented in MVP)

---

## What I'd Add With More Time

1. **Real OCR** — Tesseract locally or Google Vision API; integration stubs already in place
2. **LLM extraction** — GPT-4o JSON mode; prompt template already written in `extractor.py`
3. **PostgreSQL storage** — `storage.py` interface is stable; only implementation changes needed
4. **JWT authentication** — Member identity verification against HR/policy system
5. **Annual limit tracking** — Track YTD utilization per member across claims
6. **Claims officer dashboard** — Manual review queue for MANUAL_REVIEW decisions
7. **RAG over policy docs** — LLM cites specific policy clauses in rejection reasons
8. **Appeal workflow** — Members can flag automated decisions for human review

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, components, tech decisions |
| [`docs/API.md`](docs/API.md) | Full API reference with request/response examples |
| [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) | All design decisions and their rationale |
| [`adjudication_rules.md`](adjudication_rules.md) | Business logic reference |
| [`policy_terms.json`](policy_terms.json) | Policy configuration |
