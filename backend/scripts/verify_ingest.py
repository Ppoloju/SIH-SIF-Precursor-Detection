"""Verify generic dataset ingestion end to end (dev utility).

Proves the pipeline works with ANY dataset, not only the synthetic demo set:

* a CSV whose columns deliberately do NOT match our demo schema,
* an HSSE-platform-export-style CSV (Report_id, Report_type, Site_name,
  Location_detail, Activity, Hazard_category, Description, …),
* auto column mapping (plus an explicit override check),
* multipart file upload + raw JSON rows import (background jobs),
* live job progress persisted in the database,
* extraction quality on unseen texts,
* analytics updating automatically,
* re-analysis of a stored report (process -> update).

Assumes the backend runs on http://127.0.0.1:8000.
"""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:8000"
failures: list[str] = []


def check(ok: bool, label: str) -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}")
    if not ok:
        failures.append(label)


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
        raise SystemExit(f"!! HTTP {exc.code} on {method} {path}: {exc.read().decode()[:400]}") from exc


def multipart_upload(path: str, filename: str, payload: bytes,
                     fields: dict[str, str] | None = None) -> dict:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for key, value in (fields or {}).items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\n".encode()
    )
    parts.append(payload)
    parts.append(b"\r\n" + f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        BASE + path, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def wait_job(job: dict, timeout: float = 90.0) -> dict:
    """Poll a background import job until it finishes."""
    job_id = job["job_id"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = call("GET", f"/api/ingest/jobs/{job_id}")
        if state["status"] in ("done", "error"):
            return state
        time.sleep(0.6)
    raise SystemExit(f"!! job {job_id} did not finish in {timeout}s")


# --- A deliberately foreign-format incident register -----------------------
CSV_HEADER = "Sl No,Date of Occurrence,Place of Occurrence,Nature of Job,Type of report," \
             "Detailed description of event,Immediate action taken\n"
CSV_ROWS = [
    "1,12-05-2026,Drilling Rig X,Drilling operation,Near Miss,"
    "Driller observed a suspended pipe wrench swinging above two rig crew heads when the tongs slipped; "
    "nobody was injured but the load could have struck them.,Work stopped and area barricaded",
    "2,2026-06-02,Compressor Station 7,Maintenance,Unsafe Act,"
    "Technician opened the flange of a pressurized gas line during maintenance without verifying isolation "
    "or bleed-off; gas vented under pressure.,Isolation verified and LOTO reapplied",
    "3,2026-07-19,Gathering Station 12,Welding,Unsafe Act,"
    "Welder carried out hot work close to the fuel storage area without a gas test and no fire watch was "
    "posted.,Hot work permit suspended and gas test done",
    "4,2026-08-25,Drilling Rig Y,Confined-space entry,Incident,"
    "Two workers entered the mud pit for cleaning without gas testing and the entry permit was not "
    "displayed; oxygen reading was not taken before entry.,Entry stopped and gas testing arranged",
    "5,2026-08-28,LPG Terminal,Housekeeping,Observation,"
    "Loose rubber hose left across the walkway near the loading bay could cause a trip.,Hose coiled and stored",
    "6,11-Apr-2026,Refinery South,Maintenance,Unsafe Act,"
    "Worker climbed onto the roof of the pump shed to adjust the antenna without a harness or edge "
    "protection; the sheet roof is fragile.,Work stopped and scaffold arranged",
]
FULL_CSV = CSV_HEADER + "".join(row + "\n" for row in CSV_ROWS)

# --- HSSE-platform-export style (exact prompt schema) ----------------------
HSSE_HEADER = "Report_id,Report_type,Site_name,Location_detail,Activity,Hazard_category," \
              "Description,actual_severity,potential_severity\n"
HSSE_ROWS = [
    "HSE-901,Unsafe Act,Zone 3 — Pipeline Terminal,Tie-in point near P-12 valve,Maintenance,Pressure/Energy,"
    "Operator began removing the blind flange without isolating the energy source — the line was still pressurized at 40 bar and no bleed valve was open.,Near miss,Potential fatality",
    "HSE-902,Near Miss,Zone 1 — Processing Plant,Distillation unit level 2,Confined space entry,Toxic atmosphere,"
    "Worker entered the reboiler vessel without a pre-entry gas test; the previous shift had purged it with hydrocarbon vapours.,No injury,Fatality possible",
    "HSE-903,Unsafe Act,Zone 2 — Drilling,Rig floor,Lifting operations,Dropped object,"
    "Tag line not attached while lifting the drill pipe stand over the crew area; load swung during lift.,Near miss,Potential serious injury",
    "HSE-904,Unsafe Condition,Zone 1 — Processing Plant,Heat exchanger platform,Hot work,Fire/explosion,"
    "Gas cylinders stored beside the welding point without separation and the area was not gas tested before hot work.,No injury,Potential fatality",
]
FULL_HSSE = HSSE_HEADER + "".join(row + "\n" for row in HSSE_ROWS)


def main() -> None:
    print("== Before import ==")
    ov0 = call("GET", "/api/analytics/overview")
    total0 = ov0["total_reports"]
    print(f"  total reports: {total0}")

    print("\n== 1) Preview the foreign CSV (multipart) ==")
    preview = multipart_upload("/api/ingest/file/preview", "incident_register_2026.csv", FULL_CSV.encode())
    mapping = preview["mapping"]
    print(f"  detected mapping: {json.dumps(mapping)}")
    check(mapping.get("text") == "Detailed description of event", "text column auto-detected")
    check(mapping.get("date") == "Date of Occurrence", "date column auto-detected")
    check(mapping.get("site") == "Place of Occurrence", "site column auto-detected")
    check(mapping.get("activity") == "Nature of Job", "activity column auto-detected")
    check(mapping.get("report_type") == "Type of report", "report_type column auto-detected")
    check(preview["total_rows"] == 6, "preview reports correct row count (no writes)")
    check(preview["samples"][0]["date"] == "2026-05-12", f"row date normalized ({preview['samples'][0]['date']})")

    print("\n== 2) Import the CSV as a background job ==")
    job = multipart_upload("/api/ingest/file", "incident_register_2026.csv", FULL_CSV.encode())
    check(job.get("job_id") and job["status"] == "running", f"job started (id={job.get('job_id')})")
    res = wait_job(job)
    check(res["status"] == "done", "job finished")
    check(res["imported"] == 6 and res["failed_count"] == 0, f"imported 6 rows (imported={res['imported']}, failed={res['failed_count']})")
    check(res["sif_potential"] >= 4, f"SIF detections on foreign text ({res['sif_potential']})")

    print("\n== 3) Extraction quality on unseen rows ==")
    lst = call("GET", "/api/reports?limit=500")
    for snippet, rule, activity in [
        ("Technician opened the flange of a pressurized gas", "Energy Isolation", "Maintenance"),
        ("Welder carried out hot work close to the fuel storage", "Hot Work", "Welding"),
        ("Two workers entered the mud pit for cleaning without gas", "Confined Space", "Confined-space entry"),
    ]:
        report = next((r for r in lst if snippet.lower() in (r["report_text"] or "")[:300].lower()), None)
        if not report:
            check(False, f"row found for '{snippet[:30]}…'")
            continue
        an = report["analysis"] or {}
        check(an.get("sif_potential") is True, f"'{snippet[:28]}…' flagged SIF")
        check(an.get("life_saving_rule") == rule, f"'{snippet[:28]}…' rule == {rule} (got {an.get('life_saving_rule')})")
        check(an.get("evidence"), f"'{snippet[:28]}…' has evidence ({len(an.get('evidence') or [])} phrases)")
        effective = report.get("activity") or an.get("activity")
        check(effective == activity, f"activity = {effective} (expected {activity})")

    print("\n== 4) Mapping override is honoured ==")
    preview2 = multipart_upload("/api/ingest/file/preview", "incident_register_2026.csv", FULL_CSV.encode(),
                                {"field_mapping": json.dumps({"site": "Nature of Job"})})
    check(preview2["mapping"]["site"] == "Nature of Job", "explicit mapping override wins")

    print("\n== 5) HSSE-platform-export CSV (exact prompt schema) ==")
    hse_preview = multipart_upload("/api/ingest/file/preview", "hsse_export_2026.csv", FULL_HSSE.encode())
    hm = hse_preview["mapping"]
    print(f"  detected mapping: {json.dumps(hm)}")
    check(hm.get("text") == "Description", "HSSE: Description -> text")
    check(hm.get("report_type") == "Report_type", "HSSE: Report_type -> type")
    check(hm.get("site") == "Site_name", "HSSE: Site_name -> site")
    check(hm.get("activity") == "Activity", "HSSE: Activity -> activity")
    check(hm.get("date") is None, "HSSE: no date column -> not mapped")
    sample0 = hse_preview["samples"][0]
    check(sample0["site"] == "Zone 3 — Pipeline Terminal · Tie-in point near P-12 valve",
          f"HSSE: Location_detail merged into site ({sample0['site']!r})")

    job2 = multipart_upload("/api/ingest/file", "hsse_export_2026.csv", FULL_HSSE.encode(), {"source": "hsse-export-oct"})
    res2 = wait_job(job2)
    check(res2["status"] == "done" and res2["imported"] == 4, f"HSSE import done ({res2['imported']} rows)")
    check(res2["sif_potential"] >= 2, f"HSSE rows flagged SIF ({res2['sif_potential']})")
    hse_report = next(r for r in call("GET", "/api/reports?limit=500") if (r["report_text"] or "").startswith("Operator began removing the blind flange"))
    an = hse_report["analysis"] or {}
    check(an.get("life_saving_rule") == "Energy Isolation", f"HSSE row rule (got {an.get('life_saving_rule')})")
    check(hse_report["source"] == "upload:hsse-export-oct", "custom source label stored")

    print("\n== 6) Job progress persisted in the database ==")
    jobs = call("GET", "/api/ingest/jobs")
    latest = jobs[0]
    check(latest["status"] == "done" and latest["imported"] == 4, "recent jobs listed with final counters")
    check(latest["rows_total"] >= latest["processed"] >= latest["imported"],
          f"progress counters consistent (processed={latest['processed']}, imported={latest['imported']})")

    print("\n== 7) JSON rows import (background job) ==")
    rows = [
        {"Sl No": 7, "Occurrence Date": "2026-09-01", "Spot": "Field A",
         "Task": "Lifting", "Description": "Crane lifted the pipe bundle beyond its rated capacity with "
         "no banksman guiding the load over the workers' heads."},
        {"Sl No": 8, "Occurrence Date": "2026-09-02", "Spot": "Field B",
         "Task": "Electrical work", "Description": "Electrician worked on a live switchboard without "
         "isolating the circuit; no insulated gloves were worn."},
    ]
    job3 = call("POST", "/api/ingest/rows", {"rows": rows, "source": "client-paste"})
    res3 = wait_job(job3)
    check(res3["status"] == "done" and res3["imported"] == 2, f"imported 2 JSON rows (imported={res3['imported']})")
    check(res3.get("failures") in (None, []), "no row failures")

    print("\n== 8) Analytics update automatically ==")
    ov1 = call("GET", "/api/analytics/overview")
    expected_total = total0 + 6 + 4 + 2
    check(ov1["total_reports"] == expected_total, f"total went {total0} -> {ov1['total_reports']} (expected {expected_total})")
    check(isinstance(ov1["sif_density"], (int, float)) and 0 < ov1["sif_density"] <= 100, f"SIF density present ({ov1.get('sif_density')}%)")
    check(ov1.get("latest_report_at"), "data freshness timestamp present")
    print(f"  SIF={ov1['sif_potential_reports']} density={ov1['sif_density']}% HIGH={ov1['high_priority_reports']} top_rule={ov1['top_life_saving_rule']}")

    print("\n== 9) Re-analyze a stored report (process -> update) ==")
    target = next(r for r in call("GET", "/api/reports?limit=500")
                  if r["source"] == "upload:incident_register_2026.csv")
    updated = call("POST", f"/api/reports/{target['id']}/reanalyze")
    check(updated["analysis"] is not None and updated["review_status"] == "pending",
          "re-analysis updates the stored result and resets review state")

    print("\n== 10) Provenance + processing labels ==")
    lst2 = call("GET", "/api/reports?limit=500")
    sources, states = {}, {}
    for r in lst2:
        key = r.get("source") or "none"
        sources[key] = sources.get(key, 0) + 1
        states[r.get("processing_status", "analyzed")] = states.get(r.get("processing_status", "analyzed"), 0) + 1
    print(f"  sources: {sources}")
    print(f"  processing states: {states}")
    check(states.get("analyzed", 0) == len(lst2), "all imported rows reached 'analyzed' state")

    print()
    if failures:
        print(f"FAILED: {len(failures)} checks -> {failures}")
        sys.exit(1)
    print("ALL INGEST CHECKS PASSED")


if __name__ == "__main__":
    main()
