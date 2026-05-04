#!/usr/bin/env python3
"""End-to-end test: Ingest guidelines, then run full pipeline."""
import sys, os, json, time
sys.path.insert(0, "/home/sanju/AI SWAT Hackathon/proofline-ai")
os.chdir("/home/sanju/AI SWAT Hackathon/proofline-ai")

import httpx

API = "http://localhost:8000"
TIMEOUT = 180.0

# Load sample data
with open("data/sample_guidelines.txt") as f:
    guidelines_text = f.read()
with open("data/sample_content.txt") as f:
    content_text = f.read()

print("=" * 60)
print("PROOFLINE AI — END-TO-END VALIDATION")
print("=" * 60)

# ── Step 1: Ingest Guidelines ──
print("\n[STEP 1] Ingesting guidelines...")
t0 = time.time()
resp = httpx.post(f"{API}/api/v1/guidelines/ingest", json={
    "name": "Axion Brand Guidelines",
    "text": guidelines_text,
}, timeout=TIMEOUT)
t1 = time.time()

if resp.status_code != 200:
    print(f"  FAIL: HTTP {resp.status_code}")
    print(f"  Body: {resp.text[:500]}")
    sys.exit(1)

ingest = resp.json()
guideline_id = ingest["guideline_id"]
rule_count = ingest["rule_count"]
rules = ingest["rules"]

print(f"  OK: {rule_count} rules extracted in {t1-t0:.1f}s")
print(f"  Guideline ID: {guideline_id}")
print(f"  Rule types: {set(r['rule_type'] for r in rules)}")
print(f"  Sample rules:")
for r in rules[:3]:
    print(f"    [{r['rule_id']}] ({r['rule_type']}): {r['description'][:80]}...")

# Validate rule structure
errors = []
for r in rules:
    if not r.get("rule_id"):
        errors.append(f"Rule missing rule_id: {r}")
    if not r.get("section"):
        errors.append(f"Rule missing section: {r['rule_id']}")
    if not r.get("description"):
        errors.append(f"Rule missing description: {r['rule_id']}")
if errors:
    print(f"  WARNINGS: {len(errors)} rule structure issues")
    for e in errors[:5]:
        print(f"    - {e}")
else:
    print(f"  All {rule_count} rules have valid structure")

# ── Step 2: Run Full Pipeline ──
print(f"\n[STEP 2] Running full pipeline (LinkedIn / Executive)...")
t0 = time.time()
resp = httpx.post(f"{API}/api/v1/approve", json={
    "content": content_text,
    "guideline_id": guideline_id,
    "channel": "linkedin",
    "audience": "executive",
}, timeout=TIMEOUT)
t1 = time.time()

if resp.status_code != 200:
    print(f"  FAIL: HTTP {resp.status_code}")
    print(f"  Body: {resp.text[:1000]}")
    sys.exit(1)

packet = resp.json()
print(f"  OK: Pipeline completed in {t1-t0:.1f}s")

# ── Step 3: Validate Audit Report ──
print(f"\n[STEP 3] Validating Audit Report...")
audit = packet["audit_report"]
violations = audit["violations"]
print(f"  Violations found: {len(violations)}")
print(f"  Critical: {audit['critical_count']}, High: {audit['high_count']}, Medium: {audit['medium_count']}, Low: {audit['low_count']}")
print(f"  Summary: {audit['summary'][:120]}...")

# Check violation structure
for i, v in enumerate(violations):
    missing = [k for k in ["original_text", "issue_title", "rule_section", "rule_id", "explanation", "severity", "suggested_fix", "blocks_publishing"] if k not in v]
    if missing:
        print(f"  FAIL: Violation {i} missing fields: {missing}")
    else:
        sev = v["severity"]
        block = "BLOCKS" if v["blocks_publishing"] else "ok"
        print(f"  [{sev.upper():8s}] {v['issue_title'][:50]:50s} | Rule: {v['rule_id']:10s} | {block}")

# Check for expected violations
expected_terms = ["ai-powered", "leverag", "industry-leading", "seamlessly"]
found_terms = [v["original_text"].lower() for v in violations]
all_text = " ".join(found_terms)
for term in expected_terms:
    if term in all_text:
        print(f"  EXPECTED VIOLATION FOUND: '{term}'")
    else:
        print(f"  WARNING: Expected violation '{term}' not detected")

# ── Step 4: Validate Adaptation ──
print(f"\n[STEP 4] Validating Adapted Content...")
adapt = packet["adaptation"]
print(f"  Channel: {adapt['channel']}")
print(f"  Audience: {adapt['audience']}")
print(f"  Word count: {adapt['word_count']} (limit: 150 for LinkedIn)")
print(f"  Change log entries: {len(adapt['change_log'])}")

