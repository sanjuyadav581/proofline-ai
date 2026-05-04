"""Proofline AI — 3-step guided flow UI."""

import streamlit as st
import httpx
import json
import time
from pathlib import Path

st.set_page_config(page_title="Proofline AI", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
API_BASE = "http://localhost:8000"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ── CSS ──
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }
.block-container { padding-top: 1rem !important; max-width: 1200px; }
header[data-testid="stHeader"] { height: 2.5rem; }
/* Hide Deploy button, keep three-dot menu */
.stDeployButton { display: none !important; }
[data-testid="stToolbar"] > div:first-child { display: none !important; }
/* Hide Rerun, Settings, Print, Record — keep About and Clear cache */
[data-testid="stMainMenu"] ul [data-testid="stMainMenuPopover"] li:nth-child(1),
[data-testid="stMainMenu"] ul [data-testid="stMainMenuPopover"] li:nth-child(2),
[data-testid="stMainMenu"] ul [data-testid="stMainMenuPopover"] li:nth-child(3),
[data-testid="stMainMenu"] ul [data-testid="stMainMenuPopover"] li:nth-child(4) { display: none !important; }
#MainMenu ul li:nth-child(1), #MainMenu ul li:nth-child(2),
#MainMenu ul li:nth-child(3), #MainMenu ul li:nth-child(4) { display: none !important; }
#MainMenu ul hr:first-of-type { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }

/* ── Brand Buttons ── */
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    border: none !important; color: #fff !important; font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.3) !important; transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.35) !important; transform: translateY(-1px) !important;
}
.stButton > button[data-testid="stBaseButton-secondary"] {
    border: 1.5px solid #e2e8f0 !important; background: #fff !important; color: #475569 !important;
    font-weight: 500 !important; transition: all 0.2s ease !important;
}
.stButton > button[data-testid="stBaseButton-secondary"]:hover {
    border-color: #94a3b8 !important; background: #f8fafc !important; box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
}

