"""Quick API smoke test (dev utility).

Assumes the backend is already running on http://127.0.0.1:8000.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"  !! HTTP {exc.code} on {method} {path}: {exc.read().decode()[:300]}")
        sys.exit(1)


print("1) health:", call("GET", "/api/health"))

print("2) analyze (store) ->", end=" ")
r = call("POST", "/api/reports/analyze", {
    "report_text": "During maintenance, the technician started work on a pipeline without properly isolating the energy source.",
    "report_type": "Unsafe Act",
    "site": "Site A - Pipeline Terminal",
})
rep = r["report"]
print(f"{rep['report_id']} sif={rep['analysis']['sif_potential']} prio={rep['analysis']['priority']} rule={rep['analysis']['life_saving_rule']}")

print("3) create (hand on shaft) ->", end=" ")
r2 = call("POST", "/api/reports", {
    "report_text": "Incident: worker's hand contacted the rotating shaft; the guard was missing.",
    "report_type": "Incident",
    "site": "Site B - Processing Plant",
    "activity": "Maintenance",
})
print(f"{r2['report_id']} sif={r2['analysis']['sif_potential']} rule={r2['analysis']['life_saving_rule']} status={r2['review_status']}")

print("4) list reports ->", end=" ")
lst = call("GET", "/api/reports?limit=3")
print(f"{len(lst)} returned (showing 3); first: {lst[0]['report_id']}")

print("5) filter sif=true ->", end=" ")
sif_list = call("GET", "/api/reports?sif=true&limit=500")
print(f"{len(sif_list)} SIF reports")

print("6) get report ->", end=" ")
detail = call("GET", f"/api/reports/{rep['id']}")
print(f"{detail['report_id']} analysis.id={detail['analysis']['id'] if detail['analysis'] else None}")

print("7) overview ->", end=" ")
ov = call("GET", "/api/analytics/overview")
print(f"total={ov['total_reports']} sif={ov['sif_potential_reports']} high={ov['high_priority_reports']} top_rule={ov['top_life_saving_rule']}")

print("8) review (confirm) ->", end=" ")
rv = call("PATCH", f"/api/reports/{rep['id']}/review", {
    "reviewer": "HSE Officer Demo",
    "decision": "confirmed",
    "comments": "Valid detection — isolation was not verified before work.",
    "mark_reviewed": True,
})
print(f"decision={rv['decision']} status={rv['report']['review_status']}")

print("9) empty report ->", end=" ")
try:
    call("POST", "/api/reports/analyze", {"report_text": "   "})
    print("  !! should have failed")
except SystemExit:
    print("rejected (validation works)")

print("\nALL SMOKE TESTS PASSED")