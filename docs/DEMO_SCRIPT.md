# Demo Script — Plum OPD Adjudication Tool
**Target duration: 5–7 minutes**

---

## Setup (Before Recording)

```bash
# Terminal 1: Start backend (no FastAPI? use stdlib server)
cd plum_intern_assignment/mvp_backend
python simple_server.py
# OR with FastAPI:
# pip install -r requirements.txt
# uvicorn app:app --reload --port 8000

# Verify backend:
# curl http://localhost:8000/health

# Open frontend:
# Open mvp_frontend/index.html in Chrome (double-click or drag to browser)
```

---

## Recording Script

### 00:00–00:30 — Introduction
> *"Hi, I'm [Name]. This is my submission for the Plum AI Automation Engineer intern assignment. I've built an AI-powered OPD claim adjudication tool — a full-stack web application that automates the approval and rejection of insurance claims using a rule-based decision engine with an AI extraction layer."*

**Show:** The live application in the browser — point out the dark UI, the stats bar, and the claim form.

---

### 00:30–01:30 — Architecture Overview
> *"Let me quickly walk you through the architecture before we dive into the demo."*

**Show the repo structure:**
```
plum_intern_assignment/
├── mvp_backend/
│   ├── app.py          ← FastAPI API with CORS, 5 endpoints
│   ├── decision_engine.py ← 5-step adjudication rule engine
│   ├── extractor.py    ← Mock AI/OCR extraction with validation
│   ├── models.py       ← Pydantic type-safe models
│   └── storage.py      ← In-memory claims store
└── mvp_frontend/
    └── index.html      ← Professional single-page UI
```

> *"The backend is a FastAPI application. When a claim comes in, it first goes through the extractor — which in production would run OCR on the uploaded image, then send the text to an LLM like GPT-4o to extract structured fields. For this MVP, I've built a validation layer that checks doctor registration formats, prescription completeness, and bill integrity. Then the decision engine runs a 5-step adjudication flow against the policy terms."*

**Point to:** `docs/ARCHITECTURE.md` for the full Mermaid diagram.

---

### 01:30–02:00 — Run Tests First
> *"Let me show you the test suite passing first."*

```bash
cd mvp_backend
python run_tests.py
```

> *"These are the 10 test cases provided in the assignment. The engine correctly handles all major scenarios."*

---

### 02:00–04:30 — Live Demo (3 scenarios)

#### Scenario 1: Simple Approved Claim (TC001)
> *"Let me click the TC001 preset — a simple consultation for viral fever."*

**Click:** `TC001 ✅ Approved` preset button
**Point out:** The form auto-fills with Dr. Sharma's prescription, a ₹1,000 consultation fee, and ₹500 diagnostics.

**Click:** `Adjudicate Claim`

> *"And we get: APPROVED, ₹1,350. The ₹150 deduction is the 10% co-pay on the ₹1,000 consultation fee. Confidence score 95%. The engine also tells the claimant their next steps: reimbursement in 5–7 days."*

---

#### Scenario 2: Partial Approval — Dental (TC002)
> *"Now let's look at a dental claim with a cosmetic procedure."*

**Click:** `TC002 🟡 Partial`

> *"This is a ₹12,000 claim: ₹8,000 root canal + ₹4,000 teeth whitening. The root canal is covered, but teeth whitening is a cosmetic procedure."*

**Click:** `Adjudicate Claim`

> *"PARTIAL — ₹8,000 approved. The rejected items list clearly shows why the whitening was excluded. This is exactly the kind of itemised transparency that saves back-and-forth with claimants."*

---

#### Scenario 3: Rejected — Waiting Period (TC005)
> *"Now something more complex — a waiting period rejection for diabetes."*

**Click:** `TC005 ❌ Waiting`

> *"Vikram joined on September 1st, 2024. He's claiming for diabetes treatment on October 15th — that's only 44 days in. The policy has a 90-day waiting period for diabetes."*

**Click:** `Adjudicate Claim`

> *"REJECTED — Waiting Period. The engine calculates the exact eligible date: November 30th, 2024. Clear, actionable messaging for the claimant."*

---

### 04:30–05:30 — Internals Walkthrough

**Open `decision_engine.py` in editor:**

> *"Here's the heart of the system — the 5-step adjudication flow. Step 0 checks minimum claim amount. Step 1 validates documents — if there's no prescription, it's an instant rejection. Step 2 runs waiting period checks for specific conditions. Step 3 checks MRI pre-authorization for high-value claims. Step 4 checks diagnosis-level exclusions. Step 5 is the itemised bill processor — it maps each bill line item to a coverage category, applies sub-limits, and accumulates the approved total."*

**Open `extractor.py`:**

> *"The extractor validates doctor registration numbers — you can see the regex patterns here for standard MCI format and AYUSH format. In production, these INTEGRATION NOTE comments mark exactly where you'd plug in Tesseract or Google Vision, then GPT-4o structured extraction."*

---

### 05:30–06:00 — API Docs
**Open:** `http://localhost:8000/docs`

> *"FastAPI auto-generates the Swagger UI. You can see all 5 endpoints — adjudicate, list claims, get claim by ID, policy summary, and health check. Every field is documented with types and descriptions."*

---

### 06:00–06:30 — What I'd Build Next

> *"Given more time, I'd add:*
> 1. *Real OCR integration using Tesseract locally, or Google Vision API for cloud — the integration points are already stubbed in extractor.py*
> 2. *An LLM extraction layer using GPT-4o's JSON mode to turn raw OCR text into structured claim fields*
> 3. *PostgreSQL storage — the storage.py interface is already designed for a clean DB swap*
> 4. *JWT authentication and a claims officer dashboard for manual review workflow*
> 5. *Annual limit tracking across claims for a member*
> 6. *RAG over policy documents for the LLM to cite specific policy clauses in rejection reasons"*

---

### 06:30 — Close
> *"The full source, API docs, architecture diagram, and assumptions document are in the repo. Thanks for reviewing — happy to discuss any part of the implementation."*

---

## Recording Tips
- Use Chrome DevTools Network tab to show the JSON payload being sent during submission
- Zoom in to 125% in the browser for readability
- Zoom in to the terminal output when running tests
- Show the claims history panel updating in real-time after each submission
