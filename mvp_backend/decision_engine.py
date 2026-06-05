"""
OPD Claim Adjudication Decision Engine
Plum Insurance — MVP Implementation

Implements the 5-step adjudication flow defined in adjudication_rules.md:
  Step 1: Basic Eligibility
  Step 2: Document Validation
  Step 3: Coverage Verification
  Step 4: Limit Validation
  Step 5: Medical Necessity / Fraud Detection

Loads policy from policy_terms.json (same repo root, resolved at runtime).
"""
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Policy loading
# ---------------------------------------------------------------------------

def _load_policy() -> Dict[str, Any]:
    """Load policy_terms.json — checks same dir first (Railway), then parent (local dev)."""
    base = os.path.dirname(os.path.abspath(__file__))
    # Try same directory first (Railway deploys with root = mvp_backend)
    same_dir = os.path.join(base, "policy_terms.json")
    parent_dir = os.path.join(base, "..", "policy_terms.json")
    path = same_dir if os.path.exists(same_dir) else parent_dir
    with open(os.path.abspath(path), "r", encoding="utf-8") as f:
        return json.load(f)


_POLICY: Dict[str, Any] = _load_policy()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sum_bill(bill: Dict[str, Any]) -> float:
    """Sum all numeric values in the bill dict."""
    total = 0.0
    for v in bill.values():
        try:
            total += float(v)
        except (TypeError, ValueError):
            continue
    return total


def _bill_category(item_key: str) -> str:
    """Map a bill line-item key to a coverage category."""
    k = item_key.lower().replace("_", " ").replace("-", " ")
    if any(x in k for x in ["consult", "consultation", "doctor fee", "visit"]):
        return "consultation_fees"
    if any(x in k for x in ["medicine", "pharmacy", "drug", "tablet", "capsule"]):
        return "pharmacy"
    if any(x in k for x in ["root canal", "root_canal", "filling", "extraction",
                              "cleaning", "dental"]):
        return "dental"
    if any(x in k for x in ["whitening", "cosmetic dental", "teeth whitening",
                              "bleaching"]):
        return "dental_cosmetic"
    if any(x in k for x in ["mri", "ct scan", "ultrasound", "x-ray", "xray",
                              "ecg", "blood test", "urine test", "scan", "diagnostic"]):
        return "diagnostic_tests"
    if any(x in k for x in ["therapy", "ayurved", "homeo", "unani", "alternative"]):
        return "alternative_medicine"
    if any(x in k for x in ["spectacle", "glasses", "contact lens", "eye test",
                              "vision", "optical"]):
        return "vision"
    if any(x in k for x in ["weight", "diet", "bariatric", "obesity", "slimming"]):
        return "excluded_weight_loss"
    if any(x in k for x in ["cosmetic", "aesthetic", "botox", "liposuction",
                              "rhinoplasty", "breast"]):
        return "excluded_cosmetic"
    return "other"


