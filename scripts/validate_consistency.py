#!/usr/bin/env python3
"""E2E test for Campaign Consistency Mode — tests cross-channel inconsistency detection."""
import sys, os, json, time
sys.path.insert(0, "/home/sanju/AI SWAT Hackathon/proofline-ai")
os.chdir("/home/sanju/AI SWAT Hackathon/proofline-ai")

import httpx

API = "http://localhost:8000"
TIMEOUT = 180.0

# ── Use existing guideline_id or ingest fresh ──
print("=" * 60)
print("CAMPAIGN CONSISTENCY MODE — E2E TEST")
print("=" * 60)

with open("data/sample_guidelines.txt") as f:
    guidelines_text = f.read()

print("\n[STEP 1] Ingesting guidelines...")
t0 = time.time()
resp = httpx.post(f"{API}/api/v1/guidelines/ingest", json={
    "name": "Axion Brand Guidelines",
    "text": guidelines_text,
}, timeout=TIMEOUT)
assert resp.status_code == 200, f"Ingest failed: {resp.status_code}"
guideline_id = resp.json()["guideline_id"]
print(f"  OK: {resp.json()['rule_count']} rules, id={guideline_id[:8]} ({time.time()-t0:.1f}s)")

# ── Define 4 intentionally inconsistent assets ──
assets = [
    {
        "label": "LinkedIn Post",
        "channel": "linkedin",
        "content": (
            "Revenue teams lose time when decisions rely on last week's data. "
            "Axion is an AI-powered revenue intelligence platform that helps teams "
            "identify at-risk accounts before churn happens.\n\n"
            "Our customers report a 23% improvement in retention within 90 days.\n\n"
            "Ready to see it? Learn more today."
        ),
    },
    {
        "label": "Marketing Email",
        "channel": "email",
        "content": (
            "Hi there,\n\n"
            "Are your revenue teams still making decisions using outdated data? "
            "Axion is an AI-assisted revenue intelligence tool that leverages "
            "machine learning to forecast pipeline and surface expansion opportunities.\n\n"
            "Teams using Axion complete pipeline reviews in under 30 minutes — "
            "down from 3 hours. That's a game-changing improvement.\n\n"
            "The ROI is clear: a 25% improvement in retention rates within the first quarter.\n\n"
            "Schedule a demo to see what Axion can do for your team."
        ),
    },
    {
        "label": "Landing Page Body",
        "channel": "landing_page_body",
        "content": (
            "Axion is a robust, AI-driven revenue operations platform that integrates "
            "seamlessly with your existing CRM, MAP, and data warehouse. "
            "Our industry-leading solution empowers revenue teams to identify churn risks, "
            "forecast pipeline with best-in-class accuracy, and surface expansion opportunities.\n\n"
            "Customers who deploy Axion report a 23% improvement in retention rates. "
            "Axion is trusted by over 400 companies globally.\n\n"
            "Click here to get started."
        ),
    },
    {
        "label": "Event Abstract",
        "channel": "event_abstract",
        "content": (
            "This session explores how AI-assisted revenue intelligence helps enterprise "
            "teams catch at-risk accounts before churn happens. We'll demonstrate how Axion "
            "connects to existing CRM systems and uses predictive signals to surface expansion "
            "opportunities — reducing pipeline review time by 90%."
        ),
    },
]

# ── Run Consistency Check ──
print(f"\n[STEP 2] Running consistency check across {len(assets)} assets...")
t0 = time.time()
resp = httpx.post(f"{API}/api/v1/consistency", json={
    "assets": assets,
    "guideline_id": guideline_id,
}, timeout=TIMEOUT)
t1 = time.time()

if resp.status_code != 200:
    print(f"  FAIL: HTTP {resp.status_code}")
    print(f"  Body: {resp.text[:500]}")
    sys.exit(1)

cr = resp.json()
print(f"  OK: Consistency check completed in {t1-t0:.1f}s")

# ── Validate Results ──
print(f"\n[STEP 3] Validating results...")
print(f"  Overall Consistency Score: {cr['overall_consistency_score']:.0f}/100")
print(f"  Summary: {cr['summary'][:120]}...")

print(f"\n  TERM INCONSISTENCIES: {len(cr['term_inconsistencies'])}")
for t in cr["term_inconsistencies"]:
    print(f"    Variants: {t['term_variants']} → Canonical: '{t['canonical_term']}' | Rule: {t['rule_reference']}")

print(f"\n  CTA INCONSISTENCIES: {len(cr['cta_inconsistencies'])}")
for c in cr["cta_inconsistencies"]:
    print(f"    Variants: {c['cta_variants']} → Recommended: '{c['recommended_cta']}'")

print(f"\n  TONE DRIFTS: {len(cr['tone_drifts'])}")
for td in cr["tone_drifts"]:
    print(f"    {td['asset_label']}: {td['direction']} [{td.get('severity', '?')}]")

print(f"\n  CLAIM INCONSISTENCIES: {len(cr['claim_inconsistencies'])}")
for cl in cr["claim_inconsistencies"]:
    print(f"    '{cl['claim'][:50]}...' | {cl['issue'][:60]}")

print(f"\n  RECOMMENDATIONS: {len(cr.get('recommendations', []))}")
for rec in cr.get("recommendations", []):
    print(f"    - {rec}")

# ── Validation Checks ──
print(f"\n{'=' * 60}")
print("VALIDATION SUMMARY")
print(f"{'=' * 60}")

# The test data has intentional inconsistencies we expect to be caught:
# - "AI-powered" (LinkedIn) vs "AI-assisted" (Email, Event) vs "AI-driven" (Landing)
# - "Learn more" (LinkedIn, prohibited CTA) vs "Schedule a demo" vs "Click here" (Landing, prohibited)
# - "23%" (LinkedIn, Landing) vs "25%" (Email) — different numbers
# - "leverages" (Email), "seamlessly" (Landing), "robust" (Landing), "game-changing" (Email)
# - "solution" (Landing), "empowers" (Landing)

checks = {
    "API returned 200": resp.status_code == 200,
    "Score is 0-100": 0 <= cr["overall_consistency_score"] <= 100,
    "Score < 80 (inconsistencies exist)": cr["overall_consistency_score"] < 80,
    "Term inconsistencies found": len(cr["term_inconsistencies"]) > 0,
    "CTA inconsistencies found": len(cr["cta_inconsistencies"]) > 0,
    "Claim inconsistencies found": len(cr["claim_inconsistencies"]) > 0,
    "Summary generated": len(cr.get("summary", "")) > 20,
    "Recommendations provided": len(cr.get("recommendations", [])) >= 2,
}

passed = sum(1 for v in checks.values() if v)
failed = sum(1 for v in checks.values() if not v)
for check, ok in checks.items():
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {check}")

print(f"\nResult: {passed}/{passed+failed} checks passed")
if failed == 0:
    print("STATUS: CAMPAIGN CONSISTENCY MODE — ALL CHECKS PASSED")
else:
    print(f"STATUS: {failed} CHECKS FAILED")