/* ── Hero Section ── */
.hero-wrap { margin-top: 0; margin-bottom: 0.5rem; text-align: center; padding: 12px 0 8px 0; }
.hero-title { font-size: 2.6rem; font-weight: 900; color: #0f172a; line-height: 1.15; margin-bottom: 2px; letter-spacing: -0.5px; }
.hero-sub { font-size: 1.15rem; color: #475569; margin-bottom: 2px; font-weight: 500; }
.hero-tag { font-size: 0.95rem; color: #2563eb; font-style: italic; margin-bottom: 0.6rem; font-weight: 500; }
.hero-desc { font-size: 0.92rem; color: #334155; line-height: 1.5; }

/* ── Section Headers ── */
.sec-hdr { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #94a3b8; margin: 20px 0 10px 0; }

/* ── Selection Cards ── */
.sel-card {
    border: 1.5px solid #e2e8f0; border-radius: 12px; padding: 16px 18px 10px 18px; background: #fff;
    height: 130px; display: flex; flex-direction: column; overflow: hidden;
    transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.sel-card:hover { border-color: #94a3b8; box-shadow: 0 4px 12px rgba(0,0,0,0.08); transform: translateY(-2px); }
.sel-card.sel-ch { border-color: #2563eb; background: linear-gradient(135deg, #eff6ff 0%, #e0ecff 100%); box-shadow: 0 0 0 3px rgba(37,99,235,0.1), 0 4px 12px rgba(37,99,235,0.1); }
.sel-card.sel-au { border-color: #7c3aed; background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%); box-shadow: 0 0 0 3px rgba(124,58,237,0.1), 0 4px 12px rgba(124,58,237,0.1); }
.sel-card .c-title { font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
.sel-card .c-desc { font-size: 0.8rem; color: #64748b; line-height: 1.4; flex: 1; }
.sel-card .c-tag { font-size: 0.72rem; color: #2563eb; font-style: italic; margin-top: 6px; font-weight: 500; }

/* ── Context Box ── */
.ctx-box {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1.5px solid #e2e8f0; border-radius: 14px; padding: 20px 24px; margin: 14px 0 16px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.ctx-box .sec-hdr { margin-top: 0; color: #64748b; }

/* ── Status Badges ── */
.badge-ok { background: linear-gradient(135deg, #dcfce7, #bbf7d0); color:#166534; padding:6px 16px; border-radius:20px; font-weight:700; font-size:0.88rem; display:inline-block; box-shadow: 0 1px 4px rgba(22,101,52,0.15); }
.badge-cond { background: linear-gradient(135deg, #fef3c7, #fde68a); color:#92400e; padding:6px 16px; border-radius:20px; font-weight:700; font-size:0.88rem; display:inline-block; box-shadow: 0 1px 4px rgba(146,64,14,0.15); }
.badge-block { background: linear-gradient(135deg, #fee2e2, #fecaca); color:#991b1b; padding:6px 16px; border-radius:20px; font-weight:700; font-size:0.88rem; display:inline-block; box-shadow: 0 1px 4px rgba(153,27,27,0.15); }

/* ── Metrics Band ── */
.m-band {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    border-radius: 14px; padding: 20px 24px; margin: 8px 0 20px 0;
    display: flex; align-items: center; justify-content: space-around; flex-wrap: nowrap; gap: 0;
    box-shadow: 0 4px 20px rgba(15,23,42,0.25);
}
.m-band .m-item { text-align: center; flex: 1; }
.m-band .m-val { font-size: 1.5rem; font-weight: 800; color: #fff; line-height: 1.3; }
.m-band .m-lbl { font-size: 0.68rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 500; }

/* ── Result Tabs ── */
div[data-testid="stTabs"] > div[role="tablist"] { display: flex !important; width: 100% !important; gap: 4px !important; border-bottom: none !important; padding: 0 !important; margin-bottom: 12px !important; }
div[data-testid="stTabs"] > div[role="tablist"] > button {
    flex: 1 1 0% !important; justify-content: center !important; text-align: center !important;
    padding: 10px 8px !important; min-width: 0 !important; white-space: nowrap !important;
    border: 1.5px solid #e2e8f0 !important; border-radius: 10px !important; background: #fff !important;
    color: #475569 !important; font-weight: 600 !important; font-size: 0.82rem !important; margin: 0 !important;
    transition: all 0.15s ease !important;
}
div[data-testid="stTabs"] > div[role="tablist"] > button:hover { border-color: #94a3b8 !important; background: #f8fafc !important; }
div[data-testid="stTabs"] > div[role="tablist"] > button[aria-selected="true"] {
    border-color: #2563eb !important; background: linear-gradient(135deg, #eff6ff, #e0ecff) !important;
    color: #1e40af !important; box-shadow: 0 0 0 2px rgba(37,99,235,0.1) !important;
}
div[data-testid="stTabs"] > div[role="tablist"] > button > div > p { font-size: 0.82rem !important; font-weight: 600 !important; }

/* ── Violation Cards ── */
.v-card { border-left: 4px solid #e2e8f0; border-radius: 10px; padding: 14px 18px; margin-bottom: 8px; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.04); transition: box-shadow 0.2s; }
.v-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.08); }
.v-card.crit { border-left-color: #ef4444; background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); }

/* ── Reviewer Cards ── */
.rv-card { border-radius: 12px; padding: 16px 20px; margin-bottom: 12px; border: 1px solid #e2e8f0; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.04); transition: box-shadow 0.2s; }
.rv-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.08); }
.rv-ok { background: linear-gradient(135deg, #fff 0%, #f0fdf4 100%); border-left: 4px solid #22c55e; }
.rv-cond { background: linear-gradient(135deg, #fff 0%, #fffbeb 100%); border-left: 4px solid #f59e0b; }
.rv-rej { background: linear-gradient(135deg, #fff 0%, #fef2f2 100%); border-left: 4px solid #ef4444; }

/* ── Loading Steps ── */
.prog-wrap { text-align: center; padding: 40px 0 20px 0; }
.prog-title { font-size: 1.6rem; font-weight: 800; color: #0f172a; margin-bottom: 4px; letter-spacing: -0.3px; }
.prog-ctx { font-size: 0.9rem; color: #64748b; margin-bottom: 24px; }
.step-row { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 7px 0; font-size: 0.88rem; }
.step-done { color: #16a34a; font-weight: 500; } .step-active { color: #2563eb; font-weight: 700; } .step-wait { color: #cbd5e1; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { display: flex; flex-direction: column; height: 100%; }
section[data-testid="stSidebar"] .stMarkdown p, section[data-testid="stSidebar"] .stMarkdown li, section[data-testid="stSidebar"] .stMarkdown h1, section[data-testid="stSidebar"] .stMarkdown h2, section[data-testid="stSidebar"] .stMarkdown h3, section[data-testid="stSidebar"] label { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] hr { border-color: #334155; }
/* Sidebar collapse/expand button */
button[data-testid="stSidebarCollapseButton"] { color: #e2e8f0 !important; background: rgba(255,255,255,0.1) !important; border-radius: 8px !important; }
button[data-testid="stSidebarCollapseButton"]:hover { background: rgba(255,255,255,0.2) !important; }
button[data-testid="stBaseButton-headerNoPadding"] { color: #475569 !important; }
.sidebar-footer { margin-top: auto; padding: 16px 0 8px 0; font-size: 0.7rem; color: #475569; }

/* ── Expanders ── */
.streamlit-expanderHeader { font-weight: 600 !important; font-size: 0.9rem !important; }
details[data-testid="stExpander"] { border: 1px solid #e2e8f0 !important; border-radius: 10px !important; background: #fff !important; margin-bottom: 8px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important; }
details[data-testid="stExpander"][open] { box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important; }

/* ── Input widgets ── */
.stTextArea textarea, .stTextInput input, .stSelectbox > div > div {
    border: 1.5px solid #e2e8f0 !important; border-radius: 10px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextArea textarea:focus, .stTextInput input:focus { border-color: #2563eb !important; box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important; }

/* ── Dividers ── */
hr { border-color: #f1f5f9 !important; }

/* ── Page subtitle for input page ── */
.page-subtitle {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 20px; margin-bottom: 16px;
    display: flex; align-items: center; gap: 12px;
}
.page-subtitle .ps-icon { font-size: 1.5rem; }
.page-subtitle .ps-text { font-size: 0.88rem; color: #475569; }
.page-subtitle .ps-text strong { color: #0f172a; }
</style>""", unsafe_allow_html=True)

# ── Scroll-to-top on page navigation ──
# Streamlit strips <script> from st.markdown and sandboxes components.html iframes.
# The only reliable workaround: inject CSS that auto-scrolls via anchor + focus.
# We use a unique key per page so the element changes on navigation, triggering focus.
import streamlit.components.v1 as _stc
_page_id = st.session_state.get("page", "home")
_stc.html(f"""
<div id="scroll-anchor-{_page_id}" tabindex="-1" style="height:0;overflow:hidden;"></div>
<script>
    // Approach 1: focus trick — browser scrolls to focused element
    var anchor = document.getElementById("scroll-anchor-{_page_id}");
    if (anchor) anchor.focus({{preventScroll: false}});
    
    // Approach 2: direct parent scroll (works if same-origin)
    try {{
        var main = window.parent.document.querySelector('[data-testid="stAppViewContainer"]')
                || window.parent.document.querySelector('section.main')
                || window.parent.document.querySelector('.main');
        if (main) main.scrollTop = 0;
        window.parent.scrollTo(0, 0);
    }} catch(e) {{}}
    
    // Approach 3: tab click listener for tab scrolling
    try {{
        var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
        tabs.forEach(function(t) {{
            t.addEventListener('click', function() {{
                setTimeout(function() {{
                    try {{
                        var m = window.parent.document.querySelector('[data-testid="stAppViewContainer"]')
                                || window.parent.document.querySelector('section.main');
                        if (m) m.scrollTop = 0;
                        window.parent.scrollTo(0, 0);
                    }} catch(e2) {{}}
                }}, 80);
            }});
        }});
    }} catch(e) {{}}
</script>
""", height=0)

# ── Helpers ──
def load_sample(fn):
    p = DATA_DIR / fn
    return p.read_text(encoding="utf-8") if p.exists() else ""

def call_api(ep, payload, timeout=180.0):
    try:
        r = httpx.post(f"{API_BASE}{ep}", json=payload, timeout=timeout); r.raise_for_status(); return r.json()
    except httpx.HTTPStatusError as e: st.error(f"API error: {e.response.status_code} — {e.response.text[:300]}")
    except httpx.ConnectError: st.error("Cannot connect to backend.")
    except Exception as e: st.error(f"Error: {e}")
    return None

# ── Dynamic channel/audience loading from DB via API ──
@st.cache_data(ttl=300)
def _load_channels():
    """Fetch channel definitions from backend DB. Cached 5 min."""
    try:
        r = httpx.get(f"{API_BASE}/api/v1/config/channels", timeout=5)
        r.raise_for_status()
        items = r.json()
        return {c["key"]: c for c in items}
    except Exception:
        return {}

@st.cache_data(ttl=300)
def _load_audiences():
    """Fetch audience definitions from backend DB. Cached 5 min."""
    try:
        r = httpx.get(f"{API_BASE}/api/v1/config/audiences", timeout=5)
        r.raise_for_status()
        items = r.json()
        return {a["key"]: a for a in items}
    except Exception:
        return {}

CHANNELS_DB = _load_channels()
AUDIENCES_DB = _load_audiences()

# Fallback dicts (used if API is down)
_CHANNELS_FALLBACK = {
    "linkedin": {"key": "linkedin", "label": "LinkedIn Post", "description": "Short-form social for professionals", "paragraph_style": "Max 150 words · 1-2 sent/para", "cta_note": "Use approved CTAs only", "max_words": 150, "min_words": None, "display_order": 1},
    "email": {"key": "email", "label": "Marketing Email", "description": "Nurture and demand-gen body", "paragraph_style": "Max 300 words · 2-3 sent/para", "cta_note": "Use approved CTAs only", "max_words": 300, "min_words": None, "display_order": 2},
    "blog_post": {"key": "blog_post", "label": "Blog Post", "description": "Long-form thought leadership", "paragraph_style": "300-800 words · Subheadings", "cta_note": "Use approved CTAs only", "max_words": 800, "min_words": 300, "display_order": 3},
}
_AUDIENCES_FALLBACK = {
    "executive": {"key": "executive", "label": "Executive (VP+)", "description": "Lead with business outcomes", "tone_guidance": "Minimize technical detail", "ai_framing": "Frame AI as judgment support", "display_order": 1},
    "practitioner": {"key": "practitioner", "label": "Practitioner", "description": "Lead with workflow improvement", "tone_guidance": "Include features", "ai_framing": "Frame AI as time-saving", "display_order": 2},
}

CHANNELS = CHANNELS_DB if CHANNELS_DB else _CHANNELS_FALLBACK
AUDIENCES = AUDIENCES_DB if AUDIENCES_DB else _AUDIENCES_FALLBACK

# ── MD Report generator (must be defined before pages use it) ──
def _gen_md(result):
    a=result["audit_report"];ad=result["adaptation"];bd=result["brand_dna"];rv=result["reviewer_panel"]
    l=["# Proofline AI — Approval Report",f"**Run:** {result['run_id']}",f"**Status:** {result['publish_status'].upper().replace('_',' ')}",f"**Risk:** {result['overall_risk_score']}/100","","---","## Audit",f"Critical: {a['critical_count']} · High: {a['high_count']} · Med: {a['medium_count']} · Low: {a['low_count']}","",a.get("summary",""),""]
    for v in a["violations"]:
        bk=" 🚫" if v.get("blocks_publishing") else ""; l+=[f"### [{v['severity'].upper()}] {v['issue_title']}{bk}",f"- `{v['original_text']}` — {v['rule_id']}",f"- Fix: {v['suggested_fix']}",""]
    l+=["---","## Adapted",f"Channel: {ad['channel']} · Audience: {ad['audience']} · Words: {ad['word_count']}","",ad["adapted_content"],"","---","## Reviewers"]
    for r in rv: l+=[f"### {r['reviewer_name']}",f"- {r['verdict'].upper()} ({r['confidence_score']:.0%}) — {r['reason']}",""]
    l+=["---","## Brand DNA","| Dim | Score |","|-----|-------|"]
    for k in ["brand_fit_score","terminology_compliance","claim_risk_score","cta_compliance","channel_fit","audience_fit","tone_alignment"]: l.append(f"| {k.replace('_',' ').title()} | {bd.get(k,0):.0f} |")
    l+=["","---",result["final_recommendation"],"","*Generated by Proofline AI*"]; return "\n".join(l)


def _load_rules_map(guideline_id):
    """Load rules into a dict keyed by rule_id for quick lookup."""
    if "rules_map" in st.session_state and st.session_state.get("_rules_gid") == guideline_id:
        return st.session_state.rules_map
    try:
        resp = httpx.get(f"{API_BASE}/api/v1/guidelines/{guideline_id}/rules", timeout=10.0)
        if resp.status_code == 200:
            rules = resp.json()
            rm = {r["rule_id"]: r for r in rules}
            st.session_state.rules_map = rm
            st.session_state._rules_gid = guideline_id
            return rm
    except Exception:
        pass
    return {}


def _rule_pill(rule_id, rule_section, rules_map):
    """Render a rule ID as a styled pill with hover tooltip showing the full rule."""
    rule = rules_map.get(rule_id)
    if rule:
        desc = rule.get("description", "").replace('"', '&quot;').replace("'", "&#39;")
        section = rule.get("section", rule_section).replace('"', '&quot;').replace('§', 'Section ')
        rtype = rule.get("rule_type", "").replace("_", " ").title()
        tooltip = f"{section} | {rtype} | {desc}"
        return (
            f'<span title="{tooltip}" style="display:inline-block;padding:2px 10px;background:#dbeafe;'
            f'color:#1e40af;border-radius:12px;font-size:0.8rem;font-weight:700;cursor:help;'
            f'border:1px solid #93c5fd;">{rule_id}</span>'
        )
    return f'`{rule_id}`'

# ── State ──
_d = {"guideline_id": None, "pipeline_result": None, "guidelines_ingested": False,
      "rule_count": 0, "source_content": "", "selected_channel": None, "selected_audience": None,
      "consistency_result": None, "page": "home", "active_selector": "audience"}
for k, v in _d.items():
    if k not in st.session_state: st.session_state[k] = v

# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    # Brand header
    st.markdown(
        '<div style="padding:8px 0 12px 0;border-bottom:1px solid #334155;margin-bottom:16px;">'
        '<div style="font-size:1.1rem;font-weight:800;color:#ffffff;letter-spacing:0.5px;">PROOFLINE AI</div>'
        '<div style="font-size:0.72rem;color:#e2e8f0;margin-top:2px;">Content Risk & Approval Copilot</div>'
        '</div>', unsafe_allow_html=True)

    # Navigation
    st.markdown('<div style="font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#e2e8f0;margin-bottom:8px;">Navigation</div>', unsafe_allow_html=True)
    if st.button("Home", use_container_width=True, key="nav_home"): st.session_state.page = "home"; st.rerun()
    if st.session_state.pipeline_result is not None:
        if st.button("Results", use_container_width=True, key="nav_res"): st.session_state.page = "results"; st.rerun()
    if st.session_state.guidelines_ingested:
        if st.button("Consistency", use_container_width=True, key="nav_con"): st.session_state.page = "consistency"; st.rerun()

    # Status section
    st.markdown('<div style="margin-top:20px;font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#e2e8f0;margin-bottom:8px;">Status</div>', unsafe_allow_html=True)

    if st.session_state.guidelines_ingested:
        st.markdown(f'<div style="padding:8px 12px;background:#1e3a2f;border:1px solid #22c55e;border-radius:8px;font-size:0.78rem;color:#86efac;">'
                    f'{st.session_state.rule_count} rules loaded</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:8px 12px;background:#1e293b;border:1px solid #334155;border-radius:8px;font-size:0.78rem;color:#64748b;">'
                    'No guidelines loaded</div>', unsafe_allow_html=True)

    if st.session_state.pipeline_result:
        s = st.session_state.pipeline_result["publish_status"]
        status_cfg = {
            "approved": ("Approved", "#166534", "#22c55e", "#1e3a2f"),
            "approved_with_conditions": ("Conditional", "#92400e", "#f59e0b", "#2a2517"),
            "not_publishable": ("Blocked", "#991b1b", "#ef4444", "#2a1717"),
        }
        txt, clr, bdr, bg = status_cfg.get(s, (s, "#64748b", "#475569", "#1e293b"))
        st.markdown(f'<div style="padding:8px 12px;background:{bg};border:1px solid {bdr};border-radius:8px;font-size:0.78rem;color:{clr};margin-top:8px;">'
                    f'Last audit: {txt}</div>', unsafe_allow_html=True)

    # Actions
    st.markdown('<div style="margin-top:24px;"></div>', unsafe_allow_html=True)
    if st.button("Reset Session", use_container_width=True, type="secondary", key="nav_reset"):
        for k2, v2 in _d.items(): st.session_state[k2] = v2
        st.rerun()

    # How to Use guide
    @st.dialog("How to Use Proofline AI", width="large")
    def _show_guide():
        st.markdown("""
### Getting Started

**Step 1 — Select Audience & Channel**
Choose who you're writing for (Executive, Practitioner, etc.) and the target channel (LinkedIn, Email, Blog, etc.). This tells Proofline how to calibrate tone and format.

**Step 2 — Load Brand Guidelines**
Either select a previously saved guideline or paste a new one. Proofline will parse it into enforceable rules automatically.

**Step 3 — Paste Source Content**
Paste the marketing content you want audited. This can be a draft post, email, press release, or any marketing copy.

**Step 4 — Start Audit**
Click **🚀 Start Audit** and watch the 8-step pipeline run:
1. ⚡ Deterministic scan (banned words, CTAs, word count)
2. 🔍 AI compliance audit (semantic rule matching)
3. ✏️ Channel adaptation (rewrite for format & tone)
4. 🧬 Brand DNA scoring (7-dimension alignment)
5. 👥 Reviewer simulation (4 expert personas)
6. 📋 Approval packet assembly

**Step 5 — Review Results**
Explore 8 tabs: Overview, Violations, Adapted Content, Audit Trail, Brand DNA, Reviewers, Export, and Rules.

---

### Tips
- **Rule pills** — Hover over blue rule badges (e.g. `RULE-3.1`) to see the full rule description
- **Export** — Download the full report as Markdown
- **Consistency** — Compare multiple content assets across channels in the Consistency tab
- **Reset** — Use "Reset Session" in the sidebar to start fresh
""")

    if st.button("How to Use", use_container_width=True, type="secondary", key="nav_guide"):
        _show_guide()

    # User info — pinned to sidebar bottom via flexbox
    st.markdown(
        '<div class="sidebar-footer" style="color:#e2e8f0;">'
        'Sanju · AI SWAT Team<br/>v0.6</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  PAGE 1: HOME — Select Audience & Channel
# ══════════════════════════════════════════════
if st.session_state.page == "home":
    st.markdown("""<div class="hero-wrap">
    <div class="hero-title">🛡️ Proofline AI</div>
    <div class="hero-sub">Content Risk & Approval Copilot</div>
    <div class="hero-tag">Every content change, backed by a rule.</div>
    <div class="hero-desc">Audit marketing content against brand, legal, channel, and audience rules — before it reaches customers.</div>
    </div>""", unsafe_allow_html=True)

    ch_key = st.session_state.selected_channel
    au_key = st.session_state.selected_audience
    active = st.session_state.active_selector

    # Toggle
    st.markdown('<div class="sec-hdr">Select Target</div>', unsafe_allow_html=True)
    au_label = "✅ " + AUDIENCES[au_key]["label"] if au_key and au_key in AUDIENCES else "👥 Audience"
    ch_label = "✅ " + CHANNELS[ch_key]["label"] if ch_key and ch_key in CHANNELS else "📢 Channel"
    def _sw_au(): st.session_state.active_selector = "audience"
    def _sw_ch(): st.session_state.active_selector = "channel"
    c1, c2 = st.columns(2)
    with c1: st.button(au_label, use_container_width=True, type="primary" if active == "audience" else "secondary", key="tog_au", on_click=_sw_au)
    with c2: st.button(ch_label, use_container_width=True, type="primary" if active == "channel" else "secondary", key="tog_ch", on_click=_sw_ch)

    # ── Review Context box — always visible ──
    _has_au = au_key and au_key in AUDIENCES
    _has_ch = ch_key and ch_key in CHANNELS
    if _has_au and _has_ch:
        # Both selected — full context
        cinfo = CHANNELS[ch_key]; ainfo = AUDIENCES[au_key]
        cn = cinfo["label"]; cc = cinfo.get("paragraph_style", ""); ct = cinfo.get("cta_note", "")
        an = ainfo["label"]; al = ainfo["description"]; aa = ainfo.get("ai_framing", "")
        ctx_body = (
            f'<strong>{cn}</strong> → <strong>{an}</strong><br/>'
            f'<span style="color:#475569;font-size:0.88rem;">{cc} · {ct}<br/>{al}. {aa}.</span><br/>'
            f'<span style="color:#334155;font-size:0.85rem;margin-top:6px;display:block;">'
            f'Proofline will audit for brand compliance, adapt to {cn.lower()} format, '
            f'and calibrate tone for {an.lower().split("(")[0].strip()} audiences.</span>'
        )
    elif _has_au:
        # Only audience selected
        ainfo = AUDIENCES[au_key]
        an = ainfo["label"]; al = ainfo["description"]; aa = ainfo.get("ai_framing", "")
        ctx_body = (
            f'<strong>👥 {an}</strong><br/>'
            f'<span style="color:#475569;font-size:0.88rem;">{al}. {aa}.</span><br/>'
            f'<span style="color:#94a3b8;font-size:0.85rem;margin-top:6px;display:block;">'
            f'Now select a channel to continue.</span>'
        )
    elif _has_ch:
        # Only channel selected
        cinfo = CHANNELS[ch_key]
        cn = cinfo["label"]; cc = cinfo.get("paragraph_style", ""); ct = cinfo.get("cta_note", "")
        ctx_body = (
            f'<strong>📢 {cn}</strong><br/>'
            f'<span style="color:#475569;font-size:0.88rem;">{cc} · {ct}</span><br/>'
            f'<span style="color:#94a3b8;font-size:0.85rem;margin-top:6px;display:block;">'
            f'Now select an audience to continue.</span>'
        )
    else:
        # Nothing selected
        ctx_body = (
            '<span style="color:#94a3b8;font-size:0.9rem;">'
            'Select an audience and a channel to configure your audit context.</span>'
        )
    st.markdown(f'<div class="ctx-box"><div class="sec-hdr" style="margin-top:0;">Review Context</div>{ctx_body}</div>', unsafe_allow_html=True)

    # Continue button — only when both selected
    if _has_au and _has_ch:
        if st.button("Continue to Content →", use_container_width=True, type="primary", key="next_btn"):
            st.session_state.page = "input"; st.rerun()

    # Audience cards (dynamic from DB) — click again to deselect
    if active == "audience":
        def _toggle_au(k):
            if st.session_state.selected_audience == k:
                st.session_state.selected_audience = ""  # deselect
            else:
                st.session_state.selected_audience = k
                st.session_state.active_selector = "channel"
        au_items = list(AUDIENCES.items())
        for row_start in range(0, len(au_items), 3):
            row = au_items[row_start:row_start+3]
            cols = st.columns(3)
            for i, (ak, ainfo) in enumerate(row):
                with cols[i]:
                    is_s = au_key == ak
                    an = ainfo["label"]; al = ainfo["description"]; aa = ainfo.get("ai_framing", "")
                    st.markdown(f'<div class="sel-card {"sel-au" if is_s else ""}"><div class="c-title">{"✅ " if is_s else ""}{an}</div><div class="c-desc">{al}</div><div class="c-tag">{aa}</div></div>', unsafe_allow_html=True)
                    st.button("Deselect ✕" if is_s else "Select", key=f"au_{ak}", use_container_width=True, type="primary" if is_s else "secondary", on_click=_toggle_au, args=(ak,))

    # Channel cards (dynamic from DB) — click again to deselect
    if active == "channel":
        def _toggle_ch(k):
            if st.session_state.selected_channel == k:
                st.session_state.selected_channel = ""  # deselect
            else:
                st.session_state.selected_channel = k
        items = list(CHANNELS.items())
        for row_start in range(0, len(items), 3):
            row_items = items[row_start:row_start+3]
            cols = st.columns(3)
            for i, (ck, cinfo) in enumerate(row_items):
                with cols[i]:
                    is_s = ch_key == ck
                    cn = cinfo["label"]; cd = cinfo["description"]; cc = cinfo.get("paragraph_style", ""); ct = cinfo.get("cta_note", "")
                    st.markdown(f'<div class="sel-card {"sel-ch" if is_s else ""}"><div class="c-title">{"✅ " if is_s else ""}{cn}</div><div class="c-desc">{cd}</div><div class="c-tag">{cc}</div><div class="c-desc" style="font-size:0.73rem;margin-top:2px;">{ct}</div></div>', unsafe_allow_html=True)
                    st.button("Deselect ✕" if is_s else "Select", key=f"ch_{ck}", use_container_width=True, type="primary" if is_s else "secondary", on_click=_toggle_ch, args=(ck,))

# ══════════════════════════════════════════════
#  PAGE 2: INPUT — Guidelines & Content
# ══════════════════════════════════════════════
elif st.session_state.page == "input":
    ch_key = st.session_state.selected_channel
    au_key = st.session_state.selected_audience
    if not ch_key or not au_key:
        st.warning("Please select audience and channel first.")
        if st.button("← Back to Selection"): st.session_state.page = "home"; st.rerun()
        st.stop()

    cn = CHANNELS[ch_key]["label"]; an = AUDIENCES[au_key]["label"]

    # This placeholder covers the ENTIRE page — used by the loader to replace all content
    page_slot = st.empty()

    # Track which input section is active
    if "input_section" not in st.session_state:
        st.session_state.input_section = "guidelines"

    # Render the input form inside a container within the placeholder
    with page_slot.container():
        st.markdown(f"""<div class="hero-wrap" style="margin-bottom:0.3rem;">
        <div class="hero-title" style="font-size:1.6rem;">📋 Prepare Your Content</div>
        <div class="hero-desc" style="font-size:0.88rem;">Auditing for <strong>{cn}</strong> · <strong>{an}</strong></div>
        </div>""", unsafe_allow_html=True)

        if st.button("← Change Selection", key="back_sel"): st.session_state.page = "home"; st.rerun()

        # ── Toggle buttons for Guidelines / Content ──
        _gl_done = st.session_state.guidelines_ingested
        _gl_label = "✅ Brand Guidelines" if _gl_done else "📋 Brand Guidelines"
        _ct_label = "📝 Source Content"
        def _sw_gl(): st.session_state.input_section = "guidelines"
        def _sw_ct(): st.session_state.input_section = "content"
        _t1, _t2 = st.columns(2)
        with _t1:
            st.button(_gl_label, use_container_width=True,
                       type="primary" if st.session_state.input_section == "guidelines" else "secondary",
                       key="tog_gl", on_click=_sw_gl)
        with _t2:
            st.button(_ct_label, use_container_width=True,
                       type="primary" if st.session_state.input_section == "content" else "secondary",
                       key="tog_ct", on_click=_sw_ct)

        # Initialize text vars from session state (persisted across section switches)
        guidelines_text = st.session_state.get("_gl_text", "")
        guidelines_name = st.session_state.get("_gl_name", "")
        content_text = st.session_state.get("_ct_text", "")

        # ── Guidelines section (full width) ──
        if st.session_state.input_section == "guidelines":
            st.markdown("#### 📋 Brand Guidelines")

            # Load saved guidelines
            saved_guidelines = []
            try:
                resp = httpx.get(f"{API_BASE}/api/v1/guidelines/list", timeout=5.0)
                if resp.status_code == 200:
                    saved_guidelines = resp.json()
            except Exception:
                pass

            gl_names = ["+ Paste New Guideline"] + [sg["name"] for sg in saved_guidelines]
            gl_choice = st.selectbox("Select or create guideline:", gl_names, key="gl_pick",
                                      index=1 if saved_guidelines else 0)

            if gl_choice == "+ Paste New Guideline":
                st.session_state.guidelines_ingested = False
                st.session_state.guideline_id = None
                st.session_state.rule_count = 0
                guidelines_name = st.text_input("Guideline name:", value="", key="gl_n", placeholder="Enter a name for your guideline…")

                # Edit / Preview toggle
                if "gl_show_preview" not in st.session_state:
                    st.session_state.gl_show_preview = False
                _ep1, _ep2 = st.columns(2)
                with _ep1:
                    if st.button("✏️ Edit", use_container_width=True, type="primary" if not st.session_state.gl_show_preview else "secondary", key="gl_edit_btn"):
                        st.session_state.gl_show_preview = False; st.rerun()
                with _ep2:
                    if st.button("👁 Preview", use_container_width=True, type="primary" if st.session_state.gl_show_preview else "secondary", key="gl_prev_btn"):
                        st.session_state.gl_show_preview = True; st.rerun()

                if st.session_state.gl_show_preview:
                    raw = st.session_state.get("gl_c", "")
                    if raw:
                        import html as _html
                        _safe = _html.escape(raw)
                        st.markdown(f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 20px;height:350px;overflow-y:auto;font-size:0.88rem;line-height:1.6;white-space:pre-wrap;">{_safe}</div>', unsafe_allow_html=True)
                    else:
                        st.info("Nothing to preview yet. Switch to Edit and paste your guidelines.")
                    guidelines_text = raw
                else:
                    guidelines_text = st.text_area("Paste guidelines:", height=350, key="gl_c", placeholder="Paste brand guidelines here…")
            else:
                sg = next((g for g in saved_guidelines if g["name"] == gl_choice), None)
                if sg:
                    try:
                        resp = httpx.get(f"{API_BASE}/api/v1/guidelines/{sg['id']}/text", timeout=10.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            guidelines_text = data["text"]
                            guidelines_name = data["name"]
                            st.session_state.guideline_id = sg["id"]
                            st.session_state.guidelines_ingested = True
                            # Store original for edit-detection
                            if "_gl_original_text" not in st.session_state:
                                st.session_state["_gl_original_text"] = data["text"]
                            if st.session_state.rule_count == 0:
                                try:
                                    rc = httpx.post(f"{API_BASE}/api/v1/guidelines/ingest",
                                                    json={"name": data["name"], "text": data["text"]}, timeout=10.0)
                                    if rc.status_code == 200:
                                        st.session_state.rule_count = rc.json().get("rule_count", 0)
                                except Exception:
                                    pass
                        else:
                            guidelines_text = ""; guidelines_name = gl_choice
                    except Exception:
                        guidelines_text = ""; guidelines_name = gl_choice

                    # Editable view with preview toggle
                    if "gl_edit_existing" not in st.session_state:
                        st.session_state.gl_edit_existing = False

                    _ev1, _ev2 = st.columns(2)
                    with _ev1:
                        if st.button("👁 Preview", use_container_width=True, type="primary" if not st.session_state.gl_edit_existing else "secondary", key="gl_ex_prev"):
                            st.session_state.gl_edit_existing = False; st.rerun()
                    with _ev2:
                        if st.button("✏️ Edit", use_container_width=True, type="primary" if st.session_state.gl_edit_existing else "secondary", key="gl_ex_edit"):
                            st.session_state.gl_edit_existing = True; st.rerun()

                    if st.session_state.gl_edit_existing:
                        # Editable text area — Ctrl+Enter saves; edits persist in session state
                        _edit_val = st.session_state.get("_gl_text", guidelines_text) or guidelines_text
                        edited_text = st.text_area("Edit guidelines:", value=_edit_val, height=400, key="gl_edit_ta")
                        guidelines_text = edited_text
                        if edited_text != st.session_state.get("_gl_original_text", ""):
                            st.info("✏️ Guidelines edited. Changes will be re-parsed when you start the audit.")
                            st.session_state.guidelines_ingested = False
                    else:
                        # Preview — shows latest text including any edits
                        _preview_text = st.session_state.get("_gl_text", guidelines_text) or guidelines_text
                        import html as _html
                        _safe = _html.escape(_preview_text)
                        st.markdown(
                            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;'
                            f'padding:16px 20px;height:400px;overflow-y:auto;font-size:0.88rem;line-height:1.6;white-space:pre-wrap;">{_safe}</div>',
                            unsafe_allow_html=True)
                        guidelines_text = _preview_text

                else:
                    guidelines_text = ""; guidelines_name = gl_choice

            # Persist to session state so content section can read them
            st.session_state["_gl_text"] = guidelines_text
            st.session_state["_gl_name"] = guidelines_name

        # ── Content section (full width) ──
        if st.session_state.input_section == "content":
            st.markdown("#### 📝 Source Content")
            use_ct = st.checkbox("Use sample Axion one-pager", value=True, key="use_ct")
            content_text = load_sample("sample_content.txt") if use_ct else ""
            if use_ct:
                st.text_area("Preview:", content_text[:500] + "…", height=300, disabled=True, key="ct_p")
            else:
                content_text = st.text_area("Paste content:", height=350, key="ct_c", placeholder="Paste content to audit…")
            # Persist content to session state
            if content_text:
                st.session_state["_ct_text"] = content_text

        # ── Action buttons ──
        ready = bool(guidelines_text and content_text)
        if st.session_state.input_section == "guidelines" and guidelines_text:
            if st.button("Next: Source Content →", use_container_width=True, type="primary", key="gl_next"):
                st.session_state.input_section = "content"; st.rerun()
        if not ready and st.session_state.input_section == "content":
            if not guidelines_text:
                st.warning("Please set up brand guidelines first. Switch to the Brand Guidelines tab.")
            elif not content_text:
                st.warning("Paste or select source content to continue.")
        run_clicked = st.button("🚀 Start Audit", use_container_width=True, type="primary", disabled=not ready, key="run_btn")

    # ── If Run clicked: replace entire page with loader ──
    if run_clicked:
        st.session_state.source_content = content_text

        STEPS = [
            ("🛡️", "Preparing Guidelines", "Parsing brand rules into enforceable checks", "system"),
            ("⚡", "Deterministic Scan", "Prohibited words, CTAs & length limits", "deterministic"),
            ("🔍", "AI Compliance Audit", "Semantic analysis against brand rules", "ai"),
            ("✏️", "Channel Adaptation", "Rewriting for format & audience tone", "ai"),
            ("🧬", "Brand DNA · Original", "Scoring source content alignment", "ai"),
            ("🧬", "Brand DNA · Adapted", "Scoring adapted content alignment", "ai"),
            ("👥", "Reviewer Simulation", "4 expert personas evaluating content", "ai"),
            ("📋", "Approval Assembly", "Risk ledger & final recommendation", "system"),
        ]

        def render_loader(cur, total=len(STEPS), done=False, elapsed=0):
            pct = 100 if done else int(cur / total * 100)
            cur_icon, cur_name, cur_desc, cur_type = STEPS[min(cur, total - 1)]

            accent = "#16a34a" if done else "#2563eb"
            accent_light = "#dcfce7" if done else "#dbeafe"
            accent_bg = "#f0fdf4" if done else "#eff6ff"

            type_label = {"deterministic": "Deterministic", "ai": "AI-Powered", "system": "System"}.get(cur_type, "")
            type_color = {"deterministic": "#7c3aed", "ai": "#2563eb", "system": "#64748b"}.get(cur_type, "#64748b")

            # Micro-copy for completed steps
            step_results = {
                0: f"{st.session_state.rule_count} rules parsed" if st.session_state.rule_count else "rules parsed",
                1: "hard rules checked",
                2: "semantic analysis done",
                3: "content rewritten",
                4: "original scored",
                5: "adapted scored",
                6: "4 verdicts ready",
                7: "packet assembled",
            }

            if done:
                badge = (f'<div style="padding:12px 28px;background:#dcfce7;border:1px solid #bbf7d0;'
                         f'border-radius:12px;font-weight:700;font-size:1rem;color:#166534;margin-bottom:20px;'
                         f'text-align:center;letter-spacing:0.5px;">AUDIT COMPLETE · {elapsed:.0f}s</div>')
                step_display = ''
            else:
                badge = (f'<div style="padding:12px 28px;background:#dbeafe;border:1px solid #93c5fd;'
                         f'border-radius:12px;font-weight:700;font-size:1rem;color:#1e40af;margin-bottom:20px;'
                         f'text-align:center;letter-spacing:0.5px;">ANALYZING CONTENT</div>')
                step_display = (
                    f'<div style="margin:20px 0 24px 0;">'
                    f'<div style="display:inline-flex;align-items:center;gap:10px;padding:14px 28px;'
                    f'background:{accent_bg};border:1px solid {accent_light};border-radius:12px;">'
                    f'<span style="font-size:1.4rem;">{cur_icon}</span>'
                    f'<div style="text-align:left;">'
                    f'<div style="font-size:0.95rem;font-weight:700;color:#1e293b;">{cur_name}'
                    f'<span style="margin-left:8px;font-size:0.65rem;padding:2px 8px;background:{type_color};color:#fff;border-radius:10px;font-weight:600;">{type_label}</span></div>'
                    f'<div style="font-size:0.78rem;color:#64748b;">{cur_desc}</div>'
                    f'</div></div></div>'
                )

            r2 = 70; circ = 2 * 3.14159 * r2; offset = circ * (1 - pct / 100)
            ring = (
                f'<svg width="180" height="180" viewBox="0 0 180 180" style="display:block;margin:0 auto;">'
                f'<circle cx="90" cy="90" r="{r2}" fill="none" stroke="#f1f5f9" stroke-width="8"/>'
                f'<circle cx="90" cy="90" r="{r2}" fill="none" stroke="{accent}" stroke-width="8"'
                f' stroke-dasharray="{circ}" stroke-dashoffset="{offset}"'
                f' stroke-linecap="round" transform="rotate(-90 90 90)"/>'
                f'<text x="90" y="82" text-anchor="middle" font-size="38" font-weight="900" fill="#1e293b">{pct}</text>'
                f'<text x="90" y="105" text-anchor="middle" font-size="13" font-weight="600" fill="#94a3b8">PERCENT</text>'
                f'</svg>'
            )

            pills_html = '<div style="max-width:650px;margin:0 auto;">'
            for row_start in [0, 4]:
                pills_html += '<div style="display:flex;gap:6px;margin-bottom:6px;">'
                for j in range(row_start, min(row_start + 4, total)):
                    ic, nm, _, stype = STEPS[j]
                    st_lbl = {"deterministic":"DET","ai":"AI","system":"SYS"}.get(stype,"")
                    st_clr = {"deterministic":"#7c3aed","ai":"#2563eb","system":"#64748b"}.get(stype,"#64748b")
                    if j < cur or done:
                        pill_bg = "#f0fdf4"; pill_border = "#bbf7d0"; pill_icon = "✅"; pill_txt = "#166534"
                        micro = step_results.get(j, "done")
                    elif j == cur and not done:
                        pill_bg = "#eff6ff"; pill_border = "#93c5fd"; pill_icon = ic; pill_txt = "#1e40af"
                        micro = ""
                    else:
                        pill_bg = "#f8fafc"; pill_border = "#e2e8f0"; pill_icon = "·"; pill_txt = "#94a3b8"
                        micro = ""
                    micro_html = f'<div style="font-size:0.48rem;color:#16a34a;margin-top:1px;">{micro}</div>' if micro else ""
                    pills_html += (
                        f'<div style="flex:1;padding:8px 4px;background:{pill_bg};border:1.5px solid {pill_border};'
                        f'border-radius:10px;text-align:center;">'
                        f'<div style="font-size:1rem;">{pill_icon}</div>'
                        f'<div style="font-size:0.58rem;font-weight:600;color:{pill_txt};margin-top:2px;'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{nm}</div>'
                        f'<div style="font-size:0.5rem;color:{st_clr};font-weight:700;margin-top:1px;">{st_lbl}</div>'
                        f'{micro_html}'
                        f'</div>'
                    )
                pills_html += '</div>'
            pills_html += '</div>'

            # Thin progress bar below ring
            bar = (
                f'<div style="width:220px;height:4px;background:#f1f5f9;border-radius:2px;margin:12px auto 0 auto;">'
                f'<div style="width:{pct}%;height:100%;background:{accent};border-radius:2px;"></div>'
                f'</div>'
            )

            # Assemble
            page_slot.markdown(
                f'<div style="text-align:center;padding:30px 20px;min-height:75vh;">'
                # Badge
                f'{badge}'
                # Title
                f'<div style="font-size:1.5rem;font-weight:800;color:#0f172a;margin-bottom:4px;">Proofline AI</div>'
                f'<div style="font-size:0.88rem;color:#64748b;margin-bottom:20px;">{cn} · {an}</div>'
                # Ring
                f'{ring}{bar}'
                # Current step card
                f'{step_display}'
                # Step pills
                f'{pills_html}'
                f'</div>', unsafe_allow_html=True)

        failed = False; t0 = time.time()

        # Step 0: Guidelines
        render_loader(0)
        if not st.session_state.guidelines_ingested:
            res = call_api("/api/v1/guidelines/ingest", {"name": guidelines_name, "text": guidelines_text})
            if res:
                st.session_state.guideline_id = res["guideline_id"]
                st.session_state.guidelines_ingested = True; st.session_state.rule_count = res["rule_count"]
            else: failed = True
        gid = st.session_state.guideline_id

        # Step 1: Deterministic
        if not failed: render_loader(1)

        # Step 2: LLM audit
        audit_result = None
        if not failed:
            render_loader(2)
            audit_result = call_api("/api/v1/audit", {"content": content_text, "guideline_id": gid, "channel": ch_key, "audience": au_key})
            if not audit_result: failed = True

        # Step 3: Adapt
        adapt_result = None
        if not failed:
            render_loader(3)
            adapt_result = call_api("/api/v1/adapt", {"content": content_text, "guideline_id": gid, "channel": ch_key, "audience": au_key})
            if not adapt_result: failed = True

        # Step 4: Brand DNA original
        dna_before = None
        if not failed:
            render_loader(4)
            dna_before = call_api("/api/v1/steps/brand-dna", {"content": content_text, "guideline_id": gid, "channel": ch_key, "audience": au_key, "audit_summary": "Scoring original content."})
            if not dna_before: failed = True

        # Step 5: Brand DNA adapted
        dna_after = None
        if not failed:
            render_loader(5)
            dna_after = call_api("/api/v1/steps/brand-dna", {"content": adapt_result["adapted_content"], "guideline_id": gid, "channel": ch_key, "audience": au_key, "audit_summary": audit_result.get("summary", "")})
            if not dna_after: failed = True

        # Step 6: Reviewers
        reviewers = None
        if not failed:
            render_loader(6)
            reviewers = call_api("/api/v1/steps/reviewers", {"audit_report": audit_result, "adaptation": adapt_result})
            if not reviewers: failed = True

        # Step 7: Risk ledger + packet
        if not failed:
            render_loader(7)
            rl_result = call_api("/api/v1/steps/risk-ledger", {"audit_report": audit_result, "adaptation": adapt_result})
            risk_ledger = rl_result if rl_result else []
            critical = audit_result.get("critical_count", 0); high = audit_result.get("high_count", 0)
            has_rej = any(r.get("verdict") == "rejected" for r in reviewers)
            has_cond = any(r.get("verdict") == "conditional" for r in reviewers)
            if critical > 0 or has_rej: pub_status = "not_publishable"
            elif has_cond or high > 0: pub_status = "approved_with_conditions"
            else: pub_status = "approved"
            vp = critical*25 + high*15 + audit_result.get("medium_count",0)*5 + audit_result.get("low_count",0)
            dv = [dna_after.get(k,50) for k in ["brand_fit_score","terminology_compliance","claim_risk_score","cta_compliance","channel_fit","audience_fit","tone_alignment"]]
            risk_score = min(100, vp*0.6 + max(0, 100 - sum(dv)/len(dv))*0.4)
            unresolved = [f"{e['detected_issue']}: {e['original_text']}" for e in risk_ledger if e.get("final_action") == "flagged for review"]
            if pub_status == "approved": rec = "Content is compliant and ready for publication."
            elif pub_status == "approved_with_conditions": rec = f"Conditionally approved. {len(unresolved)} items need review."
            else: rec = f"NOT publishable. {critical} critical violations must be resolved."
            import uuid as _uuid; from datetime import datetime as _dt, timezone as _tz
            elapsed = time.time() - t0
            packet = {"run_id": str(_uuid.uuid4()), "timestamp": _dt.now(_tz.utc).isoformat(),
                       "publish_status": pub_status, "overall_risk_score": round(risk_score, 1),
                       "audit_report": audit_result, "brand_dna_before": dna_before, "brand_dna": dna_after,
                       "adaptation": adapt_result, "risk_ledger": risk_ledger, "reviewer_panel": reviewers,
                       "unresolved_items": unresolved, "final_recommendation": rec}
            render_loader(7, done=True, elapsed=elapsed)

            # Save to database
            try:
                call_api("/api/v1/steps/save-session", {
                    "run_id": packet["run_id"],
                    "guideline_id": gid,
                    "source_content": content_text,
                    "selected_channel": ch_key,
                    "selected_audience": au_key,
                    "adapted_content": adapt_result.get("adapted_content", ""),
                    "publish_status": pub_status,
                    "overall_risk_score": round(risk_score, 1),
                    "violation_count": len(audit_result.get("violations", [])),
                    "critical_count": critical,
                    "change_count": len(adapt_result.get("change_log", [])),
                    "start_time": _dt.fromtimestamp(t0, _tz.utc).isoformat(),
                    "end_time": _dt.now(_tz.utc).isoformat(),
                    "duration_seconds": round(elapsed, 2),
                    "audit_report": audit_result,
                    "adaptation_result": adapt_result,
                    "risk_ledger": risk_ledger,
                    "reviewer_panel": reviewers,
                    "brand_dna_before": dna_before,
                    "brand_dna_after": dna_after,
                    "approval_packet": packet,
                })
            except Exception:
                pass  # non-blocking save

            st.session_state.pipeline_result = packet; st.session_state.page = "results"
            time.sleep(0.6); st.rerun()

        if failed:
            page_slot.error("Pipeline failed. Please try again.")
            if st.button("← Back"): st.session_state.page = "input"; st.rerun()
        st.stop()

# ══════════════════════════════════════════════
#  PAGE 3b: RESULTS
# ══════════════════════════════════════════════
elif st.session_state.page == "results" and st.session_state.pipeline_result:
    result = st.session_state.pipeline_result
    audit = result["audit_report"]; adaptation = result["adaptation"]
    risk_ledger = result["risk_ledger"]; reviewers = result["reviewer_panel"]
    brand_dna = result["brand_dna"]; brand_dna_before = result.get("brand_dna_before", brand_dna)
    status = result["publish_status"]; risk_score = result["overall_risk_score"]

    bm = {"approved":("Approved","badge-ok"),"approved_with_conditions":("Conditional","badge-cond"),"not_publishable":("Blocked","badge-block")}
    bt, bc = bm.get(status,(status,""))
    st.markdown(f'<span class="{bc}">{bt}</span>', unsafe_allow_html=True)

    na = sum(1 for r in reviewers if r["verdict"]=="approved")
    chl = CHANNELS.get(adaptation["channel"],{"label":adaptation["channel"]})["label"]
    aul = AUDIENCES.get(adaptation["audience"],{"label":adaptation["audience"]})["label"]
    st.markdown(f'<div class="m-band"><div class="m-item"><div class="m-val">{risk_score:.0f}<span style="font-size:0.7rem;color:#64748b;">/100</span></div><div class="m-lbl">Risk Score</div></div><div class="m-item"><div class="m-val">{len(audit["violations"])}</div><div class="m-lbl">Violations</div></div><div class="m-item"><div class="m-val">{len(adaptation["change_log"])}</div><div class="m-lbl">Changes</div></div><div class="m-item"><div class="m-val">{na}/4</div><div class="m-lbl">Approved</div></div><div class="m-item"><div class="m-val" style="font-size:1rem;">{chl}</div><div class="m-lbl">Channel</div></div><div class="m-item"><div class="m-val" style="font-size:1rem;">{aul}</div><div class="m-lbl">Audience</div></div></div>', unsafe_allow_html=True)

    # Preload rules for tooltip display
    gid = st.session_state.get("guideline_id")
    rules_map = _load_rules_map(gid) if gid else {}

    t_ov,t_vi,t_ad,t_rl,t_dn,t_rv,t_pk,t_ru = st.tabs(["📋 Overview","🔍 Violations","✏️ Adapted","📊 Audit Trail","🧬 Brand DNA","👥 Reviewers","📥 Export","📖 Rules"])

    # ══════════ Overview ══════════
    with t_ov:
        rs = {"approved":"success","approved_with_conditions":"warning","not_publishable":"error"}
        getattr(st,rs.get(status,"info"))(result["final_recommendation"])

        box_style = "background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:20px;height:100%;"
        ov1, ov2, ov3 = st.columns(3)

        with ov1:
            blk = [v for v in audit["violations"] if v.get("blocks_publishing")]
            cards_html = ""
            if blk:
                for b in blk:
                    pill = _rule_pill(b["rule_id"], b.get("rule_section",""), rules_map)
                    cards_html += f'<div class="v-card crit"><strong>{b["issue_title"]}</strong><br/><code>{b["original_text"]}</code> — {pill}</div>'
            else:
                cards_html = '<div style="color:#16a34a;font-weight:600;">✅ No blocking issues</div>'
            st.markdown(f'<div style="{box_style}"><div style="font-size:1rem;font-weight:700;color:#1e293b;margin-bottom:12px;">🚫 Blocking Issues</div>{cards_html}</div>', unsafe_allow_html=True)

        with ov2:
            bars_html = ""
            for dk,dl in [("terminology_compliance","Terminology"),("channel_fit","Channel Fit"),("cta_compliance","CTA"),("audience_fit","Audience"),("tone_alignment","Tone")]:
                bv,av = brand_dna_before.get(dk,0),brand_dna.get(dk,0); d=av-bv
                if d > 0:
                    # Color based on improvement trajectory: green if after≥60 or big delta, amber if modest, red if still low
                    if av >= 70 or d >= 40:
                        bar_c = "#22c55e"
                    elif av >= 40 or d >= 15:
                        bar_c = "#f59e0b"
                    else:
                        bar_c = "#ef4444"
                    bars_html += (f'<div style="margin-bottom:10px;"><div style="display:flex;justify-content:space-between;font-size:0.82rem;">'
                                  f'<span style="font-weight:600;color:#1e293b;">{dl}</span><span style="color:#64748b;">{bv:.0f} → {av:.0f} (+{d:.0f})</span></div>'
                                  f'<div style="width:100%;height:6px;background:#e2e8f0;border-radius:3px;margin-top:4px;">'
                                  f'<div style="width:{av}%;height:100%;background:{bar_c};border-radius:3px;"></div></div></div>')
            st.markdown(f'<div style="{box_style}"><div style="font-size:1rem;font-weight:700;color:#1e293b;margin-bottom:12px;">📈 Brand Improvement</div>{bars_html}</div>', unsafe_allow_html=True)

        with ov3:
            rev_html = ""
            for rv in reviewers:
                vd = rv["verdict"]
                ic = {"approved":"🟢","conditional":"🟡","rejected":"🔴"}.get(vd,"⚪")
                rev_html += f'<div style="padding:4px 0;font-size:0.88rem;">{ic} <strong>{rv["reviewer_name"]}</strong> — {vd.title()}</div>'
            st.markdown(f'<div style="{box_style}"><div style="font-size:1rem;font-weight:700;color:#1e293b;margin-bottom:12px;">👥 Reviewer Summary</div>{rev_html}</div>', unsafe_allow_html=True)

        # Next Steps — full width below
        st.markdown("")
        if status == "not_publishable":
            next_text = "Fix all <strong>critical</strong> blocking issues → Re-run Proofline to validate → Get reviewer approval"
        elif status == "approved_with_conditions":
            next_text = "Address <strong>high</strong> severity items → Review conditional feedback → Submit for final approval"
        else:
            next_text = "Content is ready ✅ → Download approval packet → Publish with confidence"
        st.markdown(f'<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 20px;font-size:0.88rem;">'
                    f'<strong>📋 Next Steps:</strong> {next_text}</div>', unsafe_allow_html=True)

        if result.get("unresolved_items"):
            st.markdown("")
            with st.expander(f"⚠️ {len(result['unresolved_items'])} Items Requiring Human Review"):
                for item in result["unresolved_items"]: st.markdown(f"- {item}")

    with t_vi:
        sc=st.columns(4); sc[0].metric("🔴 Critical",audit["critical_count"]); sc[1].metric("🟠 High",audit["high_count"]); sc[2].metric("🟡 Medium",audit["medium_count"]); sc[3].metric("🟢 Low",audit["low_count"])
        if audit.get("summary"): st.info(audit["summary"])
        for v in audit["violations"]:
            sv=v["severity"]; blk=" · 🚫" if v.get("blocks_publishing") else ""; det=" · ⚡det" if "[deterministic]" in v.get("explanation","") else ""
            ic={"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}.get(sv,"⚪")
            with st.expander(f"{ic} **[{sv.upper()}]** {v['issue_title']}{blk}{det}", expanded=sv in ("critical","high")):
                c1,c2=st.columns(2)
                with c1:
                    st.markdown("**Flagged:**"); st.code(v["original_text"],language=None)
                    pill = _rule_pill(v["rule_id"], v["rule_section"], rules_map)
                    section_clean = v['rule_section'].replace('§', 'Section ')
                    st.markdown(f"**Rule:** {pill} — {section_clean}", unsafe_allow_html=True)
                with c2: st.markdown(f"**Why:** {v['explanation']}"); st.success(f"**Fix:** {v['suggested_fix']}")

    with t_ad:
        m1,m2,m3=st.columns(3); m1.metric("Channel",chl); m2.metric("Audience",aul); m3.metric("Words",adaptation["word_count"])
        oc,ac=st.columns(2)
        with oc: st.markdown("**📄 Original**"); st.markdown(f'<div style="background:#fef2f2;padding:14px;border-radius:8px;border-left:4px solid #ef4444;font-size:0.85rem;max-height:380px;overflow-y:auto;">{st.session_state.source_content}</div>',unsafe_allow_html=True)
        with ac: st.markdown("**✅ Adapted**"); st.markdown(f'<div style="background:#f0fdf4;padding:14px;border-radius:8px;border-left:4px solid #22c55e;font-size:0.85rem;max-height:380px;overflow-y:auto;">{adaptation["adapted_content"]}</div>',unsafe_allow_html=True)
        st.markdown("#### Change Log")
        tic={"terminology":"📝","tone":"🎭","structure":"🏗️","cta":"🔗","claim":"⚖️","formatting":"📐"}
        for i,ch in enumerate(adaptation["change_log"],1):
            # Extract first rule ID from rule_reference for pill display
            ref = ch.get("rule_reference","")
            ref_parts = [r.strip() for r in ref.replace(","," ").split() if r.strip().startswith("RULE")]
            pills = " ".join(_rule_pill(rp, "", rules_map) for rp in ref_parts) if ref_parts else f"<code>{ref}</code>"
            with st.expander(f"{tic.get(ch['change_type'],'🔄')} Change {i}: **{ch['change_type'].title()}**"):
                st.markdown(f"**Rules:** {pills}", unsafe_allow_html=True)
                l,r=st.columns(2)
                with l:
                    st.markdown("**Before:**")
                    st.markdown(f'<div style="background:#fef2f2;padding:10px 12px;border-radius:6px;border-left:3px solid #ef4444;font-size:0.84rem;white-space:pre-wrap;word-wrap:break-word;">{ch["original_text"]}</div>', unsafe_allow_html=True)
                with r:
                    st.markdown("**After:**")
                    st.markdown(f'<div style="background:#f0fdf4;padding:10px 12px;border-radius:6px;border-left:3px solid #22c55e;font-size:0.84rem;white-space:pre-wrap;word-wrap:break-word;">{ch["changed_text"]}</div>', unsafe_allow_html=True)
                st.caption(f"💡 {ch['rationale']}")

    # ══════════ Audit Trail ══════════
    with t_rl:
        import pandas as pd
        st.caption("Tracks what happened to each violation — was it auto-fixed in the adaptation or does it still need human review?")
        if risk_ledger:
            auto_fixed = sum(1 for e in risk_ledger if e["final_action"]=="auto-fixed")
            flagged = sum(1 for e in risk_ledger if e["final_action"]=="flagged for review")
            rm=st.columns(4)
            rm[0].metric("✅ Auto-Fixed", auto_fixed)
            rm[1].metric("⚠️ Needs Review", flagged)
            rm[2].metric("Brand Issues", sum(1 for e in risk_ledger if e["risk_category"]=="brand"))
            rm[3].metric("Legal Issues", sum(1 for e in risk_ledger if e["risk_category"]=="legal"))

            # Filter
            show_filter = st.radio("Show:", ["All", "Needs Review Only", "Auto-Fixed Only"], horizontal=True, key="rl_filter")
            filtered = risk_ledger
            if show_filter == "Needs Review Only":
                filtered = [e for e in risk_ledger if e["final_action"] == "flagged for review"]
            elif show_filter == "Auto-Fixed Only":
                filtered = [e for e in risk_ledger if e["final_action"] == "auto-fixed"]

            if filtered:
                df=pd.DataFrame(filtered)
                cs=["severity","detected_issue","original_text","rule_violated","risk_category","suggested_replacement","final_action"]
                df = df[[c for c in cs if c in df.columns]]

                # Severity colored chips
                sev_map = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}
                if "severity" in df.columns:
                    df["severity"] = df["severity"].apply(lambda x: f"{sev_map.get(x,'')} {x.upper()}")

                st.dataframe(df, use_container_width=True, hide_index=True,
                             column_config={
                                 "severity": st.column_config.TextColumn("Severity", width="small"),
                                 "detected_issue": st.column_config.TextColumn("Issue", width="medium"),
                                 "original_text": st.column_config.TextColumn("Original Text", width="medium"),
                                 "rule_violated": st.column_config.TextColumn("Rule", width="medium"),
                                 "risk_category": st.column_config.TextColumn("Category", width="small"),
                                 "suggested_replacement": st.column_config.TextColumn("Suggested Fix", width="large"),
                                 "final_action": st.column_config.TextColumn("Action", width="small"),
                             })

                # CSV download
                csv_data = df.to_csv(index=False)
                st.download_button("📥 Download Audit Trail (CSV)", data=csv_data,
                                   file_name="proofline_audit_trail.csv", mime="text/csv",
                                   use_container_width=True)
            else:
                st.info("No items match this filter.")
        else:
            st.info("No audit trail items.")

    # ══════════ Brand DNA ══════════
    with t_dn:
        import plotly.graph_objects as go
        cats=["Brand Fit","Terminology","Claim Safety","CTA","Channel Fit","Audience Fit","Tone"]
        keys=["brand_fit_score","terminology_compliance","claim_risk_score","cta_compliance","channel_fit","audience_fit","tone_alignment"]
        explains = {
            "Brand Fit": "Voice & identity match",
            "Terminology": "Approved terms used",
            "Claim Safety": "Claims cited & safe",
            "CTA": "Approved CTA format",
            "Channel Fit": "Length & structure",
            "Audience Fit": "Tone for audience",
            "Tone": "Confident, direct, human",
        }
        vb=[brand_dna_before.get(k,0) for k in keys]; va=[brand_dna.get(k,0) for k in keys]
        fig=go.Figure()
        fig.add_trace(go.Scatterpolar(r=vb+[vb[0]],theta=cats+[cats[0]],fill="toself",name="Original",line_color="#ef4444",fillcolor="rgba(239,68,68,0.12)"))
        fig.add_trace(go.Scatterpolar(r=va+[va[0]],theta=cats+[cats[0]],fill="toself",name="Adapted",line_color="#22c55e",fillcolor="rgba(34,197,94,0.12)"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),showlegend=True,height=420,
                          legend=dict(orientation="h",y=-0.1,x=0.5,xanchor="center"),margin=dict(t=20,b=40,l=60,r=60))
        st.plotly_chart(fig,use_container_width=True,config={"displayModeBar": False})

        # Dimension cards in a row
        dim_cards = ""
        for c, k in zip(cats, keys):
            bv, av = brand_dna_before.get(k, 0), brand_dna.get(k, 0)
            d = av - bv
            d_sign = f"+{d:.0f}" if d > 0 else f"{d:.0f}" if d < 0 else "—"
            d_color = "#16a34a" if d > 0 else "#ef4444" if d < 0 else "#94a3b8"
            bg = "#f0fdf4" if av >= 80 else "#fffbeb" if av >= 50 else "#fef2f2"
            border = "#bbf7d0" if av >= 80 else "#fde68a" if av >= 50 else "#fecaca"
            dim_cards += (
                f'<div style="flex:1;min-width:0;background:{bg};border:1px solid {border};border-radius:10px;'
                f'padding:12px 8px;text-align:center;">'
                f'<div style="font-size:1.4rem;font-weight:800;color:#1e293b;">{av:.0f}</div>'
                f'<div style="font-size:0.7rem;font-weight:600;color:{d_color};margin-bottom:4px;">{d_sign}</div>'
                f'<div style="font-size:0.7rem;font-weight:700;color:#475569;">{c}</div>'
                f'<div style="font-size:0.6rem;color:#94a3b8;margin-top:2px;">{explains.get(c,"")}</div>'
                f'</div>'
            )
        st.markdown(f'<div style="display:flex;gap:6px;margin-top:8px;">{dim_cards}</div>', unsafe_allow_html=True)

    # ══════════ Reviewers ══════════
    with t_rv:
        # Verdict summary bar
        n_app = sum(1 for r in reviewers if r["verdict"] == "approved")
        n_cond = sum(1 for r in reviewers if r["verdict"] == "conditional")
        n_rej = sum(1 for r in reviewers if r["verdict"] == "rejected")
        sum_parts = []
        if n_app: sum_parts.append(f'<span style="color:#16a34a;font-weight:700;">{n_app} Approved</span>')
        if n_cond: sum_parts.append(f'<span style="color:#d97706;font-weight:700;">{n_cond} Conditional</span>')
        if n_rej: sum_parts.append(f'<span style="color:#dc2626;font-weight:700;">{n_rej} Rejected</span>')
        st.markdown(f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 20px;margin-bottom:16px;font-size:0.9rem;">'
                    f'<strong>Verdict Summary:</strong> {" · ".join(sum_parts)}'
                    f'<span style="float:right;font-size:0.78rem;color:#64748b;">Certainty = how confident each reviewer is in their own verdict</span>'
                    f'</div>', unsafe_allow_html=True)
        rc=st.columns(2)
        for idx,rv in enumerate(reviewers):
            vd=rv["verdict"]; cls={"approved":"rv-ok","conditional":"rv-cond","rejected":"rv-rej"}.get(vd,""); ic={"approved":"🟢","conditional":"🟡","rejected":"🔴"}.get(vd,"⚪")
            verdict_label = {"approved":"Approved — ready to publish","conditional":"Conditional — needs minor fixes","rejected":"Rejected — has blocking issues"}.get(vd, vd)
            with rc[idx%2]:
                st.markdown(f'<div class="rv-card {cls}"><strong>{ic} {rv["reviewer_name"]}</strong>'
                            f'<br/><span style="font-size:0.85rem;color:#1e293b;font-weight:600;">{verdict_label}</span>'
                            f'<span style="float:right;font-size:0.78rem;color:#64748b;">Certainty: {rv.get("confidence_score",0):.0%}</span>'
                            f'<br/><em style="color:#475569;font-size:0.85rem;">{rv.get("reason","")}</em></div>',unsafe_allow_html=True)
                concerns = rv.get("top_concerns",[])
                if concerns:
                    for c in concerns: st.markdown(f"- {c}")

    # ══════════ Export ══════════
    with t_pk:
        st.markdown("#### Export Approval Packet")
        st.caption("Download, preview, or share the complete audit results.")

        ex1, ex2 = st.columns(2)
        with ex1:
            st.markdown(f"**Status:** {bt}")
            st.markdown(f"**Violations:** {len(audit['violations'])} ({audit.get('critical_count',0)} critical)")
        with ex2:
            st.markdown(f"**Channel:** {chl}")
            st.markdown(f"**Audience:** {aul}")

        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 20px;margin:12px 0;font-size:0.82rem;color:#475569;">'
            '<strong style="color:#1e293b;">Included in export:</strong><br/>'
            'Violation report with rule citations · Adapted content with change log · '
            'Audit trail · Brand DNA scores (before & after) · 4 reviewer verdicts · '
            'Risk score · Publishability status · Final recommendation'
            '</div>', unsafe_allow_html=True)

        # Download buttons
        d1,d2=st.columns(2)
        md_report = _gen_md(result)
        with d1:
            st.download_button("Download JSON",data=json.dumps(result,indent=2,default=str),file_name=f"proofline_{result['run_id'][:8]}.json",mime="application/json",use_container_width=True)
            st.caption("Machine-readable · for system integration")
        with d2:
            st.download_button("Download Report",data=md_report,file_name=f"proofline_{result['run_id'][:8]}.md",mime="text/markdown",use_container_width=True)
            st.caption("Human-readable · for approval workflow")

        # Report preview
        with st.expander("Preview Report", expanded=False):
            st.markdown(md_report)

        # Integration hints
        st.markdown('<div style="margin-top:16px;font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#94a3b8;">Coming Soon</div>', unsafe_allow_html=True)
        r1,r2,r3 = st.columns(3)
        with r1: st.button("Send to Slack", disabled=True, use_container_width=True, key="exp_slack")
        with r2: st.button("Create Jira Ticket", disabled=True, use_container_width=True, key="exp_jira")
        with r3: st.button("Email Report", disabled=True, use_container_width=True, key="exp_email")

    with t_ru:
        st.markdown("#### Brand Rules Reference")
        st.caption("All parsed rules from your brand guidelines. Hover on any rule pill in other tabs to see the description.")
        if rules_map:
            # Search filter
            search_q = st.text_input("Find a rule:", placeholder="Search by keyword, rule ID, or section…", key="rule_search")
            search_lower = search_q.lower().strip() if search_q else ""

            # Group by section
            sections: dict[str, list] = {}
            for r in rules_map.values():
                sec = r.get("section", "Other")
                sections.setdefault(sec, []).append(r)

            shown_count = 0
            for idx, (sec_name, sec_rules) in enumerate(sections.items()):
                # Filter rules if search is active
                if search_lower:
                    filtered_rules = [r for r in sec_rules if
                                      search_lower in r.get("description","").lower() or
                                      search_lower in r.get("rule_id","").lower() or
                                      search_lower in sec_name.lower() or
                                      search_lower in r.get("rule_type","").lower() or
                                      any(search_lower in ex.lower() for ex in r.get("examples_bad",[])) or
                                      any(search_lower in ex.lower() for ex in r.get("examples_good",[]))]
                else:
                    filtered_rules = sec_rules

                if not filtered_rules:
                    continue

                shown_count += len(filtered_rules)
                # Expand first section by default, or all if searching
                expand = (idx == 0 and not search_lower) or bool(search_lower)
                with st.expander(f"**{sec_name}** ({len(filtered_rules)} rules)", expanded=expand):
                    for r in filtered_rules:
                        rtype = r.get("rule_type", "").replace("_", " ").title()
                        pill = _rule_pill(r["rule_id"], sec_name, rules_map)
                        st.markdown(
                            f'{pill} <span style="color:#64748b;font-size:0.78rem;">[{rtype}]</span><br/>'
                            f'<span style="color:#1e293b;font-size:0.88rem;">{r["description"]}</span>',
                            unsafe_allow_html=True)
                        ex_good = r.get("examples_good", [])
                        ex_bad = r.get("examples_bad", [])
                        if ex_good:
                            st.markdown(f'<span style="color:#16a34a;font-size:0.78rem;">✓ {" · ".join(ex_good)}</span>', unsafe_allow_html=True)
                        if ex_bad:
                            st.markdown(f'<span style="color:#dc2626;font-size:0.78rem;">✗ {" · ".join(ex_bad)}</span>', unsafe_allow_html=True)
                        st.markdown("<hr style='margin:6px 0;border-color:#f1f5f9;'>", unsafe_allow_html=True)

            if search_lower:
                st.caption(f"Showing {shown_count} of {len(rules_map)} rules matching \"{search_q}\"")
            else:
                st.caption(f"Total: {len(rules_map)} rules")
        else:
            st.info("No rules loaded. Run the pipeline first.")

# ── Consistency ──
elif st.session_state.page == "consistency":
    st.markdown("## 🔄 Campaign Consistency"); st.caption("Compare content assets across channels.")
    if not st.session_state.guidelines_ingested: st.warning("Ingest guidelines first."); st.stop()
    num=st.slider("Assets:",2,6,3); ai_list=[]; chn={v:CHANNELS[v]["label"] for v in CHANNELS}; cho=list(chn.keys())
    cols=st.columns(min(num,3))
    for i in range(num):
        with cols[i%len(cols)]:
            st.markdown(f"**Asset {i+1}**"); lb=st.text_input("Label",f"Asset {i+1}",key=f"ca_l_{i}")
            chv=st.selectbox("Channel",cho,format_func=lambda x:chn[x],key=f"ca_c_{i}",index=i%len(cho))
            ctv=st.text_area("Content",height=140,key=f"ca_t_{i}",placeholder=f"Paste {chn[chv]} content…")
            ai_list.append({"label":lb,"channel":chv,"content":ctv})
    if st.button("🔄 Run Check",use_container_width=True,type="primary"):
        fl=[a for a in ai_list if a["content"].strip()]
        if len(fl)<2: st.error("Need at least 2 assets.")
        else:
            with st.spinner(f"Checking {len(fl)} assets…"):
                cr=call_api("/api/v1/consistency",{"assets":fl,"guideline_id":st.session_state.guideline_id})
                if cr: st.session_state.consistency_result=cr
    if st.session_state.consistency_result:
        cr=st.session_state.consistency_result; sco=cr["overall_consistency_score"]
        ico="🟢" if sco>=80 else "🟡" if sco>=50 else "🔴"
        st.markdown(f"### {ico} Score: {sco:.0f}/100")
        if cr.get("summary"): st.info(cr["summary"])
        ct1,ct2,ct3,ct4=st.tabs([f"📝 Terms ({len(cr['term_inconsistencies'])})",f"🔗 CTAs ({len(cr['cta_inconsistencies'])})",f"🎭 Tone ({len(cr['tone_drifts'])})",f"⚖️ Claims ({len(cr['claim_inconsistencies'])})"])
        with ct1:
            for t in cr["term_inconsistencies"]:
                si={"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}.get(t.get("severity","medium"),"⚪")
                with st.expander(f"{si} {', '.join(t['term_variants'])}"): st.markdown(f"**Canonical:** `{t['canonical_term']}` · **Rule:** `{t['rule_reference']}` · **Assets:** {', '.join(t['asset_labels'])}")
            if not cr["term_inconsistencies"]: st.success("None.")
        with ct2:
            for c in cr["cta_inconsistencies"]:
                with st.expander(f"Variants: {', '.join(c['cta_variants'])}"): st.markdown(f"**Recommended:** `{c['recommended_cta']}`")
            if not cr["cta_inconsistencies"]: st.success("None.")
        with ct3:
            for td in cr["tone_drifts"]:
                si={"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}.get(td.get("severity","medium"),"⚪")
                with st.expander(f"{si} {td['asset_label']}: {td['direction']}"): st.markdown(td["description"])
            if not cr["tone_drifts"]: st.success("None.")
        with ct4:
            for cl in cr["claim_inconsistencies"]:
                si={"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}.get(cl.get("severity","medium"),"⚪")
                with st.expander(f"{si} {cl['claim'][:60]}"): st.markdown(f"**Issue:** {cl['issue']} · **Assets:** {', '.join(cl['asset_labels'])}")
            if not cr["claim_inconsistencies"]: st.success("None.")
        if cr.get("recommendations"):
            st.markdown("#### 💡 Recommendations")
            for r in cr["recommendations"]:
                st.markdown(f"- {r}")

elif st.session_state.page == "results" and not st.session_state.pipeline_result:
    st.info("No results yet."); st.button("← Home",on_click=lambda:st.session_state.update(page="home"))