def _make_decision(
    *,
    claim_id: str,
    decision: str,
    approved_amount: float = 0,
    rejection_reasons: Optional[List[str]] = None,
    rejected_items: Optional[List[str]] = None,
    confidence_score: float = 0.9,
    notes: str = "",
    next_steps: str = "",
    deductions: Optional[Dict[str, Any]] = None,
    network_discount: Optional[float] = None,
    flags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build the standard decision output dict."""
    out: Dict[str, Any] = {
        "claim_id": claim_id,
        "decision": decision,
        "approved_amount": int(approved_amount),
        "rejection_reasons": rejection_reasons or [],
        "confidence_score": round(confidence_score, 2),
        "notes": notes,
        "next_steps": next_steps,
    }
    if rejected_items:
        out["rejected_items"] = rejected_items
    if deductions:
        out["deductions"] = deductions
    if network_discount is not None:
        out["network_discount"] = int(network_discount)
    if flags:
        out["flags"] = flags
    return out


# ---------------------------------------------------------------------------
# Main adjudication logic
# ---------------------------------------------------------------------------

def adjudicate(claim: Dict[str, Any]) -> Dict[str, Any]:  # noqa: C901
    """
    Run the full 5-step adjudication flow and return a decision dict.
    """
    policy = _POLICY
    claim_id = claim.get("case_id", "CLM_XXXXX")
    claim_amount = float(claim.get("claim_amount", 0))
    documents = claim.get("documents", {})
    bill: Dict[str, Any] = documents.get("bill") or {}
    prescription: Optional[Dict[str, Any]] = documents.get("prescription")
    extraction_meta: Dict[str, Any] = documents.get("_extraction") or {}

    coverage = policy.get("coverage_details", {})
    waiting_cfg = policy.get("waiting_periods", {})
    network_hospitals: List[str] = policy.get("network_hospitals", [])
    exclusions: List[str] = [e.lower() for e in policy.get("exclusions", [])]

    per_claim_limit = float(coverage.get("per_claim_limit", 5000))
    min_claim_amount = float(policy.get("claim_requirements", {}).get("minimum_claim_amount", 500))

    # -----------------------------------------------------------------------
    # Step 0: Minimum claim amount
    # -----------------------------------------------------------------------
    if claim_amount < min_claim_amount:
        return _make_decision(
            claim_id=claim_id,
            decision="REJECTED",
            rejection_reasons=["BELOW_MIN_AMOUNT"],
            confidence_score=1.0,
            notes=f"Claim amount ₹{int(claim_amount)} is below the minimum of ₹{int(min_claim_amount)}.",
            next_steps="Claims below ₹500 are not eligible. No further action required.",
        )

    # -----------------------------------------------------------------------
    # Step 1: Document validation
    # -----------------------------------------------------------------------
    if not prescription:
        return _make_decision(
            claim_id=claim_id,
            decision="REJECTED",
            rejection_reasons=["MISSING_DOCUMENTS"],
            confidence_score=1.0,
            notes="A prescription from a registered doctor is mandatory for OPD claims.",
            next_steps="Resubmit with a valid prescription from a registered medical practitioner.",
        )

    # Doctor registration validation (from extraction metadata or inline)
    if extraction_meta:
        if not extraction_meta.get("doctor_reg_valid", True):
            flags_from_extraction = extraction_meta.get("validation_flags", [])
            return _make_decision(
                claim_id=claim_id,
                decision="REJECTED",
                rejection_reasons=["DOCTOR_REG_INVALID"],
                confidence_score=0.97,
                notes="; ".join(flags_from_extraction) or "Doctor registration number is invalid or missing.",
                next_steps="Resubmit with a valid doctor registration number (format: STATE/NUMBER/YEAR).",
            )

    # -----------------------------------------------------------------------
    # Step 2: Waiting period checks
    # -----------------------------------------------------------------------
    diagnosis = (prescription.get("diagnosis") or "").lower()
    join_date_str = claim.get("member_join_date")
    treatment_date_str = claim.get("treatment_date", "2024-01-01")

    def _check_waiting(condition_key: str, display_name: str) -> Optional[Dict[str, Any]]:
        if condition_key not in diagnosis:
            return None
        days = int(
            waiting_cfg.get("specific_ailments", {}).get(
                condition_key,
                waiting_cfg.get("initial_waiting", 30),
            )
        )
        if join_date_str:
            join_dt = datetime.fromisoformat(join_date_str)
            eligible_dt = join_dt + timedelta(days=days)
            treat_dt = datetime.fromisoformat(treatment_date_str)
            if treat_dt < eligible_dt:
                return _make_decision(
                    claim_id=claim_id,
                    decision="REJECTED",
                    rejection_reasons=["WAITING_PERIOD"],
                    confidence_score=0.96,
                    notes=(
                        f"{display_name} has a {days}-day waiting period. "
                        f"Eligible from {eligible_dt.date()}."
                    ),
                    next_steps=f"Resubmit after {eligible_dt.date()} for {display_name}-related claims.",
                )
        return None

    for cond_key, display in [
        ("diabetes", "Diabetes"),
        ("hypertension", "Hypertension"),
        ("joint", "Joint Replacement"),
        ("maternity", "Maternity"),
    ]:
        result = _check_waiting(cond_key, display)
        if result:
            return result

    # Initial waiting period (first 30 days)
    if join_date_str:
        join_dt = datetime.fromisoformat(join_date_str)
        initial_days = int(waiting_cfg.get("initial_waiting", 30))
        eligible_dt = join_dt + timedelta(days=initial_days)
        treat_dt = datetime.fromisoformat(treatment_date_str)
        if treat_dt < eligible_dt:
            return _make_decision(
                claim_id=claim_id,
                decision="REJECTED",
                rejection_reasons=["WAITING_PERIOD"],
                confidence_score=0.96,
                notes=(
                    f"Policy has a {initial_days}-day initial waiting period. "
                    f"Eligible from {eligible_dt.date()}."
                ),
                next_steps=f"Resubmit after {eligible_dt.date()}.",
            )

    # -----------------------------------------------------------------------
    # Step 3: Pre-authorization for MRI / CT Scan
    # -----------------------------------------------------------------------
    bill_keys_lower = " ".join(bill.keys()).lower()
    tests_rx = prescription.get("tests_prescribed") or prescription.get("tests") or []
    tests_lower = " ".join(str(t).lower() for t in tests_rx)

    needs_mri_pre_auth = ("mri" in bill_keys_lower or "mri" in tests_lower)
    needs_ct_pre_auth = ("ct scan" in bill_keys_lower or "ct" in tests_lower)

    if (needs_mri_pre_auth or needs_ct_pre_auth) and claim_amount > 10000:
        if not claim.get("pre_auth_obtained", False):
            scan_type = "MRI" if needs_mri_pre_auth else "CT Scan"
            return _make_decision(
                claim_id=claim_id,
                decision="REJECTED",
                rejection_reasons=["PRE_AUTH_MISSING"],
                confidence_score=0.94,
                notes=f"{scan_type} requires pre-authorization for claims above ₹10,000.",
                next_steps=f"Obtain pre-authorization for {scan_type} and resubmit the claim.",
            )

    # -----------------------------------------------------------------------
    # Step 4: Diagnosis-level exclusion check
    # -----------------------------------------------------------------------
    exclusion_keywords = {
        "cosmetic": "COSMETIC_PROCEDURE",
        "weight loss": "SERVICE_NOT_COVERED",
        "infertility": "SERVICE_NOT_COVERED",
        "experimental": "SERVICE_NOT_COVERED",
        "hiv": "SERVICE_NOT_COVERED",
        "aids": "SERVICE_NOT_COVERED",
        "alcoholism": "SERVICE_NOT_COVERED",
        "drug abuse": "SERVICE_NOT_COVERED",
    }
    for keyword, reason_code in exclusion_keywords.items():
        if keyword in diagnosis:
            exc_display = keyword.title()
            return _make_decision(
                claim_id=claim_id,
                decision="REJECTED",
                rejection_reasons=[reason_code],
                confidence_score=0.97,
                notes=f"{exc_display}-related treatments are excluded from coverage under this policy.",
                next_steps="This condition/treatment is not covered. Please refer to your policy exclusions list.",
            )

    # -----------------------------------------------------------------------
    # Step 5: Itemised bill processing — approve covered, reject excluded
    # -----------------------------------------------------------------------
    approved_items: Dict[str, float] = {}
    rejected_items: List[str] = []
    partial_notes: List[str] = []

    for item_key, item_val in bill.items():
        if item_key.startswith("_") or item_key == "test_names":
            continue
        try:
            amt = float(item_val)
        except (TypeError, ValueError):
            continue

        cat = _bill_category(item_key)

        # Hard exclusions at item level
        if cat == "excluded_weight_loss":
            return _make_decision(
                claim_id=claim_id,
                decision="REJECTED",
                rejection_reasons=["SERVICE_NOT_COVERED"],
                confidence_score=0.97,
                notes=f"'{item_key}' is a weight-loss/bariatric item excluded from coverage.",
                next_steps="Weight loss and bariatric treatments are not covered. Review your policy exclusions.",
            )
        if cat == "excluded_cosmetic":
            rejected_items.append(f"{item_key} - cosmetic procedure (excluded)")
            continue

        # Dental cosmetic
        if cat == "dental_cosmetic":
            rejected_items.append(f"{item_key} - cosmetic dental procedure (excluded)")
            continue

        # Apply sub-limits
        cat_coverage = coverage.get(cat, {})
        if isinstance(cat_coverage, dict):
            sub_limit = cat_coverage.get("sub_limit")
            if sub_limit is not None and amt > float(sub_limit):
                approved_items[item_key] = float(sub_limit)
                partial_notes.append(
                    f"{item_key}: capped at sub-limit ₹{int(sub_limit)} (claimed ₹{int(amt)})"
                )
            else:
                approved_items[item_key] = amt
        else:
            # Default: approve if not explicitly excluded
            approved_items[item_key] = amt

    total_approved_raw = sum(approved_items.values())

    # -----------------------------------------------------------------------
    # Per-claim limit enforcement
    # -----------------------------------------------------------------------
    # Only dental/vision-only claims bypass the standard per-claim limit
    non_dental_vision = {
        k: v for k, v in approved_items.items()
        if _bill_category(k) not in ("dental", "vision")
    }
    if non_dental_vision:
        total_non_dv = sum(non_dental_vision.values())
        dental_vision_total = total_approved_raw - total_non_dv
        if total_non_dv > per_claim_limit:
            return _make_decision(
                claim_id=claim_id,
                decision="REJECTED",
                rejection_reasons=["PER_CLAIM_EXCEEDED"],
                confidence_score=0.98,
                notes=f"Claim total ₹{int(total_non_dv)} exceeds the per-claim limit of ₹{int(per_claim_limit)}.",
                next_steps="You may split large claims across multiple submissions within the annual limit.",
            )

    # -----------------------------------------------------------------------
    # Fraud / Manual review flags
    # -----------------------------------------------------------------------
    fraud_flags: List[str] = []
    if claim.get("previous_claims_same_day", 0) >= 3:
        fraud_flags.append("Multiple claims from same provider on same day")
    if claim_amount > 25000:
        fraud_flags.append("High-value claim (>₹25,000) requires manual review")

    if fraud_flags:
        return _make_decision(
            claim_id=claim_id,
            decision="MANUAL_REVIEW",
            confidence_score=0.65,
            notes="Claim flagged for human review due to unusual patterns.",
            next_steps="A claims officer will review your submission within 2 business days.",
            flags=fraud_flags,
        )

    # -----------------------------------------------------------------------
    # Partial approval
    # -----------------------------------------------------------------------
    if rejected_items and total_approved_raw > 0:
        return _make_decision(
            claim_id=claim_id,
            decision="PARTIAL",
            approved_amount=total_approved_raw,
            rejected_items=rejected_items,
            confidence_score=0.92,
            notes="Claim partially approved. Some items are not covered.",
            next_steps="The approved amount will be reimbursed. Excluded items cannot be appealed unless policy is updated.",
        )

    if total_approved_raw == 0 and rejected_items:
        return _make_decision(
            claim_id=claim_id,
            decision="REJECTED",
            rejection_reasons=["SERVICE_NOT_COVERED"],
            confidence_score=0.97,
            notes="All claimed items are excluded or not covered under the policy.",
            next_steps="Review your policy coverage document. Contact support to understand your coverage.",
        )

    # -----------------------------------------------------------------------
    # Network hospital cashless discount
    # -----------------------------------------------------------------------
    approved_base = total_approved_raw if total_approved_raw > 0 else claim_amount

    if claim.get("hospital") in network_hospitals and claim.get("cashless_request"):
        discount_pct = float(coverage.get("consultation_fees", {}).get("network_discount", 0))
        # Network discount applies to the full approved bill amount for cashless claims
        network_disc = approved_base * (discount_pct / 100.0)
        final_cashless = approved_base - network_disc
        return _make_decision(
            claim_id=claim_id,
            decision="APPROVED",
            approved_amount=final_cashless,
            confidence_score=0.93,
            notes=f"Cashless claim approved at {claim.get('hospital')}. {int(discount_pct)}% network discount applied.",
            next_steps="Cashless settlement will be processed directly with the hospital.",
            network_discount=network_disc,
        )

    # -----------------------------------------------------------------------
    # Standard approval with copay
    # -----------------------------------------------------------------------
    copay_pct = float(coverage.get("consultation_fees", {}).get("copay_percentage", 0))

    # Co-pay applies to the full approved amount when the claim includes standard consultation.
    # Alternative medicine, dental, and vision claims are exempt from co-pay.
    # If ANY non-consultation item is alternative medicine, the whole claim is exempt.
    has_alt_medicine = any(_bill_category(k) == "alternative_medicine" for k in approved_items)
    has_dental_only = all(_bill_category(k) in ("dental", "dental_cosmetic") for k in approved_items)
    has_vision_only = all(_bill_category(k) == "vision" for k in approved_items)

    if has_alt_medicine or has_dental_only or has_vision_only:
        copay_amount = 0.0
    else:
        copay_amount = approved_base * (copay_pct / 100.0) if copay_pct else 0.0

    final_amount = approved_base - copay_amount

    extra_notes = " | ".join(partial_notes) if partial_notes else ""
    full_notes = "Claim approved." + (f" Note: {extra_notes}" if extra_notes else "")

    result = _make_decision(
        claim_id=claim_id,
        decision="APPROVED",
        approved_amount=final_amount,
        confidence_score=0.95,
        notes=full_notes,
        next_steps="Reimbursement will be processed within 5-7 business days.",
    )
    if copay_amount:
        result["deductions"] = {"copay": int(copay_amount)}
    return result


# ---------------------------------------------------------------------------
# CLI quick-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json as _json
    tc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_cases.json"))
    with open(tc_path, "r", encoding="utf-8") as f:
        cases = _json.load(f).get("test_cases", [])
    for c in cases:
        res = adjudicate(c.get("input_data", {}))
        exp = c.get("expected_output", {})
        match = "✅" if res.get("decision") == exp.get("decision") else "❌"
        print(f"{match} {c.get('case_id')} {c.get('case_name')}: "
              f"expected={exp.get('decision')}, got={res.get('decision')}, "
              f"amount={res.get('approved_amount')}")
