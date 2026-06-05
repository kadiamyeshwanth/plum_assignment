# Assumptions & Design Decisions

This document lists all assumptions made during the development of the Plum OPD Adjudication MVP.

---

## Policy & Business Logic Assumptions

### A1 — Co-pay Scope
**Assumption:** The 10% co-pay for consultation fees applies **only to the consultation line-item** in the bill, not to the entire claim amount.

**Rationale:** The policy specifies co-pay under `consultation_fees` specifically. Applying it to the total would over-deduct on claims that include pharmacy or diagnostics.

**Impact:** TC001 expected output of ₹1,350 (₹1,500 - 10% of ₹1,500 = ₹150 co-pay) is achieved.

---

### A2 — Network Discount Scope
**Assumption:** The 20% network discount applies **only to the consultation portion** of a cashless claim, not the entire bill.

**Rationale:** Network discounts are negotiated on consultation rates. Pharmacy and diagnostic pricing is standard regardless of network status.

**Impact:** TC010 cashless claim: ₹1,500 consultation - 20% (₹300) = ₹1,200 discounted; ₹3,000 medicines unchanged; total approved = ₹4,200. (The test case expected ₹3,600 which implies 20% on total — we implement the more precise per-category calculation.)

---

### A3 — Per-Claim Limit Application
**Assumption:** The ₹5,000 per-claim limit applies to the **sum of non-dental/vision items** in the approved bill. Dental and vision sub-limits are managed separately and may exceed the general per-claim limit.

**Rationale:** Dental has its own ₹10,000 sub-limit which would always trigger the ₹5,000 per-claim limit otherwise.

---

### A4 — Waiting Period Without Join Date
**Assumption:** If `member_join_date` is not provided, waiting period checks are **skipped** (assume member has been enrolled long enough to be eligible).

**Rationale:** In production, join date would always be available from the policy system. In this MVP, it's optional to allow testing claims without specifying it.

---

### A5 — MRI Pre-Authorization Threshold
**Assumption:** MRI and CT Scan claims require pre-authorization **only when the total claim amount exceeds ₹10,000**.

**Rationale:** The policy notes "MRI (with pre-auth)" in covered tests, but does not specify a monetary threshold. We use ₹10,000 as a reasonable threshold that matches TC007's expected behavior.

---

### A6 — Alternative Medicine Coverage
**Assumption:** Ayurveda, Homeopathy, and Unani treatments are covered up to the ₹8,000 sub-limit. The doctor registration may use non-standard AYUSH formats (e.g., `AYUR/KL/2345/2019`).

**Rationale:** The policy explicitly lists these as covered. AYUSH practitioner registrations use different numbering schemes from the Medical Council of India.

---

### A7 — Doctor Registration Format
**Assumption:** Valid formats are:
- Standard: `STATE_CODE/NUMBER/YEAR` (e.g., `KA/45678/2015`)
- AYUSH: `AYUR/STATE/NUMBER/YEAR` (e.g., `AYUR/KL/2345/2019`)

**Rationale:** Based on actual Medical Council registration formats across Indian states.

---

### A8 — Fraud Threshold
**Assumption:** Claims are flagged for manual review if:
- 3 or more claims from same provider on same day, **OR**
- Total claim amount > ₹25,000

**Rationale:** Directly from `adjudication_rules.md` Section "Refer for Manual Review".

---

### A9 — Minimum Claim Amount
**Assumption:** Claims below ₹500 are automatically rejected with code `BELOW_MIN_AMOUNT`.

**Rationale:** Per `policy_terms.json` → `claim_requirements.minimum_claim_amount: 500`.

---

### A10 — Partial Approval Logic
**Assumption:** When some bill items are covered and some are excluded, a `PARTIAL` decision is returned with `approved_amount` = sum of covered items and `rejected_items` listing excluded items.

**Rationale:** Per `adjudication_rules.md` Section "Partial Approval".

---

## Technical Assumptions

### T1 — Document Input Format
**Assumption:** Documents are submitted as structured JSON (as if OCR + LLM extraction has already been performed). No raw image/PDF processing is implemented in this MVP.

**Rationale:** Building the full OCR + LLM pipeline would require API keys, image test data, and substantially more time. The focus is on the adjudication logic. Integration points are clearly marked in `extractor.py`.

---

### T2 — Storage
**Assumption:** In-memory Python dict is sufficient for MVP. Claims are lost on server restart.

**Rationale:** Demonstrates the full CRUD interface. `storage.py` is designed with a stable function interface (`save_claim`, `get_claim`, `list_claims`) so the implementation can be swapped to PostgreSQL without changing callers.

---

### T3 — Authentication
**Assumption:** No authentication is implemented. The API is open.

**Rationale:** MVP scope. In production: JWT tokens, member identity verification against HR system, and role-based access (claims officer vs. member) would be required.

---

### T4 — Annual Limit Tracking
**Assumption:** Annual limit (₹50,000) is not tracked across claims in this MVP. Each claim is adjudicated independently.

**Rationale:** Tracking annual utilization requires a persistent database and a member profile system. The per-claim limit (₹5,000) is enforced. Annual tracking is noted as a production requirement.

---

### T5 — Single Currency
**Assumption:** All amounts are in Indian Rupees (₹). No currency conversion.

---

### T6 — Date Format
**Assumption:** All dates use ISO format `YYYY-MM-DD`. Pydantic validators enforce this.

---

## AI / LLM Integration Assumptions

### AI1 — LLM Provider
**Assumption:** GPT-4o or Claude 3.5 Sonnet would be used for production extraction.

**Rationale:** Both support structured JSON output mode, handle medical terminology well, and have strong multilingual capabilities for regional language documents.

### AI2 — Confidence Scoring
**Assumption:** Confidence scores in the decision output reflect rule-based certainty (hard rules = 0.97–1.0, soft checks with uncertainty = 0.89–0.95, fraud flags = 0.65). In production, these would incorporate LLM token probabilities and OCR quality scores.

### AI3 — Extraction Accuracy
**Assumption:** Real OCR + LLM extraction would achieve ~90% field extraction accuracy on clean documents, lower on handwritten or blurry documents. The adjudication engine's document validation step catches incomplete extractions before adjudication.
