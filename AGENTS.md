# Proofline AI — Agent Instructions

## Project Overview
Proofline AI is a Content Risk & Approval Copilot that transforms brand guidelines into automated compliance checks. It audits marketing content against brand rules, adapts it for target channels and audiences, and produces traceable approval packets.

## Tech Stack
- **Backend**: FastAPI (Python 3.10), SQLAlchemy ORM, Pydantic v2
- **Frontend**: Streamlit with custom CSS, Plotly for charts, httpx for API calls
- **Database**: PostgreSQL 15 (5 tables), Qdrant vector DB (rule embeddings)
- **AI**: Azure OpenAI (GPT-class chat + text-embedding-3-small), JSON mode
- **Prompts**: Jinja2 templates (.j2) + system prompts (.txt) + YAML configs
- **Testing**: pytest (58 tests, zero LLM dependency)

## Architecture
```
Frontend (Streamlit) → REST API → FastAPI Backend (11 services) → PostgreSQL / Qdrant / Azure OpenAI
```

### Key Services
- `deterministic_auditor.py` — Regex-based pre-audit (12 prohibited terms, 3 CTAs, word counts)
- `auditor.py` — LLM semantic audit with Qdrant rule retrieval
- `adapter.py` — Channel/audience content adaptation
- `brand_dna.py` — 7-dimension brand alignment scoring
- `reviewers.py` — 4 simulated expert reviewers
- `approval.py` — Pipeline orchestrator with parallel execution
- `consistency.py` — Cross-asset campaign consistency checker

## Coding Conventions
- Channel and audience are `str` (not enum) — DB-driven, dynamically configurable
- All LLM calls go through `llm.py` → `chat_json()` with JSON mode
- User message prompts use Jinja2 templates in `backend/prompts/*.j2`
- System prompts are plain text in `backend/prompts/*.txt`
- All prompts include prompt injection defense
- Constants in `backend/constants.py` — not scattered in code
- Fail-closed: malformed LLM output returns `_degraded: true`
- Session state persisted in `chat_sessions` table with JSONB blobs

## Database Tables
1. `guidelines` — Uploaded brand guideline documents (text_hash indexed)
2. `parsed_rules` — Extracted rules with FK CASCADE to guidelines
3. `chat_sessions` — Complete audit run history (21 columns, 4 indexes)
4. `channel_definitions` — Dynamic channel config (seeded from YAML)
5. `audience_definitions` — Dynamic audience config (seeded from YAML)

## Testing
- `tests/test_deterministic.py` — 31 tests: prohibited terms, CTAs, word counts, publish status, merge dedup
- `tests/test_business_logic.py` — 27 tests: risk score, hash, risk ledger, schema validation, mocked LLM
- All tests run without Azure OpenAI credentials

## Important Patterns
- Two-layer audit: deterministic violations have `source="deterministic"` and take priority in merge
- Risk score formula: `violation_penalty * 0.6 + dna_inverse * 0.4`
- Pipeline runs in 5 phases with parallel ThreadPoolExecutor
- Guideline cache: SHA-256 hash → in-memory dict → PostgreSQL fallback
- Qdrant retrieval: top-15 per paragraph, max 30 total, score ≥ 0.3 threshold
