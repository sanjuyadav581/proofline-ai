"""Proofline AI — centralized tunable constants.

All magic numbers and thresholds live here so they're easy to find,
tune, and (if needed later) load from .env via config.py.
"""

# ── Guideline Processing ──
CHUNK_WORD_LIMIT = 6000        # max words per chunk for LLM parsing
DEDUP_PREFIX_LENGTH = 200      # chars of description used for cross-chunk dedup

# ── Qdrant Retrieval ──
TOP_K_RULES = 15               # max rules retrieved per content segment
MAX_TOTAL_RULES = 30           # cap on unique rules sent to the audit LLM prompt

# ── Pipeline Orchestration ──
LLM_TIMEOUT_SECONDS = 120      # max wait per LLM future before timeout

# ── Risk Score Formula ──
VIOLATION_WEIGHT = 0.6         # blend weight for violation penalty
DNA_WEIGHT = 0.4               # blend weight for brand DNA inverse
CRITICAL_PENALTY = 25          # risk points per critical violation
HIGH_PENALTY = 15              # risk points per high violation
MEDIUM_PENALTY = 5             # risk points per medium violation
LOW_PENALTY = 1                # risk points per low violation
