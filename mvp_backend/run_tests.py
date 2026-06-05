import json
import os
from decision_engine import adjudicate


def run_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Try same dir first (Railway), then parent (local dev)
    same_dir_path = os.path.join(base_dir, "test_cases.json")
    parent_path = os.path.join(base_dir, "..", "test_cases.json")
    tc_path = same_dir_path if os.path.exists(same_dir_path) else parent_path
    with open(os.path.abspath(tc_path), "r", encoding="utf-8") as f:
        cases = json.load(f).get("test_cases", [])
    passed = 0
    for c in cases:
        cid = c.get("case_id")
        inp = c.get("input_data")
        expected = c.get("expected_output")
        res = adjudicate(inp)
        ok = res.get("decision") == expected.get("decision")
        # Check approved amount when present in expected
        if expected.get("approved_amount") is not None:
            ok = ok and (res.get("approved_amount") == expected.get("approved_amount"))
        print(f"{cid}: {c.get('case_name')} -> expected: {expected.get('decision')}, got: {res.get('decision')}")
        if ok:
            passed += 1
    print(f"Passed {passed}/{len(cases)} test cases")


if __name__ == "__main__":
    run_all()
