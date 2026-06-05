"""
Document extraction module for the Plum OPD Adjudication system.

MVP Strategy:
  - In production: pipe document bytes through OCR (Tesseract / Google Vision)
    then send extracted text to an LLM (GPT-4o / Claude) with a structured
    extraction prompt to get JSON fields.
  - For this MVP: we simulate that pipeline. The incoming payload already
    carries structured 'documents' (as if OCR+LLM already ran). We validate
    those fields and return extraction metadata including confidence scores and
    validation flags — exactly what a real LLM extraction layer would produce.

Integration points marked with # INTEGRATION NOTE for future replacement.
"""
import re
from typing import Any, Dict, List, Tuple


# ------------------------------------------------------------------
# Doctor registration number validator
# Accepted formats:
#   Standard Allopathy : STATE_CODE/NUMBER/YEAR  (e.g. KA/45678/2015)
#   AYUSH practitioners : AYUR/STATE/NUMBER/YEAR (e.g. AYUR/KL/2345/2019)
# ------------------------------------------------------------------
_DR_REG_PATTERNS = [
    re.compile(r"^[A-Z]{2}/\d{4,6}/\d{4}$"),          # e.g. KA/45678/2015
    re.compile(r"^AYUR/[A-Z]{2}/\d{3,6}/\d{4}$"),     # e.g. AYUR/KL/2345/2019
    re.compile(r"^[A-Z]{2,4}/[A-Z]{2}/\d{4,6}/\d{4}$"),  # generic AYUSH variants
]


def _validate_doctor_reg(reg: str) -> Tuple[bool, str]:
    """Validate doctor registration number format. Returns (is_valid, note)."""
    if not reg:
        return False, "Doctor registration number missing"
    for pattern in _DR_REG_PATTERNS:
        if pattern.match(reg.strip().upper()):
            return True, "Doctor registration number valid"
    return False, f"Doctor registration number format invalid: {reg}"


def _check_prescription_completeness(prescription: Dict[str, Any]) -> List[str]:
    """Return list of missing required prescription fields."""
    missing = []
    required = ["doctor_name", "doctor_reg", "diagnosis"]
    for field in required:
        if not prescription.get(field):
            missing.append(field)
    has_meds_or_treatment = (
        prescription.get("medicines_prescribed")
        or prescription.get("treatment")
        or prescription.get("procedures")
        or prescription.get("tests_prescribed")
    )
    if not has_meds_or_treatment:
        missing.append("medicines_prescribed / treatment / procedures")
    return missing


def _check_bill_completeness(bill: Dict[str, Any]) -> List[str]:
    """Return list of issues with the bill."""
    issues = []
    if not bill:
        issues.append("Bill document is empty or missing")
        return issues
    has_numeric = any(
        True for v in bill.values()
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "").isdigit())
    )
    if not has_numeric:
        issues.append("Bill has no numeric line items")
    return issues


def extract_documents(upload_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main extraction entry-point called by the API layer.

    INTEGRATION NOTE:
      Replace this function body with:
        1. OCR call: text = ocr_service.extract(document_bytes)
        2. LLM call: structured = llm.extract_fields(text, schema=ClaimFields)
        3. Return structured dict

    For now we validate and return the incoming structured documents
    with added metadata.
    """
    docs = upload_payload.get("documents", {})
    prescription = docs.get("prescription") or {}
    bill = docs.get("bill") or {}

    validation_flags: List[str] = []
    extraction_confidence = 1.0

    # --- Validate prescription ---
    if prescription:
        reg = prescription.get("doctor_reg", "")
        reg_valid, reg_note = _validate_doctor_reg(reg)
        if not reg_valid:
            validation_flags.append(reg_note)
            extraction_confidence -= 0.15

        missing_rx = _check_prescription_completeness(prescription)
        if missing_rx:
            validation_flags.append(f"Prescription missing: {', '.join(missing_rx)}")
            extraction_confidence -= 0.10 * len(missing_rx)

    # --- Validate bill ---
    bill_issues = _check_bill_completeness(bill)
    if bill_issues:
        validation_flags.extend(bill_issues)
        extraction_confidence -= 0.05 * len(bill_issues)

    extraction_confidence = max(0.0, min(1.0, extraction_confidence))

    # Build extraction metadata
    extraction_meta = {
        "validation_flags": validation_flags,
        "doctor_reg_valid": not any("registration" in f.lower() for f in validation_flags),
        "documents_complete": len(validation_flags) == 0,
        "extraction_confidence": round(extraction_confidence, 2),
        "extracted_fields": {
            "diagnosis": (prescription.get("diagnosis") or "").lower(),
            "doctor_name": prescription.get("doctor_name"),
            "doctor_reg": prescription.get("doctor_reg"),
            "total_bill_items": len([k for k, v in bill.items()
                                     if isinstance(v, (int, float))]),
        },
    }

    # Return original docs enriched with extraction metadata
    return {**docs, "_extraction": extraction_meta}


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    INTEGRATION NOTE: Replace with real OCR pipeline.
    Options:
      - Tesseract: pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
      - Google Vision: vision_client.text_detection(image=vision.Image(content=image_bytes))
      - AWS Textract: textract_client.detect_document_text(Document={"Bytes": image_bytes})
    """
    # INTEGRATION NOTE
    return "[OCR extraction placeholder — integrate Tesseract or cloud OCR here]"


def build_llm_extraction_prompt(ocr_text: str) -> str:
    """
    INTEGRATION NOTE: Use this prompt with GPT-4o / Claude to extract structured fields.
    """
    return f"""You are a medical document extractor for an insurance company.
Extract the following fields from this medical document text and return as JSON:

{{
  "doctor_name": "string",
  "doctor_reg": "string (format: STATE/NUMBER/YEAR)",
  "diagnosis": "string",
  "medicines_prescribed": ["list of strings"],
  "tests_prescribed": ["list of strings"],
  "bill_items": {{"item_name": amount_in_rupees}},
  "treatment_date": "YYYY-MM-DD",
  "patient_name": "string"
}}

Document text:
{ocr_text}

Return only valid JSON. Use null for missing fields."""
