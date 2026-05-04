#!/usr/bin/env python3
"""Quick connectivity test for Azure OpenAI credentials."""
import sys, os
sys.path.insert(0, "/home/sanju/AI SWAT Hackathon/proofline-ai")
os.chdir("/home/sanju/AI SWAT Hackathon/proofline-ai")

from backend.config import get_settings
s = get_settings()
print(f"Endpoint: {s.azure_openai_endpoint}")
print(f"Deployment: {s.azure_openai_deployment}")
print(f"Embeddings: {s.azure_openai_embeddings_deployment}")
print(f"API Version: {s.azure_openai_api_version}")
print(f"Key loaded: {'YES' if s.azure_openai_api_key else 'NO'} ({len(s.azure_openai_api_key)} chars)")

print("\n--- Testing LLM call ---")
from backend.services.llm import chat_json
result = chat_json.__wrapped__ if hasattr(chat_json, '__wrapped__') else chat_json
try:
    out = chat_json("audit_system.txt", 'Return a JSON object: {"status": "ok", "message": "Proofline AI connected"}', max_completion_tokens=100)
    print(f"LLM response: {out}")
except Exception as e:
    print(f"LLM error: {e}")

print("\n--- Testing Embedding call ---")
from backend.services.llm import get_embedding
try:
    vec = get_embedding("test sentence")
    print(f"Embedding dimensions: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")
except Exception as e:
    print(f"Embedding error: {e}")

print("\nDone!")
