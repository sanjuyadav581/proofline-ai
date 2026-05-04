#!/usr/bin/env python3
"""Quick test to verify the FastAPI app loads correctly."""
import sys
sys.path.insert(0, "/home/sanju/AI SWAT Hackathon/proofline-ai")

from backend.main import app

print("FastAPI app loaded OK")
print("Routes:")
for route in app.routes:
    methods = getattr(route, "methods", set())
    print(f"  {methods} {route.path}")
print("\nAll imports successful!")
