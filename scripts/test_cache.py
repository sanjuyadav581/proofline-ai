#!/usr/bin/env python3
"""Test guideline caching."""
import sys, os, time
sys.path.insert(0, "/home/sanju/AI SWAT Hackathon/proofline-ai")
os.chdir("/home/sanju/AI SWAT Hackathon/proofline-ai")
import httpx

gl = open("data/sample_guidelines.txt").read()

print("Call 1 (may be cached from postgres)...")
t0 = time.time()
r1 = httpx.post("http://localhost:8000/api/v1/guidelines/ingest", json={"name": "Test", "text": gl}, timeout=180)
t1 = time.time()
d1 = r1.json()
print(f"  Time: {t1-t0:.1f}s | Rules: {d1['rule_count']} | ID: {d1['guideline_id'][:8]}")

print("Call 2 (should hit memory cache)...")
t0 = time.time()
r2 = httpx.post("http://localhost:8000/api/v1/guidelines/ingest", json={"name": "Test", "text": gl}, timeout=180)
t1 = time.time()
d2 = r2.json()
print(f"  Time: {t1-t0:.1f}s | Rules: {d2['rule_count']} | ID: {d2['guideline_id'][:8]}")

if t1 - t0 < 2:
    print("\nCACHE WORKING - second call was instant")
else:
    print("\nCACHE NOT WORKING - second call was slow")