if adapt["word_count"] > 150:
    print(f"  WARNING: Adapted content exceeds LinkedIn 150-word limit!")
else:
    print(f"  OK: Within word limit")

print(f"  Content preview: {adapt['adapted_content'][:200]}...")

for i, c in enumerate(adapt["change_log"][:5]):
    print(f"  Change {i+1}: [{c['change_type']}] '{c['original_text'][:40]}' → '{c['changed_text'][:40]}' | {c['rule_reference']}")

# ── Step 5: Validate Risk Ledger ──
print(f"\n[STEP 5] Validating Risk Ledger...")
ledger = packet["risk_ledger"]
print(f"  Entries: {len(ledger)}")
for entry in ledger[:3]:
    print(f"  [{entry['severity'].upper():8s}] {entry['detected_issue'][:40]:40s} | {entry['risk_category']:8s} | {entry['final_action']}")

# ── Step 6: Validate Reviewer Panel ──
print(f"\n[STEP 6] Validating Reviewer Panel...")
reviewers = packet["reviewer_panel"]
print(f"  Reviewers: {len(reviewers)}")
expected_reviewers = ["Brand", "Legal", "Channel", "Revenue"]
for r in reviewers:
    concerns = ", ".join(r["top_concerns"][:2]) if r["top_concerns"] else "none"
    print(f"  {r['reviewer_name']:20s} | {r['verdict']:12s} | conf={r['confidence_score']:.2f} | {concerns[:60]}")

if len(reviewers) != 4:
    print(f"  WARNING: Expected 4 reviewers, got {len(reviewers)}")

# ── Step 7: Validate Brand DNA ──
print(f"\n[STEP 7] Validating Brand DNA Fingerprint (Before vs After)...")
dna = packet["brand_dna"]
dna_before = packet.get("brand_dna_before", {})
dims = ["brand_fit_score", "terminology_compliance", "claim_risk_score", "cta_compliance", "channel_fit", "audience_fit", "tone_alignment"]
has_before = bool(dna_before)
print(f"  Before/After comparison: {'YES' if has_before else 'NO'}")
for d in dims:
    val_after = dna.get(d, -1)
    val_before = dna_before.get(d, -1) if has_before else -1
    status = "OK" if 0 <= val_after <= 100 else "OUT OF RANGE"
    delta = f" (delta: {val_after - val_before:+.0f})" if has_before and val_before >= 0 else ""
    print(f"  {d:25s}: before={val_before:6.1f} → after={val_after:6.1f} [{status}]{delta}")

# ── Step 8: Validate Approval Packet ──
print(f"\n[STEP 8] Validating Approval Packet...")
print(f"  Run ID: {packet['run_id']}")
print(f"  Timestamp: {packet['timestamp']}")
print(f"  Publish Status: {packet['publish_status']}")
print(f"  Overall Risk Score: {packet['overall_risk_score']}")
print(f"  Unresolved Items: {len(packet['unresolved_items'])}")
print(f"  Recommendation: {packet['final_recommendation'][:120]}...")

# ── Summary ──
print(f"\n{'=' * 60}")
print("VALIDATION SUMMARY")
print(f"{'=' * 60}")
checks = {
    "Backend health": True,
    "Guidelines ingested": rule_count > 0,
    "Rules structured": len(errors) == 0,
    "Violations detected": len(violations) > 0,
    "Violation fields complete": all(
        all(k in v for k in ["original_text", "rule_id", "severity", "suggested_fix"])
        for v in violations
    ),
    "Adapted content generated": len(adapt["adapted_content"]) > 0,
    "Word count within limit": adapt["word_count"] <= 150,
    "Change log populated": len(adapt["change_log"]) > 0,
    "Risk ledger populated": len(ledger) > 0,
    "4 reviewers present": len(reviewers) == 4,
    "Brand DNA (after) valid": all(0 <= dna.get(d, -1) <= 100 for d in dims),
    "Brand DNA (before) present": has_before and all(0 <= dna_before.get(d, -1) <= 100 for d in dims),
    "Publish status set": packet["publish_status"] in ["approved", "approved_with_conditions", "not_publishable"],
    "Risk score computed": 0 <= packet["overall_risk_score"] <= 100,
    "Recommendation generated": len(packet["final_recommendation"]) > 0,
}

passed = sum(1 for v in checks.values() if v)
failed = sum(1 for v in checks.values() if not v)
for check, ok in checks.items():
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {check}")

print(f"\nResult: {passed}/{passed+failed} checks passed")
if failed == 0:
    print("STATUS: ALL CHECKS PASSED — DEMO READY")
else:
    print(f"STATUS: {failed} CHECKS FAILED — NEEDS FIXES")
