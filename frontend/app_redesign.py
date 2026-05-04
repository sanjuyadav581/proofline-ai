"""Proofline AI — Redesigned Enterprise UI."""

import streamlit as st
import httpx
import json
import time
from pathlib import Path

# ── Page Config ──
st.set_page_config(
    page_title="Proofline AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ══════════════════════════════════════════════
#  CUSTOM CSS
# ══════════════════════════════════════════════
st.markdown("""
<style>
/* ── Global ── */
.block-container { padding-top: 1.5rem; }

/* ── Hero ── */
.hero-title {
    font-size: 2.8rem; font-weight: 800; color: #0f172a;
    margin-bottom: 0; line-height: 1.1;
}
.hero-sub {
    font-size: 1.25rem; color: #475569; font-weight: 400;
    margin-top: 0.25rem; margin-bottom: 0.15rem;
}
.hero-tagline {
    font-size: 1rem; color: #64748b; font-style: italic;
    margin-bottom: 1.5rem;
}

/* ── Cards ── */
.ch-card, .au-card {
    border: 2px solid #e2e8f0; border-radius: 12px; padding: 16px 18px;
    cursor: pointer; transition: all 0.15s ease;
    background: #ffffff; min-height: 120px;
}
.ch-card:hover, .au-card:hover { border-color: #94a3b8; }
.ch-card.selected { border-color: #2563eb; background: #eff6ff; box-shadow: 0 0 0 3px rgba(37,99,235,0.15); }
.au-card.selected { border-color: #7c3aed; background: #f5f3ff; box-shadow: 0 0 0 3px rgba(124,58,237,0.15); }
.card-title { font-size: 1rem; font-weight: 700; color: #1e293b; margin-bottom: 4px; }
.card-desc { font-size: 0.82rem; color: #64748b; line-height: 1.35; }
.card-constraint { font-size: 0.78rem; color: #2563eb; font-weight: 600; margin-top: 6px; }

/* ── Status badges ── */
.status-approved { background: #dcfce7; color: #166534; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 0.95rem; display: inline-block; }
.status-conditional { background: #fef3c7; color: #92400e; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 0.95rem; display: inline-block; }
.status-blocked { background: #fee2e2; color: #991b1b; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 0.95rem; display: inline-block; }

/* ── Metric band ── */
.metric-band {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-radius: 14px; padding: 20px 28px; margin-bottom: 24px;
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px;
}
.metric-item { text-align: center; flex: 1; min-width: 100px; }
.metric-value { font-size: 1.6rem; font-weight: 800; color: #ffffff; }
.metric-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── Violation card ── */
.viol-card {
    border-left: 4px solid #e2e8f0; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 10px; background: #f8fafc;
}
.viol-card.critical { border-left-color: #ef4444; background: #fef2f2; }
.viol-card.high { border-left-color: #f97316; background: #fff7ed; }
.viol-card.medium { border-left-color: #eab308; background: #fefce8; }
.viol-card.low { border-left-color: #22c55e; background: #f0fdf4; }

/* ── Reviewer card ── */
.rev-card {
    border-radius: 12px; padding: 18px 20px; margin-bottom: 14px;
    border: 1px solid #e2e8f0;
}
.rev-approved { background: #f0fdf4; border-left: 4px solid #22c55e; }
.rev-conditional { background: #fffbeb; border-left: 4px solid #f59e0b; }
.rev-rejected { background: #fef2f2; border-left: 4px solid #ef4444; }

/* ── Section header ── */
.section-hdr {
    font-size: 0.8rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #94a3b8; margin-bottom: 12px; margin-top: 20px;
}

/* ── Context summary ── */
.ctx-summary {
    background: linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%);
    border-radius: 12px; padding: 18px 22px; margin: 16px 0;
    border: 1px solid #c7d2fe;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #0f172a; }
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] label { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] hr { border-color: #334155; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════
def load_sample(filename: str) -> str:
    path = DATA_DIR / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


def call_api(endpoint: str, payload: dict, timeout: float = 180.0) -> dict | None:
    try:
        resp = httpx.post(f"{API_BASE}{endpoint}", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text[:300]}")
    except httpx.ConnectError:
        st.error("Cannot connect to backend. Is the FastAPI server running on port 8000?")
    except Exception as e:
        st.error(f"Error: {e}")
    return None


# ── Channel / Audience data ──
CHANNELS = {
    "linkedin": ("LinkedIn Post", "Short-form social for professional audiences", "Max 150 words · 1-2 sentence paragraphs", "CTA: 'See it in action' or 'Book a demo'"),
    "email": ("Marketing Email", "Nurture and demand-gen email body", "Max 300 words · 2-3 sentence paragraphs", "CTA: 'Schedule a demo' or 'Get started'"),
    "landing_page_body": ("Landing Page", "Conversion-focused web copy", "Max 200 words · 2-3 sentence paragraphs", "CTA: 'Book a demo today'"),
    "press_release": ("Press Release", "Media-facing announcement in AP style", "400–600 words · AP style paragraphs", "No CTA in body"),
    "event_abstract": ("Event Abstract", "Conference session description", "75–100 words · Single paragraph", "No CTA"),
}
AUDIENCES = {
    "executive": ("Executive (VP+)", "Lead with business outcomes, minimize technical detail", "Frame AI as judgment support, not automation"),
    "practitioner": ("Practitioner", "Lead with workflow improvement, include feature specifics", "Frame AI as time-saving"),
    "technical": ("Technical", "Lead with architecture and integration details", "Frame AI as data processing layer"),
}


# ══════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════
_defaults = {
    "guideline_id": None,
    "pipeline_result": None,
    "guidelines_ingested": False,
    "rule_count": 0,
    "source_content": "",
    "selected_channel": None,
    "selected_audience": None,
    "consistency_result": None,
    "page": "home",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🛡️ Proofline AI")
    st.caption("Content Risk & Approval Copilot")
    st.markdown("---")

    if st.button("🏠  Home", use_container_width=True):
        st.session_state.page = "home"
    if st.button("📊  Results Dashboard", use_container_width=True,
                 disabled=st.session_state.pipeline_result is None):
        st.session_state.page = "results"
    if st.button("🔄  Campaign Consistency", use_container_width=True,
                 disabled=not st.session_state.guidelines_ingested):
        st.session_state.page = "consistency"

    st.markdown("---")

    # Guidelines status
    if st.session_state.guidelines_ingested:
        st.success(f"✅ {st.session_state.rule_count} rules loaded")
    else:
        st.info("No guidelines ingested yet")

    if st.session_state.pipeline_result:
        r = st.session_state.pipeline_result
        status = r["publish_status"]
        badge = {"approved": "🟢 Approved", "approved_with_conditions": "🟡 Conditional", "not_publishable": "🔴 Blocked"}
        st.markdown(f"**Last run:** {badge.get(status, status)}")

    st.markdown("---")
    st.markdown("---")
    st.caption("👤 Sanju · AI SWAT Team")
    st.caption("Proofline AI v0.3 · Hackathon Demo")


# ══════════════════════════════════════════════
#  PAGE: HOME
# ══════════════════════════════════════════════
if st.session_state.page == "home":

    # ── Hero ──
    st.markdown('<p class="hero-title">🛡️ Proofline AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">Content Risk & Approval Copilot</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-tagline">Every content change, backed by a rule.</p>', unsafe_allow_html=True)
    st.markdown("Audit marketing content against brand, legal, channel, and audience rules — before it reaches customers.")

    st.markdown("---")

    # ── Channel Selection ──
    st.markdown('<div class="section-hdr">Choose Target Channel</div>', unsafe_allow_html=True)
    ch_cols = st.columns(len(CHANNELS))
    for i, (ch_key, (ch_name, ch_desc, ch_constraint, ch_cta)) in enumerate(CHANNELS.items()):
        with ch_cols[i]:
            is_sel = st.session_state.selected_channel == ch_key
            cls = "ch-card selected" if is_sel else "ch-card"
            st.markdown(
                f'<div class="{cls}">'
                f'<div class="card-title">{"✅ " if is_sel else ""}{ch_name}</div>'
                f'<div class="card-desc">{ch_desc}</div>'
                f'<div class="card-constraint">{ch_constraint}</div>'
                f'<div class="card-desc" style="margin-top:4px;font-size:0.75rem;">{ch_cta}</div>'
                f'</div>', unsafe_allow_html=True)
            if st.button(f"Select" if not is_sel else "Selected ✓", key=f"ch_{ch_key}",
                         use_container_width=True, type="primary" if is_sel else "secondary"):
                st.session_state.selected_channel = ch_key
                st.rerun()

    # ── Audience Selection ──
    st.markdown('<div class="section-hdr">Choose Target Audience</div>', unsafe_allow_html=True)
    au_cols = st.columns(len(AUDIENCES))
    for i, (au_key, (au_name, au_lead, au_ai)) in enumerate(AUDIENCES.items()):
        with au_cols[i]:
            is_sel = st.session_state.selected_audience == au_key
            cls = "au-card selected" if is_sel else "au-card"
            st.markdown(
                f'<div class="{cls}">'
                f'<div class="card-title">{"✅ " if is_sel else ""}{au_name}</div>'
                f'<div class="card-desc">{au_lead}</div>'
                f'<div class="card-constraint">{au_ai}</div>'
                f'</div>', unsafe_allow_html=True)
            if st.button(f"Select" if not is_sel else "Selected ✓", key=f"au_{au_key}",
                         use_container_width=True, type="primary" if is_sel else "secondary"):
                st.session_state.selected_audience = au_key
                st.rerun()

    # ── Pair Summary ──
    ch_key = st.session_state.selected_channel
    au_key = st.session_state.selected_audience
    if ch_key and au_key:
        ch_name, _, ch_constraint, ch_cta = CHANNELS[ch_key]
        au_name, au_lead, au_ai = AUDIENCES[au_key]
        st.markdown(
            f'<div class="ctx-summary">'
            f'<div class="section-hdr" style="margin-top:0;">Review Context</div>'
            f'<strong>{ch_name}</strong> → <strong>{au_name}</strong><br/>'
            f'<span style="color:#475569;font-size:0.9rem;">'
            f'{ch_constraint} · {ch_cta}<br/>'
            f'{au_lead}. {au_ai}.</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Content Inputs ──
    st.markdown('<div class="section-hdr">Content Inputs</div>', unsafe_allow_html=True)
    inp_col1, inp_col2 = st.columns(2)

    with inp_col1:
        st.markdown("#### 📋 Brand Guidelines")
        use_sample_gl = st.checkbox("Use sample Axion guidelines", value=True, key="use_sample_gl")
        if use_sample_gl:
            guidelines_text = load_sample("sample_guidelines.txt")
            st.text_area("Guidelines preview:", guidelines_text[:500] + "...", height=150, disabled=True, key="gl_preview")
        else:
            guidelines_text = st.text_area("Paste brand guidelines:", height=200, key="gl_custom",
                                           placeholder="Paste your brand guidelines here...")
        guidelines_name = st.text_input("Guidelines name:", value="Axion Brand Guidelines", key="gl_name")

    with inp_col2:
        st.markdown("#### 📝 Source Content")
        use_sample_ct = st.checkbox("Use sample Axion product one-pager", value=True, key="use_sample_ct")
        if use_sample_ct:
            content_text = load_sample("sample_content.txt")
            st.text_area("Content preview:", content_text[:500] + "...", height=150, disabled=True, key="ct_preview")
        else:
            content_text = st.text_area("Paste source content:", height=200, key="ct_custom",
                                        placeholder="Paste the content to audit...")

    st.markdown("---")

    # ── Run Button ──
    ready = bool(ch_key and au_key and guidelines_text and content_text)

    if not ready:
        missing = []
        if not ch_key: missing.append("target channel")
        if not au_key: missing.append("target audience")
        if not guidelines_text: missing.append("brand guidelines")
        if not content_text: missing.append("source content")
        st.warning(f"Select {', '.join(missing)} to continue.")

    run_clicked = st.button("🚀  Run Proofline", use_container_width=True, type="primary",
                             disabled=not ready, key="run_btn")

    if run_clicked:
        st.session_state.source_content = content_text

        # Auto-ingest if needed
        if not st.session_state.guidelines_ingested:
            with st.status("Preparing guidelines...", expanded=True) as status_ui:
                st.write("📋 Parsing brand guidelines into enforceable rules...")
                result = call_api("/api/v1/guidelines/ingest", {
                    "name": guidelines_name, "text": guidelines_text,
                })
                if result:
                    st.session_state.guideline_id = result["guideline_id"]
                    st.session_state.guidelines_ingested = True
                    st.session_state.rule_count = result["rule_count"]
                    st.write(f"✅ {result['rule_count']} rules extracted")
                    status_ui.update(label="Guidelines ready", state="complete")
                else:
                    status_ui.update(label="Guideline ingestion failed", state="error")
                    st.stop()

        # Run pipeline
        with st.status("Proofline is reviewing your content...", expanded=True) as status_ui:
            st.write("⚡ Running deterministic checks...")
            st.write("🔍 Performing AI compliance audit...")
            st.write("✏️ Adapting content for channel and audience...")
            st.write("📊 Building risk ledger...")
            st.write("👥 Simulating reviewer panel...")
            st.write("🧬 Scoring brand DNA (before & after)...")
            st.write("📋 Assembling approval packet...")

            t0 = time.time()
            result = call_api("/api/v1/approve", {
                "content": content_text,
                "guideline_id": st.session_state.guideline_id,
                "channel": ch_key,
                "audience": au_key,
            })
            elapsed = time.time() - t0

            if result:
                st.session_state.pipeline_result = result
                st.session_state.page = "results"
                status_ui.update(label=f"Complete in {elapsed:.0f}s", state="complete")
                st.rerun()
            else:
                status_ui.update(label="Pipeline failed", state="error")


# ══════════════════════════════════════════════
#  PAGE: RESULTS
# ══════════════════════════════════════════════
elif st.session_state.page == "results" and st.session_state.pipeline_result:
    result = st.session_state.pipeline_result
    audit = result["audit_report"]
    adaptation = result["adaptation"]
    risk_ledger = result["risk_ledger"]
    reviewers = result["reviewer_panel"]
    brand_dna = result["brand_dna"]
    brand_dna_before = result.get("brand_dna_before", brand_dna)
    status = result["publish_status"]
    risk_score = result["overall_risk_score"]

    # ── Status badge ──
    badge_map = {
        "approved": ("APPROVED", "status-approved"),
        "approved_with_conditions": ("APPROVED WITH CONDITIONS", "status-conditional"),
        "not_publishable": ("NOT PUBLISHABLE", "status-blocked"),
    }
    badge_text, badge_cls = badge_map.get(status, (status, ""))
    st.markdown(f'<span class="{badge_cls}">{badge_text}</span>', unsafe_allow_html=True)

    # ── Metric band ──
    n_approved = sum(1 for r in reviewers if r["verdict"] == "approved")
    ch_label = CHANNELS.get(adaptation["channel"], (adaptation["channel"],))[0]
    au_label = AUDIENCES.get(adaptation["audience"], (adaptation["audience"],))[0]

    st.markdown(f"""
    <div class="metric-band">
        <div class="metric-item"><div class="metric-value">{risk_score:.0f}</div><div class="metric-label">Risk Score</div></div>
        <div class="metric-item"><div class="metric-value">{len(audit['violations'])}</div><div class="metric-label">Violations</div></div>
        <div class="metric-item"><div class="metric-value">{len(adaptation['change_log'])}</div><div class="metric-label">Changes</div></div>
        <div class="metric-item"><div class="metric-value">{n_approved}/4</div><div class="metric-label">Reviewers Approved</div></div>
        <div class="metric-item"><div class="metric-value" style="font-size:1.1rem;">{ch_label}</div><div class="metric-label">Channel</div></div>
        <div class="metric-item"><div class="metric-value" style="font-size:1.1rem;">{au_label}</div><div class="metric-label">Audience</div></div>
    </div>""", unsafe_allow_html=True)

    # ── Tabs ──
    tab_ov, tab_viol, tab_adapt, tab_rl, tab_dna, tab_rev, tab_pkt = st.tabs([
        "📋 Overview", "🔍 Violations", "✏️ Adapted Content",
        "📊 Risk Ledger", "🧬 Brand DNA", "👥 Reviewers", "📥 Approval Packet",
    ])

    # ══════════ Overview ══════════
    with tab_ov:
        rec_style = {"approved": "success", "approved_with_conditions": "warning", "not_publishable": "error"}
        getattr(st, rec_style.get(status, "info"))(result["final_recommendation"])

        ov1, ov2 = st.columns(2)
        with ov1:
            st.markdown("#### Top Blocking Issues")
            blockers = [v for v in audit["violations"] if v.get("blocks_publishing")]
            if blockers:
                for b in blockers:
                    st.markdown(f'<div class="viol-card critical"><strong>{b["issue_title"]}</strong><br/>'
                                f'<code>{b["original_text"]}</code> — {b["rule_id"]}</div>', unsafe_allow_html=True)
            else:
                st.success("No blocking issues.")

        with ov2:
            st.markdown("#### Improvement Summary")
            dim_keys = ["terminology_compliance", "channel_fit", "cta_compliance", "audience_fit"]
            dim_labels = ["Terminology", "Channel Fit", "CTA", "Audience Fit"]
            for dk, dl in zip(dim_keys, dim_labels):
                bv = brand_dna_before.get(dk, 0)
                av = brand_dna.get(dk, 0)
                delta = av - bv
                if delta > 0:
                    st.markdown(f"**{dl}:** {bv:.0f} → {av:.0f} *(+{delta:.0f})*")

        if result.get("unresolved_items"):
            st.markdown("#### ⚠️ Unresolved Items")
            for item in result["unresolved_items"]:
                st.markdown(f"- {item}")

    # ══════════ Violations ══════════
    with tab_viol:
        sev_cols = st.columns(4)
        sev_cols[0].metric("🔴 Critical", audit["critical_count"])
        sev_cols[1].metric("🟠 High", audit["high_count"])
        sev_cols[2].metric("🟡 Medium", audit["medium_count"])
        sev_cols[3].metric("🟢 Low", audit["low_count"])

        if audit.get("summary"):
            st.info(f"**Summary:** {audit['summary']}")

        for v in audit["violations"]:
            sev = v["severity"]
            blocks = " · 🚫 BLOCKS PUBLISHING" if v.get("blocks_publishing") else ""
            det = " · ⚡ deterministic" if "[deterministic]" in v.get("explanation", "") else ""

            with st.expander(f"{'🔴' if sev == 'critical' else '🟠' if sev == 'high' else '🟡' if sev == 'medium' else '🟢'} **[{sev.upper()}]** {v['issue_title']}{blocks}{det}",
                             expanded=(sev in ("critical", "high"))):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Flagged text:**")
                    st.code(v["original_text"], language=None)
                    st.markdown(f"**Rule:** `{v['rule_id']}` — {v['rule_section']}")
                with c2:
                    st.markdown(f"**Why:** {v['explanation']}")
                    st.success(f"**Fix:** {v['suggested_fix']}")

    # ══════════ Adapted Content ══════════
    with tab_adapt:
        m1, m2, m3 = st.columns(3)
        m1.metric("Channel", ch_label)
        m2.metric("Audience", au_label)
        m3.metric("Word Count", adaptation["word_count"])

        orig_col, adapt_col = st.columns(2)
        with orig_col:
            st.markdown("**📄 Original**")
            st.markdown(f'<div style="background:#fef2f2;padding:16px;border-radius:8px;border-left:4px solid #ef4444;'
                        f'font-size:0.88rem;max-height:400px;overflow-y:auto;">{st.session_state.source_content}</div>',
                        unsafe_allow_html=True)
        with adapt_col:
            st.markdown("**✅ Adapted**")
            st.markdown(f'<div style="background:#f0fdf4;padding:16px;border-radius:8px;border-left:4px solid #22c55e;'
                        f'font-size:0.88rem;max-height:400px;overflow-y:auto;">{adaptation["adapted_content"]}</div>',
                        unsafe_allow_html=True)

        st.markdown("#### Change Log")
        type_icons = {"terminology": "📝", "tone": "🎭", "structure": "🏗️", "cta": "🔗", "claim": "⚖️", "formatting": "📐"}
        for i, ch in enumerate(adaptation["change_log"], 1):
            icon = type_icons.get(ch["change_type"], "🔄")
            with st.expander(f"{icon} Change {i}: **{ch['change_type'].title()}** — `{ch['rule_reference']}`"):
                lc, rc = st.columns(2)
                with lc:
                    st.markdown("**Before:**")
                    st.code(ch["original_text"], language=None)
                with rc:
                    st.markdown("**After:**")
                    st.code(ch["changed_text"], language=None)
                st.caption(f"💡 {ch['rationale']}")

    # ══════════ Risk Ledger ══════════
    with tab_rl:
        import pandas as pd
        if risk_ledger:
            rl_m = st.columns(4)
            rl_m[0].metric("Auto-Fixed", sum(1 for e in risk_ledger if e["final_action"] == "auto-fixed"))
            rl_m[1].metric("Flagged", sum(1 for e in risk_ledger if e["final_action"] == "flagged for review"))
            rl_m[2].metric("Brand", sum(1 for e in risk_ledger if e["risk_category"] == "brand"))
            rl_m[3].metric("Legal", sum(1 for e in risk_ledger if e["risk_category"] == "legal"))

            df = pd.DataFrame(risk_ledger)
            cols = ["severity", "detected_issue", "original_text", "rule_violated",
                    "risk_category", "suggested_replacement", "final_action", "reviewer_status"]
            df = df[[c for c in cols if c in df.columns]]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No risk items.")

    # ══════════ Brand DNA ══════════
    with tab_dna:
        import plotly.graph_objects as go
        cats = ["Brand Fit", "Terminology", "Claim Safety", "CTA", "Channel Fit", "Audience Fit", "Tone"]
        keys = ["brand_fit_score", "terminology_compliance", "claim_risk_score",
                "cta_compliance", "channel_fit", "audience_fit", "tone_alignment"]
        vb = [brand_dna_before.get(k, 0) for k in keys]
        va = [brand_dna.get(k, 0) for k in keys]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=vb + [vb[0]], theta=cats + [cats[0]], fill="toself",
                                       name="Original", line_color="#ef4444", fillcolor="rgba(239,68,68,0.12)"))
        fig.add_trace(go.Scatterpolar(r=va + [va[0]], theta=cats + [cats[0]], fill="toself",
                                       name="Adapted", line_color="#22c55e", fillcolor="rgba(34,197,94,0.12)"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                          showlegend=True, height=480,
                          legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center"),
                          margin=dict(t=30, b=50))
        st.plotly_chart(fig, use_container_width=True)

        score_cols = st.columns(len(cats))
        for i, (c, k) in enumerate(zip(cats, keys)):
            bv, av = brand_dna_before.get(k, 0), brand_dna.get(k, 0)
            d = av - bv
            score_cols[i].metric(c, f"{av:.0f}", delta=f"{d:+.0f}" if d else None)

    # ══════════ Reviewers ══════════
    with tab_rev:
        st.caption("Four expert personas evaluate the adapted content for publication readiness.")
        rev_cols = st.columns(2)
        for idx, rv in enumerate(reviewers):
            vd = rv["verdict"]
            cls = {"approved": "rev-approved", "conditional": "rev-conditional", "rejected": "rev-rejected"}.get(vd, "")
            icon = {"approved": "🟢", "conditional": "🟡", "rejected": "🔴"}.get(vd, "⚪")
            conf = rv.get("confidence_score", 0)

            with rev_cols[idx % 2]:
                st.markdown(
                    f'<div class="rev-card {cls}">'
                    f'<strong>{icon} {rv["reviewer_name"]}</strong>'
                    f'<span style="float:right;font-size:0.85rem;">{vd.upper()} · {conf:.0%}</span>'
                    f'<br/><em style="color:#475569;">{rv.get("reason", "")}</em></div>',
                    unsafe_allow_html=True)
                concerns = rv.get("top_concerns", [])
                if concerns:
                    for c in concerns:
                        st.markdown(f"- {c}")

    # ══════════ Approval Packet ══════════
    with tab_pkt:
        rec_style2 = {"approved": "success", "approved_with_conditions": "warning", "not_publishable": "error"}
        getattr(st, rec_style2.get(status, "info"))(result["final_recommendation"])

        st.markdown("#### Adapted Content")
        st.markdown(f'<div style="background:#f8fafc;padding:16px;border-radius:8px;border:1px solid #e2e8f0;">'
                    f'{adaptation["adapted_content"]}</div>', unsafe_allow_html=True)

        if result.get("unresolved_items"):
            st.markdown("#### ⚠️ Unresolved Items")
            for item in result["unresolved_items"]:
                st.markdown(f"- {item}")

        st.markdown("---")
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button("📥 Download JSON Packet", data=json.dumps(result, indent=2, default=str),
                               file_name=f"proofline_{result['run_id'][:8]}.json",
                               mime="application/json", use_container_width=True)
        with dl2:
            st.download_button("📄 Download Markdown Report", data=_generate_markdown_report(result),
                               file_name=f"proofline_{result['run_id'][:8]}.md",
                               mime="text/markdown", use_container_width=True)


# ══════════════════════════════════════════════
#  PAGE: CAMPAIGN CONSISTENCY
# ══════════════════════════════════════════════
elif st.session_state.page == "consistency":
    st.markdown("## 🔄 Campaign Consistency Mode")
    st.caption("Compare multiple content assets across channels for terminology, CTA, tone, and claim consistency.")

    if not st.session_state.guidelines_ingested:
        st.warning("Ingest guidelines from the Home page first.")
        st.stop()

    num_assets = st.slider("Number of assets to compare:", 2, 6, 3)
    asset_inputs = []
    cols = st.columns(min(num_assets, 3))
    ch_names = {v: CHANNELS[v][0] for v in CHANNELS}
    ch_options = list(ch_names.keys())

    for i in range(num_assets):
        with cols[i % len(cols)]:
            st.markdown(f"**Asset {i+1}**")
            label = st.text_input("Label", value=f"Asset {i+1}", key=f"ca_l_{i}")
            ch = st.selectbox("Channel", ch_options, format_func=lambda x: ch_names[x], key=f"ca_c_{i}", index=i % len(ch_options))
            ct = st.text_area("Content", height=150, key=f"ca_t_{i}", placeholder=f"Paste {ch_names[ch]} content...")
            asset_inputs.append({"label": label, "channel": ch, "content": ct})

    if st.button("🔄 Run Consistency Check", use_container_width=True, type="primary"):
        filled = [a for a in asset_inputs if a["content"].strip()]
        if len(filled) < 2:
            st.error("Provide content for at least 2 assets.")
        else:
            with st.spinner(f"Checking consistency across {len(filled)} assets..."):
                cr = call_api("/api/v1/consistency", {"assets": filled, "guideline_id": st.session_state.guideline_id})
                if cr:
                    st.session_state.consistency_result = cr

    if st.session_state.consistency_result:
        cr = st.session_state.consistency_result
        score = cr["overall_consistency_score"]
        icon = "🟢" if score >= 80 else "🟡" if score >= 50 else "🔴"
        st.markdown(f"### {icon} Consistency Score: {score:.0f}/100")
        if cr.get("summary"):
            st.info(cr["summary"])

        ct1, ct2, ct3, ct4 = st.tabs([
            f"📝 Terms ({len(cr['term_inconsistencies'])})",
            f"🔗 CTAs ({len(cr['cta_inconsistencies'])})",
            f"🎭 Tone ({len(cr['tone_drifts'])})",
            f"⚖️ Claims ({len(cr['claim_inconsistencies'])})",
        ])
        with ct1:
            for t in cr["term_inconsistencies"]:
                sev_i = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(t.get("severity", "medium"), "⚪")
                with st.expander(f"{sev_i} {', '.join(t['term_variants'])}"):
                    st.markdown(f"**Canonical:** `{t['canonical_term']}` | **Rule:** `{t['rule_reference']}`")
                    st.markdown(f"**Assets:** {', '.join(t['asset_labels'])}")
            if not cr["term_inconsistencies"]:
                st.success("No terminology inconsistencies.")

        with ct2:
            for c in cr["cta_inconsistencies"]:
                with st.expander(f"CTA variants: {', '.join(c['cta_variants'])}"):
                    st.markdown(f"**Recommended:** `{c['recommended_cta']}`")
            if not cr["cta_inconsistencies"]:
                st.success("No CTA inconsistencies.")

        with ct3:
            for td in cr["tone_drifts"]:
                sev_i = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(td.get("severity", "medium"), "⚪")
                with st.expander(f"{sev_i} {td['asset_label']}: {td['direction']}"):
                    st.markdown(td["description"])
            if not cr["tone_drifts"]:
                st.success("No tone drift detected.")

        with ct4:
            for cl in cr["claim_inconsistencies"]:
                sev_i = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(cl.get("severity", "medium"), "⚪")
                with st.expander(f"{sev_i} {cl['claim'][:60]}"):
                    st.markdown(f"**Issue:** {cl['issue']}")
                    st.markdown(f"**Assets:** {', '.join(cl['asset_labels'])}")
            if not cr["claim_inconsistencies"]:
                st.success("No claim inconsistencies.")

        if cr.get("recommendations"):
            st.markdown("#### 💡 Recommendations")
            for rec in cr["recommendations"]:
                st.markdown(f"- {rec}")


# ══════════════════════════════════════════════
#  FALLBACK
# ══════════════════════════════════════════════
elif st.session_state.page == "results" and not st.session_state.pipeline_result:
    st.info("No results yet. Go to Home and run Proofline first.")
    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()


# ══════════════════════════════════════════════
#  MARKDOWN REPORT GENERATOR
# ══════════════════════════════════════════════
def _generate_markdown_report(result: dict) -> str:
    audit = result["audit_report"]
    adaptation = result["adaptation"]
    brand_dna = result["brand_dna"]
    reviewers = result["reviewer_panel"]

    lines = [
        "# Proofline AI — Approval Report",
        f"**Run ID:** {result['run_id']}",
        f"**Timestamp:** {result['timestamp']}",
        f"**Status:** {result['publish_status'].upper().replace('_', ' ')}",
        f"**Risk Score:** {result['overall_risk_score']}/100", "",
        "---", "## Audit Summary",
        f"- Critical: {audit['critical_count']}", f"- High: {audit['high_count']}",
        f"- Medium: {audit['medium_count']}", f"- Low: {audit['low_count']}",
        f"- Total: {len(audit['violations'])}", "", audit.get("summary", ""), "",
        "## Violations",
    ]
    for v in audit["violations"]:
        block = " 🚫 BLOCKS" if v.get("blocks_publishing") else ""
        lines += [f"### [{v['severity'].upper()}] {v['issue_title']}{block}",
                  f"- **Text:** `{v['original_text']}`", f"- **Rule:** {v['rule_id']} — {v['rule_section']}",
                  f"- **Why:** {v['explanation']}", f"- **Fix:** {v['suggested_fix']}", ""]
    lines += ["---", "## Adapted Content",
              f"**Channel:** {adaptation['channel']} | **Audience:** {adaptation['audience']} | **Words:** {adaptation['word_count']}",
              "", adaptation["adapted_content"], "", "---", "## Reviewer Panel"]
    for r in reviewers:
        concerns = ", ".join(r["top_concerns"]) if r["top_concerns"] else "None"
        lines += [f"### {r['reviewer_name']}", f"- **Verdict:** {r['verdict'].upper()} ({r['confidence_score']:.0%})",
                  f"- **Reason:** {r['reason']}", f"- **Concerns:** {concerns}", ""]
    lines += ["---", "## Brand DNA (Adapted)", "| Dimension | Score |", "|-----------|-------|"]
    for k in ["brand_fit_score", "terminology_compliance", "claim_risk_score",
              "cta_compliance", "channel_fit", "audience_fit", "tone_alignment"]:
        lines.append(f"| {k.replace('_', ' ').title()} | {brand_dna.get(k, 0):.0f}/100 |")
    lines += ["", "---", "## Recommendation", result["final_recommendation"],
              "", "---", "*Generated by Proofline AI*"]
    return "\n".join(lines)
