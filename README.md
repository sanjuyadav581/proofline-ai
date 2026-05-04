# 🛡️ Proofline AI — Content Risk & Approval Copilot

> *Every content change, backed by a rule.*

Proofline AI transforms static brand guidelines into an automated compliance engine that audits, adapts, and produces traceable approval packets for enterprise marketing content.

## The Problem

Enterprise marketing teams publish 100+ content assets monthly across channels. Brand guidelines exist as static PDFs with no enforcement mechanism. Manual compliance review takes 2-4 hours per asset and produces inconsistent results. Non-compliant content creates legal exposure and brand erosion.

## The Solution

Proofline AI runs every content asset through an 8-step compliance pipeline:

1. **Guideline Ingestion** — Parse brand guidelines into structured, enforceable rules
2. **Deterministic Scan** — Instant regex checks for prohibited terms, banned CTAs, word count limits (zero LLM cost)
3. **AI Compliance Audit** — Semantic rule retrieval via Qdrant + GPT-class severity classification with rule citations
4. **Channel Adaptation** — Rewrite content for target channel format and audience tone
5. **Brand DNA Scoring** — 7-dimension brand alignment fingerprint (before vs after)
6. **Reviewer Simulation** — 4 expert personas (Brand, Legal, Channel, Revenue) with confidence scores
7. **Risk Ledger** — Cross-reference violations with adaptations (auto-fixed vs flagged)
8. **Approval Assembly** — Complete traceable approval packet with publish verdict

**Plus:** Campaign Consistency Checker — compares 2-6 assets across channels for terminology drift, conflicting claims, CTA mismatches, and tone inconsistencies.

## Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit | Review console with 8-tab results dashboard, Brand DNA radar chart, campaign consistency |
| **Backend** | FastAPI (Python 3.10) | 14 REST endpoints, 11 service modules, parallel pipeline orchestration |
| **Database** | PostgreSQL 15 | 5 tables: guidelines, parsed_rules, chat_sessions, channel_definitions, audience_definitions |
| **Vector Search** | Qdrant | Rule embeddings (1536-dim), semantic retrieval with score threshold |
| **AI** | Azure OpenAI | GPT-class model for reasoning, text-embedding-3-small for search, JSON mode |
| **Prompts** | Jinja2 + YAML | 6 system prompts, 3 user templates, 2 config files — all editable without code |

## Key Design Decisions

- **Two-layer audit**: Deterministic regex catches hard violations instantly; LLM catches semantic violations (tone, claims, audience mismatch)
- **Fail-closed**: Malformed LLM output returns `_degraded: true` — never silently reports "clean"
- **Compliance ≠ Approval**: Zero violations can still return "Conditional" if reviewers flag quality issues
- **Configurable without code**: Add channels/audiences via database INSERT; edit prompts via `.j2`/`.txt` files
- **Every fix cites a rule**: Not "this seems wrong" but "this violates RULE-9 §Prohibited Words"

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Azure OpenAI API access

### Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/proofline-ai.git
cd proofline-ai

# Start infrastructure
docker-compose up -d  # PostgreSQL, Qdrant, Redis

# Configure
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# Install dependencies
pip install -r requirements.txt

# Start backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (new terminal)
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

### Access
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
proofline-ai/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Pydantic settings from .env
│   ├── constants.py            # Tunable parameters
│   ├── database.py             # SQLAlchemy models + DB init + seeding
│   ├── models/
│   │   └── schemas.py          # Pydantic models, enums, channel/audience configs
│   ├── routers/
│   │   ├── audit.py            # POST /api/v1/audit
│   │   ├── adapt.py            # POST /api/v1/adapt
│   │   ├── approve.py          # POST /api/v1/approve (full pipeline)
│   │   ├── guidelines.py       # Guideline CRUD
│   │   ├── consistency.py      # Campaign consistency check
│   │   ├── steps.py            # Step-by-step pipeline endpoints
│   │   └── config.py           # Channel/audience definitions from DB
│   ├── services/
│   │   ├── llm.py              # Azure OpenAI wrapper + Jinja2 renderer
│   │   ├── guidelines.py       # Guideline parsing, chunking, caching
│   │   ├── auditor.py          # LLM audit with Qdrant retrieval
│   │   ├── deterministic_auditor.py  # Regex pre-audit
│   │   ├── adapter.py          # Channel/audience adaptation
│   │   ├── brand_dna.py        # 7-dimension brand scoring
│   │   ├── reviewers.py        # 4-persona reviewer simulation
│   │   ├── risk_ledger.py      # Violation-adaptation cross-reference
│   │   ├── approval.py         # Pipeline orchestrator
│   │   ├── consistency.py      # Cross-asset consistency checker
│   │   └── prompt_loader.py    # YAML config loader
│   ├── vectorstore/
│   │   └── qdrant_client.py    # Qdrant collection management + search
│   └── prompts/
│       ├── audit_system.txt    # System prompts (6 files)
│       ├── audit_user.j2       # Jinja2 user templates (3 files)
│       ├── channels.yaml       # Channel definitions
│       └── audiences.yaml      # Audience definitions
├── frontend/
│   ├── app.py                  # Streamlit application
│   └── .streamlit/config.toml  # Streamlit configuration
├── tests/
│   ├── test_deterministic.py   # 31 tests
│   └── test_business_logic.py  # 27 tests
├── docs/
│   ├── architecture.drawio     # Detailed architecture diagram
│   └── architecture-judge.drawio  # Judge-friendly architecture diagram
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Testing

```bash
# Run all 58 tests (zero LLM dependency)
pytest tests/ -v
```

## Environment Variables

Create a `.env` file with:

```env
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=your_embeddings_deployment
AZURE_OPENAI_API_VERSION=2024-12-01-preview
POSTGRES_USER=hackuser
POSTGRES_PASSWORD=your_password
```

## Built With

- **Backend**: FastAPI, SQLAlchemy, Pydantic, Jinja2
- **Frontend**: Streamlit, Plotly, httpx
- **Database**: PostgreSQL 15, Qdrant Vector DB
- **AI**: Azure OpenAI (GPT-class + text-embedding-3-small)
- **Infrastructure**: Docker Compose

## Author

**Sanju** — AI SWAT Team Hackathon

---

*AI recommends. Humans approve.*
