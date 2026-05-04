#!/usr/bin/env python3
"""Quick test: run pipeline via step-by-step endpoints and save to chat_sessions."""
import sys, os, time, json
sys.path.insert(0, "/home/sanju/AI SWAT Hackathon/proofline-ai")
os.chdir("/home/sanju/AI SWAT Hackathon/proofline-ai")
import httpx
from datetime import datetime, timezone

API = "http://localhost:8000"
T = 180.0

gl_text = """1 — Product Name
Always refer to the product as "BrightPath" with exact capitalization. Never use "brightpath", "BRIGHTPATH", or "Bright Path" (two words).

2 — Prohibited Words
The following words are banned in all content:
- innovative (replace with "effective" or "practical")
- cutting-edge (replace with "modern" or "advanced")
- disrupt (replace with "improve" or "transform")

3 — Tone
Write in a friendly but professional tone. Do not use overly casual language like "awesome", "cool", or "super easy". Do not use aggressive sales language like "buy now" or "act fast".

4 — Claims
All numerical claims must include a source. For example, "50% faster" must be followed by "(source: internal benchmark, 2025)". Never use unsourced statistics.

5 — Call to Action
The only approved CTA is "Start your free trial". Do not use "Sign up now", "Get started", or "Learn more"."""

content = """Introducing brightpath — the most innovative and cutting-edge platform for modern teams.

Our product helps teams work 50% faster and reduces costs by 30%. It's super easy to set up and awesome to use.

Ready to disrupt your workflow? Sign up now and see the difference!"""

print("Step 0: Ingest guidelines...")
t0 = time.time()
r = httpx.post(f"{API}/api/v1/guidelines/ingest", json={"name": "SimpleTest Brand Rules", "text": gl_text}, timeout=T)
gid = r.json()["guideline_id"]
print(f"  OK: {r.json()['rule_count']} rules, id={gid[:8]}")

print("Step 1: Audit...")
audit = httpx.post(f"{API}/api/v1/audit", json={"content": content, "guideline_id": gid, "channel": "linkedin", "audience": "executive"}, timeout=T).json()
print(f"  OK: {len(audit['violations'])} violations")

print("Step 2: Adapt...")
adapt = httpx.post(f"{API}/api/v1/adapt", json={"content": content, "guideline_id": gid, "channel": "linkedin", "audience": "executive"}, timeout=T).json()
print(f"  OK: {adapt['word_count']} words, {len(adapt['change_log'])} changes")

print("Step 3: Brand DNA before...")
dna_b = httpx.post(f"{API}/api/v1/steps/brand-dna", json={"content": content, "guideline_id": gid, "channel": "linkedin", "audience": "executive", "audit_summary": ""}, timeout=T).json()

print("Step 4: Brand DNA after...")
dna_a = httpx.post(f"{API}/api/v1/steps/brand-dna", json={"content": adapt["adapted_content"], "guideline_id": gid, "channel": "linkedin", "audience": "executive", "audit_summary": audit.get("summary","")}, timeout=T).json()

print("Step 5: Reviewers...")
revs = httpx.post(f"{API}/api/v1/steps/reviewers", json={"audit_report": audit, "adaptation": adapt}, timeout=T).json()
print(f"  OK: {len(revs)} reviewers")

print("Step 6: Risk ledger...")
rl = httpx.post(f"{API}/api/v1/steps/risk-ledger", json={"audit_report": audit, "adaptation": adapt}, timeout=T).json()

elapsed = time.time() - t0

import uuid
run_id = str(uuid.uuid4())

print(f"Step 7: Saving session (elapsed={elapsed:.1f}s)...")
save = httpx.post(f"{API}/api/v1/steps/save-session", json={
    "run_id": run_id,
    "guideline_id": gid,
    "source_content": content,
    "selected_channel": "linkedin",
    "selected_audience": "executive",
    "adapted_content": adapt.get("adapted_content", ""),
    "publish_status": "not_publishable",
    "overall_risk_score": 89.0,
    "violation_count": len(audit["violations"]),
    "critical_count": audit.get("critical_count", 0),
    "change_count": len(adapt.get("change_log", [])),
    "start_time": datetime.fromtimestamp(t0, timezone.utc).isoformat(),
    "end_time": datetime.now(timezone.utc).isoformat(),
    "duration_seconds": round(elapsed, 2),
    "audit_report": audit,
    "adaptation_result": adapt,
    "risk_ledger": rl,
    "reviewer_panel": revs,
    "brand_dna_before": dna_b,
    "brand_dna_after": dna_a,
    "approval_packet": {},
}, timeout=T)
print(f"  Save result: {save.json()}")

print(f"\nDone in {elapsed:.1f}s. Run ID: {run_id[:8]}")
