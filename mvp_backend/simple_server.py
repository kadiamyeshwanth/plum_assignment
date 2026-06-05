"""
Zero-dependency HTTP server for the Plum OPD Adjudication API.
Uses Python stdlib only — no pip install required.

Supports:
  GET  /health           — Liveness check
  GET  /claims           — List stored claims (?limit=N)
  GET  /claims/<id>      — Get claim by ID
  GET  /policy           — Policy summary
  POST /adjudicate       — Submit a claim

Run:  python simple_server.py
"""
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from decision_engine import adjudicate
from extractor import extract_documents
from storage import save_claim, get_claim, list_claims, claims_count

# Load policy for the /policy endpoint
_BASE = os.path.dirname(os.path.abspath(__file__))
_POLICY_PATH = (
    os.path.join(_BASE, "policy_terms.json")
    if os.path.exists(os.path.join(_BASE, "policy_terms.json"))
    else os.path.join(_BASE, "..", "policy_terms.json")
)
with open(os.path.abspath(_POLICY_PATH), "r", encoding="utf-8") as _f:
    _POLICY = json.load(_f)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter logs
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}")

    def _send(self, code: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        # CORS headers
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)

        if path == "/health":
            self._send(200, {
                "status": "ok",
                "service": "Plum OPD Adjudication API",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "total_claims_processed": claims_count(),
            })

        elif path == "/claims":
            limit = int(qs.get("limit", ["20"])[0])
            claims = list_claims(limit=limit)
            self._send(200, {
                "total": claims_count(),
                "returned": len(claims),
                "claims": claims,
            })

        elif path.startswith("/claims/"):
            claim_id = path[len("/claims/"):]
            record = get_claim(claim_id)
            if record is None:
                self._send(404, {"detail": f"Claim '{claim_id}' not found."})
            else:
                self._send(200, record)

        elif path == "/policy":
            coverage = _POLICY.get("coverage_details", {})
            self._send(200, {
                "policy_id": _POLICY.get("policy_id"),
                "policy_name": _POLICY.get("policy_name"),
                "annual_limit": coverage.get("annual_limit"),
                "per_claim_limit": coverage.get("per_claim_limit"),
                "covered_categories": [k for k, v in coverage.items() if isinstance(v, dict)],
                "exclusions": _POLICY.get("exclusions", []),
                "network_hospitals": _POLICY.get("network_hospitals", []),
                "submission_deadline_days": _POLICY.get("claim_requirements", {}).get("submission_timeline_days"),
                "minimum_claim_amount": _POLICY.get("claim_requirements", {}).get("minimum_claim_amount"),
            })

        elif path in ("", "/docs"):
            self._send(200, {
                "message": "Plum OPD Adjudication API",
                "version": "1.0.0",
                "endpoints": {
                    "POST /adjudicate": "Submit and adjudicate a claim",
                    "GET /health": "Liveness check",
                    "GET /claims": "List claims (optional ?limit=N)",
                    "GET /claims/{id}": "Get claim by ID",
                    "GET /policy": "Active policy summary",
                }
            })

        else:
            self._send(404, {"detail": "Endpoint not found."})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path != "/adjudicate":
            self._send(404, {"detail": "Not found."})
            return

        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            self._send(400, {"detail": f"Invalid JSON: {e}"})
            return

        # Basic validation
        if not isinstance(payload.get("claim_amount"), (int, float)):
            self._send(422, {"detail": "claim_amount must be a number."})
            return
        if not payload.get("treatment_date"):
            self._send(422, {"detail": "treatment_date is required."})
            return

        try:
            enriched_docs = extract_documents(payload)
            payload["documents"] = enriched_docs
            result = adjudicate(payload)
            save_claim(payload, result)
            self._send(200, result)
        except Exception as e:
            self._send(500, {"detail": f"Internal error: {e}"})


def run(port: int = 8000):
    server = HTTPServer(("", port), Handler)
    print(f"\nPlum OPD Adjudication API")
    print(f"   Running at: http://localhost:{port}")
    print(f"   Endpoints: GET /health | GET /claims | POST /adjudicate | GET /policy")
    print(f"   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    server.server_close()


if __name__ == "__main__":
    run()
