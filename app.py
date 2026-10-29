"""Shortfundly Campus Email Automation - Streamlit dashboard.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import base64 as _b64
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from shortfundly import contacts as ct
from shortfundly import database as db
from shortfundly import importer, sending
from shortfundly import stats as stats_mod
from shortfundly import template_service as ts
from shortfundly.config import Config, load_config
from shortfundly.mailer import SMTPMailer

st.set_page_config(page_title="Shortfundly Campus Outreach Engine", page_icon="🔴", layout="wide")

VERIFICATION_OPTIONS = ["All", "verified", "unverified"]

# --------------------------------------------------------------- UI / styling


def _app_dir() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def _logo_html(size_px: int = 56) -> str:
    """Return an <img> tag with the embedded logo.jpg, or an SVG fallback."""
    path = os.path.join(_app_dir(), "logo.jpg")
    try:
        with open(path, "rb") as fh:
            data = _b64.b64encode(fh.read()).decode("ascii")
        return (
            f'<img class="sf-logo" src="data:image/jpeg;base64,{data}" '
            f'style="width:{size_px}px;height:{size_px}px;border-radius:50%;object-fit:cover;'
            f'box-shadow:0 0 16px rgba(255,43,68,0.45);border:2px solid rgba(255,43,68,0.6);" alt="Shortfundly"/>'
        )
    except Exception:
        return (
            f'<svg class="sf-logo" viewBox="0 0 100 100" style="width:{size_px}px;height:{size_px}px;" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="50" cy="50" r="46" fill="#0B0E14" stroke="#FF2B44" stroke-width="4"/>'
            '<circle cx="50" cy="50" r="38" fill="url(#grad)"/>'
            '<defs><linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0%" stop-color="#FF2B44"/><stop offset="100%" stop-color="#8B1020"/>'
            '</linearGradient></defs>'
            '<path d="M42 32 L70 50 L42 68 Z" fill="#ffffff"/></svg>'
        )


_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

/* ---- Base & Typography ---- */
html, body, .stApp, .stMarkdown, .stText, [data-testid="stMarkdownContainer"], [data-baseweb="input"] input, div[data-testid="stMetricValue"] {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  letter-spacing: -0.01em;
}

code, pre, .stCodeBlock {
  font-family: 'JetBrains Mono', monospace !important;
}

/* ---- Protect Streamlit Icons & Ligatures ---- */
[data-testid*="Icon"],
[data-testid*="icon"],
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined,
.material-icons,
[class*="material-symbols"],
[class*="material-icons"],
button[aria-label*="password" i] span,
button[aria-label*="password" i] i,
span[translate="no"] {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
  font-weight: normal !important;
  font-style: normal !important;
  font-size: 20px !important;
  line-height: 1 !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  display: inline-block !important;
  white-space: nowrap !important;
  word-wrap: normal !important;
  direction: ltr !important;
  -webkit-font-smoothing: antialiased !important;
  font-feature-settings: 'liga' 1 !important;
}

/* ---- Custom Scrollbars ---- */
::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-track { background: #0B0E14; }
::-webkit-scrollbar-thumb { background: #1E2838; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #FF2B44; }

/* ---- Animations ---- */
@keyframes sfFadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes sfPulseGlow { 0%, 100% { box-shadow: 0 0 12px rgba(255,43,68,0.25); } 50% { box-shadow: 0 0 26px rgba(255,43,68,0.6); } }
@keyframes sfPulseDot { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.35); opacity: 0.6; } }

/* ---- Modern Hero Header ---- */
.sf-hero {
  border-radius: 20px;
  padding: 24px 30px;
  margin-bottom: 22px;
  color: #fff;
  background: linear-gradient(135deg, rgba(255,43,68,0.14) 0%, rgba(20,26,38,0.95) 55%, rgba(11,14,20,0.98) 100%);
  border: 1px solid rgba(255,43,68,0.25);
  backdrop-filter: blur(20px);
  box-shadow: 0 16px 40px -8px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.1);
  animation: sfFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.sf-hero-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap; }
.sf-hero-left { display: flex; align-items: center; gap: 18px; }
.sf-hero-text h1 { margin: 0; font-size: 1.95rem; font-weight: 800; letter-spacing: -0.02em; color: #ffffff; }
.sf-hero-text p { margin: 0.35rem 0 0; opacity: 0.88; font-size: 0.96rem; color: #cbd5e1; }
.sf-hero-pills { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }

/* ---- Modern Pill Badges ---- */
.sf-pill {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 6px 14px; border-radius: 9999px; font-size: 0.78rem; font-weight: 700;
  letter-spacing: 0.03em; text-transform: uppercase;
}
.sf-pill-live {
  background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.35);
}
.sf-pill-test {
  background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.35);
}
.sf-pill-state {
  background: rgba(59, 130, 246, 0.15); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.35);
}
.sf-pill-user {
  background: rgba(168, 85, 247, 0.15); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.35);
}
.sf-dot {
  width: 7px; height: 7px; border-radius: 50%; display: inline-block;
  animation: sfPulseDot 2s infinite ease-in-out;
}
.sf-dot-live { background: #ef4444; }
.sf-dot-test { background: #10b981; }

/* ---- Metric Cards (Glassmorphic & Hover Lift) ---- */
div[data-testid="stMetric"] {
  background: linear-gradient(150deg, #141B26 0%, #0E121A 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-top: 3px solid #FF2B44 !important;
  border-radius: 14px !important;
  padding: 16px 20px !important;
  box-shadow: 0 10px 25px -4px rgba(0,0,0,0.4) !important;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
  animation: sfFadeUp 0.5s ease both;
}
div[data-testid="stMetric"]:hover {
  transform: translateY(-4px) !important;
  border-top-color: #FF4D64 !important;
  box-shadow: 0 16px 36px -4px rgba(255, 43, 68, 0.2), 0 0 1px 1px rgba(255, 43, 68, 0.3) !important;
}
div[data-testid="stMetric"] label {
  font-size: 0.8rem !important;
  font-weight: 600 !important;
  color: #94A3B8 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
  font-size: 1.85rem !important;
  font-weight: 800 !important;
  color: #FFFFFF !important;
  letter-spacing: -0.02em !important;
}

/* ---- Modern Tabs ---- */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px !important;
  background: #0F141F !important;
  padding: 6px 8px !important;
  border-radius: 14px !important;
  border: 1px solid #1E283A !important;
  margin-bottom: 20px !important;
}
.stTabs [data-baseweb="tab"] {
  height: 42px !important;
  border-radius: 10px !important;
  padding: 6px 20px !important;
  font-weight: 600 !important;
  font-size: 0.92rem !important;
  color: #94A3B8 !important;
  border: none !important;
  transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
  color: #FFFFFF !important;
  background: rgba(255, 255, 255, 0.04) !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, #FF2B44 0%, #C41228 100%) !important;
  color: #FFFFFF !important;
  box-shadow: 0 4px 14px rgba(255, 43, 68, 0.38) !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

/* ---- Buttons ---- */
button[kind="primary"], .stButton > button[type="primary"] {
  background: linear-gradient(135deg, #FF2B44 0%, #D4142D 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em !important;
  padding: 0.55rem 1.35rem !important;
  box-shadow: 0 4px 16px rgba(255, 43, 68, 0.32) !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
button[kind="primary"]:hover, .stButton > button[type="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(255, 43, 68, 0.5) !important;
  background: linear-gradient(135deg, #FF455C 0%, #E01B34 100%) !important;
}
.stButton > button:not([kind="primary"]) {
  background: #141B27 !important;
  border: 1px solid #232D3F !important;
  color: #E2E8F0 !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  transition: all 0.2s ease !important;
}
.stButton > button:not([kind="primary"]):hover {
  background: #1C2637 !important;
  border-color: #FF2B44 !important;
  color: #FFFFFF !important;
  transform: translateY(-1px) !important;
}

/* ---- Form Inputs ---- */
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
  background-color: #111723 !important;
  border: 1px solid #202B3C !important;
  border-radius: 12px !important;
  color: #FFFFFF !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within, div[data-baseweb="textarea"]:focus-within {
  border-color: #FF2B44 !important;
  box-shadow: 0 0 0 3px rgba(255, 43, 68, 0.22) !important;
}

/* ---- Containers & Cards ---- */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: #111622 !important;
  border: 1px solid #1D2638 !important;
  border-radius: 18px !important;
  padding: 22px 24px !important;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3) !important;
  margin-bottom: 18px !important;
  animation: sfFadeUp 0.5s ease both;
}

/* ---- Sidebar Profile & Widgets ---- */
.sf-profile-card {
  background: linear-gradient(135deg, rgba(255, 43, 68, 0.12) 0%, rgba(20, 26, 38, 0.8) 100%);
  border: 1px solid rgba(255, 43, 68, 0.3);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.sf-profile-avatar {
  width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, #FF2B44, #991020);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.15rem; font-weight: 800; color: white;
  box-shadow: 0 4px 12px rgba(255, 43, 68, 0.45);
}
.sf-profile-info h3 { margin: 0; font-size: 1.05rem; font-weight: 700; color: #FFFFFF; }
.sf-profile-info p { margin: 2px 0 0; font-size: 0.78rem; color: #94A3B8; }

/* ---- Redesigned Unified Login Screen ---- */
.login-header-wrap {
  text-align: center;
  padding: 10px 0 20px;
  animation: sfFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.login-icon-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(255, 43, 68, 0.18) 0%, rgba(255, 43, 68, 0.04) 100%);
  border: 1px solid rgba(255, 43, 68, 0.35);
  box-shadow: 0 10px 28px -4px rgba(255, 43, 68, 0.35);
  color: #FF3B53;
  margin-bottom: 14px;
}
.login-title {
  margin: 0 0 6px 0;
  font-size: 1.85rem;
  font-weight: 800;
  letter-spacing: -0.025em;
  color: #FFFFFF;
}
.login-subtitle {
  margin: 0 auto;
  font-size: 0.92rem;
  color: #94A3B8;
  line-height: 1.45;
}
.login-system-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding: 4px 14px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  background: rgba(16, 185, 129, 0.12);
  color: #6EE7B7;
  border: 1px solid rgba(16, 185, 129, 0.28);
}
.login-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10B981;
  box-shadow: 0 0 8px #10B981;
  animation: sfPulseDot 2s infinite ease-in-out;
}
.login-footer-note {
  text-align: center;
  margin-top: 16px;
  font-size: 0.76rem;
  color: #64748B;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.login-footer-note code {
  color: #94A3B8;
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
}

/* ---- Form Container Polish ---- */
div[data-testid="stForm"] {
  background: linear-gradient(160deg, #131926 0%, #0D121B 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-top: 2px solid #FF2B44 !important;
  border-radius: 20px !important;
  padding: 26px 28px !important;
  box-shadow: 0 20px 48px -12px rgba(0, 0, 0, 0.65), 0 0 1px 1px rgba(255, 255, 255, 0.04) !important;
}

/* ---- Chips ---- */
.sf-chip {
  display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 0.75rem;
  font-weight: 600; font-family: 'JetBrains Mono', monospace;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  color: #E2E8F0; margin: 2px;
}
</style>
"""


def inject_css() -> None:
    """Inject global modern executive styling."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, mode: str = "test", state: str = "Kerala", user: str = "Arjumaan") -> None:
    """Render a modern executive command header with branding and dynamic status pills."""
    logo = _logo_html()
    mode_class = "sf-pill-live" if mode.lower() == "live" else "sf-pill-test"
    dot_class = "sf-dot-live" if mode.lower() == "live" else "sf-dot-test"
    mode_label = f'<span class="sf-dot {dot_class}"></span> LIVE MODE' if mode.lower() == "live" else f'<span class="sf-dot {dot_class}"></span> TEST MODE (Safe)'

    st.markdown(
        f"""
        <div class="sf-hero">
          <div class="sf-hero-row">
            <div class="sf-hero-left">
              {logo}
              <div class="sf-hero-text">
                <h1>{title}</h1>
                <p>{subtitle}</p>
              </div>
            </div>
            <div class="sf-hero-pills">
              <span class="sf-pill {mode_class}">{mode_label}</span>
              <span class="sf-pill sf-pill-state">📍 State: {state}</span>
              <span class="sf-pill sf-pill-user">👤 {user}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------ helpers
def flash(kind: str, message: str) -> None:
    """Remember a message across the next rerun."""
    st.session_state["_flash"] = (kind, message)


def show_flash() -> None:
    kind, message = st.session_state.pop("_flash", (None, None))
    if kind:
        getattr(st, kind)(message)


def get_sender(conn, cfg: Config) -> dict:
    return {
        "sender_name": db.get_setting(conn, "sender_name", cfg.sender_name or "Arjumaan") or "Arjumaan",
        "sender_title": db.get_setting(conn, "sender_title", cfg.sender_title or "Campus Partnership Manager") or "Campus Partnership Manager",
    }


def contact_label(c) -> str:
    return f"#{c['id']} {c['college_name']} <{c['email']}>"


def csv_download(df: pd.DataFrame, label: str, filename: str, key: str) -> None:
    st.download_button(label, df.to_csv(index=False).encode("utf-8-sig"), filename, "text/csv", key=key)


# ------------------------------------------------------------------ sidebar
def render_sidebar(conn, cfg: Config) -> dict:
    with st.sidebar:
        # Profile Header
        st.markdown(
            """
            <div class="sf-profile-card">
              <div class="sf-profile-avatar">A</div>
              <div class="sf-profile-info">
                <h3>Arjumaan</h3>
                <p>Campus Outreach Lead · Kerala</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🚪 Sign out", use_container_width=True):
            st.session_state.pop("_authenticated", None)
            st.rerun()

        st.divider()
        st.markdown("### 🛡️ Dispatch Safeguards")
        if cfg.send_mode == "live":
            st.error("⚡ **LIVE MODE ENABLED**\n\nReal emails permitted after explicit two-factor typing confirmation.")
        else:
            st.success(
                f"🛡️ **TEST MODE (Safe)**\n\nEvery email safely intercepted and routed to:\n`{cfg.test_recipient or 'arjumaan21@gmail.com'}`"
            )

        st.caption("SMTP Service: " + ("✅ Configured" if cfg.smtp_configured else "⚠️ Not configured (.env)"))
        if st.button("🔍 Test SMTP Connection", disabled=not cfg.smtp_configured, use_container_width=True):
            try:
                SMTPMailer(cfg).check_connection()
                st.success("✅ SMTP authenticated successfully.")
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)
                if hasattr(exc, "smtp_error") and isinstance(exc.smtp_error, bytes):
                    err_msg = exc.smtp_error.decode("utf-8", errors="replace")
                st.error(cfg.redact(f"❌ {type(exc).__name__}: {err_msg}"))

        st.divider()
        st.markdown("### ✍️ Sender Details")
        st.caption("Applied dynamically across `{sender_name}` and `{sender_title}` variables.")
        current = get_sender(conn, cfg)
        with st.form("sender_form"):
            name = st.text_input("Sender name", value=current["sender_name"])
            title = st.text_input("Sender title", value=current["sender_title"])
            if st.form_submit_button("Save sender details", use_container_width=True):
                db.set_setting(conn, "sender_name", name.strip() or "Arjumaan")
                db.set_setting(conn, "sender_title", title.strip())
                st.success("Sender profile saved.")
                st.rerun()

        st.markdown(
            """
            <div style="margin-top:20px; padding:12px; border-radius:10px; background:#0B0E14; border:1px solid #1D2638; font-size:0.75rem; color:#64748B;">
              <div><strong>Region:</strong> Kerala (Official)</div>
              <div><strong>Engine:</strong> Shortfundly Campus v2.5</div>
              <div><strong>Account:</strong> arjumaan21@gmail.com</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    return get_sender(conn, cfg)


# ---------------------------------------------------------------- dashboard
def render_dashboard(conn) -> None:
    s = stats_mod.get_stats(conn)
    with st.container(border=True):
        st.markdown("### 📇 Official Contact Directory")
        c = st.columns(4)
        c[0].metric("Total Contacts", s["contacts_total"])
        c[1].metric("Verified Records", s["contacts_verified"])
        c[2].metric("Pending Verification", s["contacts_unverified"])
        c[3].metric("Validation Issues", s["contacts_invalid"])

        total = s["contacts_total"] or 0
        if total:
            pct = s["contacts_verified"] / total
            st.markdown(f"**Verification Progress:** {s['contacts_verified']} of {total} contacts ({pct*100:.1f}%)")
            st.progress(pct)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        c2 = st.columns(4)
        c2[0].metric("Multi-Contact Colleges", s["duplicate_college_groups"])
        c2[1].metric("Rejected: Invalid", s["rejected_invalid_rows"])
        c2[2].metric("Rejected: Duplicate", s["rejected_duplicate_rows"])
        c2[3].metric("Campus Group Members", s["duplicate_college_contacts"])

    with st.container(border=True):
        st.markdown("### 📧 Email Delivery Telemetry (Live)")
        e = s["emails_live"]
        c = st.columns(5)
        c[0].metric("Pending Dispatch", e["pending"])
        c[1].metric("Currently Sending", e["sending"])
        c[2].metric("Accepted by SMTP", e["sent"])
        c[3].metric("Dispatch Failed", e["failed"])
        c[4].metric("Lifetime Tracked", e["total"])
        t = s["emails_test"]
        st.caption(
            f"🛡️ Test-mode messages intercepted: {t['total']} total | "
            f"{t['sent']} accepted | {t['failed']} failed | {t['pending']} pending."
        )
        st.info(f"ℹ️ {sending.SMTP_ACCEPTANCE_NOTE}")

    if s["contacts_by_state"]:
        with st.container(border=True):
            st.markdown("### 📊 Contact Distribution by State")
            st.bar_chart(pd.Series(s["contacts_by_state"], name="Contacts"), color="#FF2B44")


# ----------------------------------------------------------------- contacts
def filter_row(conn, key: str):
    c1, c2, c3, c4 = st.columns(4)
    text = c1.text_input("🔍 Search keyword", key=f"{key}_text", placeholder="Search college, email, or city...")
    state = c2.selectbox("State Filter", ["All"] + ct.list_states(conn), key=f"{key}_state")
    city = c3.selectbox("City Filter", ["All"] + ct.list_cities(conn, "" if state == "All" else state), key=f"{key}_city")
    ver = c4.selectbox("Verification Filter", VERIFICATION_OPTIONS, key=f"{key}_ver")
    return text, "" if state == "All" else state, "" if city == "All" else city, "" if ver == "All" else ver


def render_browse(conn) -> None:
    text, state, city, ver = filter_row(conn, "browse")
    df = ct.search_contacts(conn, text, state, city, ver)
    st.caption(f"Showing {len(df)} matching contact(s)")
    shown = ["id", "state", "city", "college_name", "contact_person", "department", "email",
             "website", "source_url", "verification_status"]
    st.dataframe(df[shown], hide_index=True, use_container_width=True)
    if df.empty:
        return
    rows = {int(r["id"]): r for r in df.to_dict("records")}

    with st.container(border=True):
        st.markdown("#### ✏️ Edit Contact")
        cid = st.selectbox("Select contact to edit", list(rows), index=None, format_func=lambda i: contact_label(rows[i]),
                           placeholder="Choose a contact...", key="edit_pick")
        if cid is not None:
            cur = rows[cid]
            with st.form(f"edit_form_{cid}"):
                cols = st.columns(2)
                vals = {
                    "college_name": cols[0].text_input("College Name *", cur["college_name"]),
                    "email": cols[1].text_input("Official Email *", cur["email"]),
                    "state": cols[0].text_input("State *", cur["state"]),
                    "city": cols[1].text_input("City *", cur["city"]),
                    "website": cols[0].text_input("Official Website", cur["website"]),
                    "source_url": cols[1].text_input("Source Page URL", cur["source_url"]),
                    "contact_person": cols[0].text_input("Contact Person", cur["contact_person"]),
                    "department": cols[1].text_input("Department", cur["department"]),
                }
                if st.form_submit_button("Save changes", type="primary"):
                    try:
                        ct.update_contact(conn, cid, vals)
                        flash("success", "Contact updated (verification resets if email/website/source changed).")
                        st.rerun()
                    except ct.ContactError as exc:
                        for err in exc.errors:
                            st.error(err)

    with st.container(border=True):
        st.markdown("#### 🗑️ Delete Contacts")
        doomed = st.multiselect("Select contacts to delete", list(rows), format_func=lambda i: contact_label(rows[i]))
        confirm = st.checkbox("I understand this permanently deletes the selected contacts", key="del_confirm")
        if st.button("Delete selected contacts", disabled=not (doomed and confirm)):
            n = ct.delete_contacts(conn, doomed)
            flash("success", f"Deleted {n} contact(s). Historical audit trail preserved.")
            st.rerun()


def render_import(conn) -> None:
    st.markdown("#### 📥 Bulk Import Contacts")
    st.write("Upload a CSV or Excel file. Nothing is written to the database until you review the preview and confirm.")
    st.caption("Required columns: `state`, `city`, `college_name`, `email`. Optional: `website`, `contact_person`, "
               "`department`, `source_url`. Common variants (e.g. 'Official Email') are mapped automatically.")
    upload = st.file_uploader("Upload contacts file", type=["csv", "xlsx", "xlsm"], key="import_file")
    if st.button("Analyse file", disabled=upload is None, type="primary"):
        try:
            df = importer.read_table(upload.getvalue(), upload.name)
            st.session_state["import_preview"] = importer.build_preview(conn, df, upload.name)
        except importer.ImportFormatError as exc:
            st.session_state.pop("import_preview", None)
            st.error(str(exc))

    preview = st.session_state.get("import_preview")
    if not preview:
        return
    st.markdown(f"#### 🔍 Validation Preview: `{preview.filename}`")
    if preview.missing_columns:
        st.error("Missing required column(s): " + ", ".join(preview.missing_columns))
        return
    if preview.ignored_columns:
        st.caption("Ignored columns: " + ", ".join(preview.ignored_columns))
    c = st.columns(4)
    c[0].metric("Ready to Import", len(preview.ok_rows))
    c[1].metric("Invalid Rows", preview.invalid_count)
    c[2].metric("Duplicate Emails", preview.duplicate_count)
    c[3].metric("Colleges Existing", preview.duplicate_college_count)
    st.dataframe(importer.preview_dataframe(preview), hide_index=True, use_container_width=True)
    skip = st.checkbox("Skip extra contacts for colleges that already exist in database", value=False)
    st.caption("Imported contacts are always saved as UNVERIFIED. Verify them in the Verification tab.")
    if st.button("Save valid rows to database", disabled=not preview.ok_rows, type="primary"):
        result = importer.commit_import(conn, preview, skip_existing_colleges=skip)
        st.session_state.pop("import_preview", None)
        flash("success", f"Imported {result.inserted} contact(s). Rejected: {result.invalid} invalid, "
                         f"{result.duplicates} duplicate.")
        st.rerun()


def render_add(conn) -> None:
    st.markdown("#### ➕ Add Single College Contact")
    st.caption("Manual entry defaults to official state **Kerala**. All fields marked with * are mandatory.")
    with st.form("add_form", clear_on_submit=False):
        cols = st.columns(2)
        vals = {
            "college_name": cols[0].text_input("College Name *", placeholder="e.g. Cochin University of Science and Technology"),
            "email": cols[1].text_input("Official Email *", placeholder="e.g. registrar@cusat.ac.in"),
            "state": cols[0].text_input("State *", value="Kerala"),
            "city": cols[1].text_input("City *", placeholder="e.g. Kochi"),
            "website": cols[0].text_input("Official Website", placeholder="https://www.cusat.ac.in"),
            "source_url": cols[1].text_input("Source Page URL", placeholder="https://www.cusat.ac.in/contact"),
            "contact_person": cols[0].text_input("Contact Person", placeholder="e.g. Dr. K. Mohammed"),
            "department": cols[1].text_input("Department", placeholder="e.g. Dean of Student Affairs"),
        }
        if st.form_submit_button("Add contact to database", type="primary"):
            try:
                ct.add_contact(conn, vals)
                flash("success", "Contact successfully added as UNVERIFIED.")
                st.rerun()
            except ct.ContactError as exc:
                for err in exc.errors:
                    st.error(err)


def render_verification(conn) -> None:
    st.markdown("#### 🛡️ Contact Authenticity Verification")
    st.markdown(
        "Mark a record **verified** only after you have opened the college's **official website** and seen "
        "the email address on the page you recorded as the source. The app also checks that the email and "
        "source page belong to the official website's domain. It cannot browse for you, and it never "
        "invents or auto-verifies contacts. Use the Kerala filter below to work through Kerala colleges."
    )
    c1, c2 = st.columns(2)
    state = c1.selectbox("Filter State", ["All"] + ct.list_states(conn), key="ver_state")
    status = c2.selectbox("Filter Status", ["unverified", "verified"], key="ver_status")
    df = ct.search_contacts(conn, state="" if state == "All" else state, verification=status)
    if df.empty:
        st.info("No contacts match the filter criteria.")
        return
    rows = {int(r["id"]): r for r in df.to_dict("records")}
    cid = st.selectbox("Select contact to review", list(rows), format_func=lambda i: contact_label(rows[i]), key="ver_pick")
    cur = rows[cid]

    with st.container(border=True):
        st.write({k: cur[k] for k in ("college_name", "city", "state", "website", "email", "source_url", "verification_status")})
        c_link1, c_link2 = st.columns(2)
        if cur["website"]:
            c_link1.markdown(f"🌐 [Open Official Website]({cur['website']})")
        if cur["source_url"]:
            c_link2.markdown(f"🔗 [Open Source Page]({cur['source_url']})")

        if cur["verification_status"] == "verified":
            st.success(f"✅ Verified by **{cur['verified_by']}** on {cur['verified_at']}. Note: {cur['verification_note'] or 'None'}")
            if st.button("Mark as unverified"):
                ct.unverify_contact(conn, cid)
                st.rerun()
            return

        problems = ct.verification_problems(cur)
        for p in problems:
            st.warning(f"⚠️ {p}")
        who = st.text_input("Verified by (your name)", value="Arjumaan", key="ver_by")
        note = st.text_input("Verification Note (optional)", key="ver_note")
        seen = st.checkbox("I opened the source page on the official website and personally confirmed this email address", key="ver_seen")
        if st.button("Confirm and mark as VERIFIED", disabled=bool(problems), type="primary"):
            try:
                ct.verify_contact(conn, cid, who, note, seen)
                flash("success", "Record verified successfully.")
                st.rerun()
            except ct.ContactError as exc:
                for err in exc.errors:
                    st.error(err)


def render_export(conn) -> None:
    st.markdown("#### 📤 Export Directory")
    text, state, city, ver = filter_row(conn, "export")
    df = ct.search_contacts(conn, text, state, city, ver)
    st.caption(f"{len(df)} contact(s) ready for export")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Download CSV", ct.export_csv(df), "shortfundly_kerala_contacts.csv", "text/csv", key="dl_csv")
    c2.download_button("⬇️ Download Excel (.xlsx)", ct.export_xlsx(df), "shortfundly_kerala_contacts.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")
    dups = ct.find_duplicate_colleges(conn)
    if not dups.empty:
        st.markdown("#### ⚠️ Colleges with Multiple Contacts")
        st.dataframe(dups.drop(columns=["college_key"]), hide_index=True, use_container_width=True)


# ---------------------------------------------------------------- templates
def _tpl_load_selected() -> None:
    row = ts.load_template(st.session_state["_conn"], st.session_state["tpl_select"])
    if row:
        st.session_state.update(tpl_subject=row["subject"], tpl_body=row["body"], tpl_name=row["name"])
        flash("info", f"Loaded template '{row['name']}'.")


def _tpl_on_upload() -> None:
    f = st.session_state.get("tpl_upload")
    if f is None:
        return
    try:
        st.session_state["tpl_body"] = ts.decode_upload(f.getvalue())
        flash("success", "Body loaded from the file. Review it, then click Save template.")
    except ValueError as exc:
        flash("error", str(exc))


def _tpl_restore_default() -> None:
    conn = st.session_state["_conn"]
    ts.restore_default_template(conn)
    row = ts.load_template(conn, ts.DEFAULT_TEMPLATE_NAME)
    st.session_state.update(tpl_subject=row["subject"], tpl_body=row["body"], tpl_name=row["name"])
    flash("success", "Default proposal restored.")


def render_templates(conn, sender: dict) -> None:
    if "tpl_subject" not in st.session_state:
        row = ts.load_template(conn, ts.DEFAULT_TEMPLATE_NAME)
        st.session_state.update(tpl_subject=row["subject"], tpl_body=row["body"], tpl_name=row["name"])
    st.session_state["_conn"] = conn

    with st.container(border=True):
        st.markdown("#### 📝 Template Designer & Editor")
        c1, c2 = st.columns([3, 1])
        c1.selectbox("Saved Templates", ts.list_templates(conn), key="tpl_select")
        c2.write("")
        c2.button("📂 Load Selected", on_click=_tpl_load_selected, use_container_width=True)
        st.file_uploader("Upload .txt file to replace proposal body", type=["txt"], key="tpl_upload", on_change=_tpl_on_upload)

        st.text_input("Subject Line", key="tpl_subject")
        st.text_area("Email Body", key="tpl_body", height=380)

        chips_html = "".join([f'<span class="sf-chip">{{{{{p}}}}}</span>' for p in ts.ALLOWED_PLACEHOLDERS])
        st.markdown(f"**Available Dynamic Placeholders:** {chips_html}", unsafe_allow_html=True)

        st.text_input("Template Save Name", key="tpl_name")
        b1, b2, b3 = st.columns(3)
        if b1.button("💾 Save Template", type="primary", use_container_width=True):
            try:
                ts.save_template(conn, st.session_state["tpl_name"], st.session_state["tpl_subject"], st.session_state["tpl_body"])
                flash("success", f"Template '{st.session_state['tpl_name']}' saved successfully.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        b2.button("🔄 Restore Default Proposal", on_click=_tpl_restore_default, use_container_width=True)
        if b3.button("🗑️ Delete Selected Template", use_container_width=True):
            try:
                ts.delete_template(conn, st.session_state["tpl_select"])
                flash("success", "Template deleted.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    with st.container(border=True):
        st.markdown("#### 👁️ Live Personalisation Preview")
        df = ct.search_contacts(conn)
        options = {int(r["id"]): r for r in df.to_dict("records")}
        pick = st.selectbox("Render preview with contact:", [0] + list(options),
                            format_func=lambda i: "✨ Sample Kerala College (Demonstration)" if i == 0 else contact_label(options[i]))
        contact = ({"college_name": "Cochin Institute of Technology", "contact_person": "Dr. Suresh Kumar", "department": "Student Affairs",
                    "city": "Kochi", "state": "Kerala"} if pick == 0 else options[pick])
        rendered = ts.render_email(st.session_state["tpl_subject"], st.session_state["tpl_body"], contact, sender)
        for p in rendered.problems:
            st.warning(p + (" - set sender details in the sidebar." if "sender_" in p else ""))
        st.text_input("Personalised Subject Preview", rendered.subject, disabled=True, key=f"prev_subj_{pick}_{hash(rendered.subject)}")
        st.text_area("Personalised Body Preview", rendered.body, height=320, disabled=True, key=f"prev_body_{pick}_{hash(rendered.body)}")


# --------------------------------------------------------------------- send
def render_send(conn, cfg: Config, sender: dict) -> None:
    names = ts.list_templates(conn)
    with st.container(border=True):
        st.markdown("#### 🎯 Campaign Setup")
        c1, c2 = st.columns(2)
        tpl_name = c1.selectbox("Select Template", names, key="send_tpl")
        campaign = c2.text_input("Campaign Label", value=db.get_setting(conn, "campaign", "Kerala Campus Proposal"), key="send_campaign")
        st.caption("🛡️ Duplicate protection: Each recipient receives a live email only once per campaign label.")
    tpl = ts.load_template(conn, tpl_name)

    with st.container(border=True):
        st.markdown("#### 1. Filter & Choose Recipients")
        text, state, city, ver = filter_row(conn, "send")
        only_verified = st.checkbox("Only verified contacts", value=False)
        df = ct.search_contacts(conn, text, state, city, "verified" if only_verified else ver)
        if df.empty:
            st.info("No contacts match the filters.")
            return
        select_all = st.checkbox("Select all filtered contacts", value=False)
        already = sending.emails_in_campaign(conn, campaign)
        view = df[["id", "college_name", "city", "state", "contact_person", "email", "verification_status"]].copy()
        view.insert(0, "Select", select_all)
        view["already_in_campaign"] = view["email"].isin(already)
        sig = hash((text, state, city, ver, only_verified, select_all, campaign))
        edited = st.data_editor(
            view, hide_index=True, key=f"send_editor_{sig}",
            disabled=[c for c in view.columns if c != "Select"],
            column_config={"Select": st.column_config.CheckboxColumn("Select")},
            use_container_width=True,
        )
        ids = [int(i) for i in edited.loc[edited["Select"], "id"]]
        selected = ct.get_contacts(conn, ids)
        st.markdown(f"**{len(selected)}** recipient(s) currently selected.")
        if not selected:
            return
        if any(c["verification_status"] != "verified" for c in selected):
            st.warning("⚠️ Some selected contacts are UNVERIFIED against an official college website.")

    with st.container(border=True):
        st.markdown("#### 2. Recipient Preview")
        by_id = {c["id"]: c for c in selected}
        pid = st.selectbox("Inspect individual message:", list(by_id), format_func=lambda i: contact_label(by_id[i]))
        rendered = ts.render_email(tpl["subject"], tpl["body"], by_id[pid], sender)
        for p in rendered.problems:
            st.error(p)
        st.text_input("Personalised Subject", rendered.subject, disabled=True, key=f"s_subj_{pid}_{hash(rendered.subject)}")
        st.text_area("Personalised Body", rendered.body, height=240, disabled=True, key=f"s_body_{pid}_{hash(rendered.body)}")

    with st.container(border=True):
        st.markdown("#### 3. Attachments (Optional)")
        attach_dir = Path(__file__).parent / "data" / "attachments"
        attach_dir.mkdir(parents=True, exist_ok=True)
        uploaded_files = st.file_uploader(
            "Upload files to attach to this batch",
            accept_multiple_files=True,
            type=["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "png", "jpg", "jpeg", "gif", "txt", "zip"],
            help="PDF, Word, PPT, Excel, images, zip. Max 25 MB total recommended.",
        )
        saved_attachment_paths = []
        if uploaded_files:
            for uf in uploaded_files:
                dest = attach_dir / uf.name
                dest.write_bytes(uf.read())
                saved_attachment_paths.append(str(dest))
            st.success(f"{len(saved_attachment_paths)} attachment(s) staged: "
                       + ", ".join(Path(p).name for p in saved_attachment_paths))

    with st.container(border=True):
        st.markdown("#### 4. Safety Audit & Dispatch")
        live_possible = cfg.send_mode == "live"
        mode = st.radio("Dispatch Mode", ["Test"] + (["Live"] if live_possible else []), horizontal=True,
                        help="Test mode redirects all outgoing messages safely to your internal test address.")
        live = mode == "Live"
        if not live_possible:
            st.caption("Live sending is locked. To enable live mode, set `SEND_MODE=live` in `.env`.")
        if live:
            st.error(f"🚨 **LIVE MODE:** {len(selected)} real email(s) will be dispatched directly to college authorities.")
            phrase = f"SEND {len(selected)}"
            typed = st.text_input(f"Type '{phrase}' to confirm live sending:")
            ack = st.checkbox("I confirm that these emails will be dispatched to real institutions and cannot be undone.")
            confirmed = typed.strip() == phrase and ack
        else:
            st.info(f"🛡️ **TEST MODE:** All {len(selected)} message(s) will be routed to `{cfg.test_recipient or 'arjumaan21@gmail.com'}`.")
            confirmed = True

        if st.button("🚀 Queue and Dispatch Batch", type="primary", disabled=not confirmed or bool(rendered.problems)):
            db.set_setting(conn, "campaign", campaign)
            try:
                q = sending.queue_messages(conn, cfg, selected, tpl["subject"], tpl["body"], sender, campaign,
                                           live=live, live_confirmed=live and confirmed)
                for email, why in q.skipped:
                    st.warning(f"Skipped {email}: {why}")
                if q.created_ids:
                    bar = st.progress(0.0, text="Dispatching emails via SMTP...")
                    res = sending.process_queue(
                        conn, SMTPMailer(cfg), cfg, q.created_ids,
                        progress=lambda done, total, msg: bar.progress(done / total, text=msg),
                        attachments=saved_attachment_paths or None,
                    )
                    bar.empty()
                    (st.success if not res.failed and not res.aborted else st.warning)(
                        f"✅ {res.accepted} accepted by SMTP | ❌ {res.failed} failed | ⏸️ {res.not_attempted} not attempted.")
                    if res.aborted:
                        st.error(res.abort_reason)
                    st.caption(f"{sending.SMTP_ACCEPTANCE_NOTE} Review the History tab for detailed delivery logs.")
            except sending.SendingError as exc:
                st.error(str(exc))


# ------------------------------------------------------------------ history
def render_history(conn, cfg: Config) -> None:
    c1, c2, c3 = st.columns(3)
    text = c1.text_input("🔍 Search history", key="hist_text", placeholder="Search by college or email...")
    status = c2.selectbox("Filter Status", ["All", "pending", "sending", "sent", "failed"], key="hist_status")
    mode = c3.selectbox("Filter Mode", ["All", "live", "test"], key="hist_mode")
    df = sending.history_dataframe(conn, text, "" if status == "All" else status, "" if mode == "All" else mode)
    st.caption(f"ℹ️ {sending.SMTP_ACCEPTANCE_NOTE}")
    cols = ["id", "created_at", "campaign", "college_name", "recipient_email", "delivered_to", "subject", "status",
            "attempt_count", "last_attempt_at", "accepted_at", "last_error", "is_test"]

    if not df.empty:
        vc = df["status"].value_counts()
        m = st.columns(4)
        m[0].metric("Accepted (Sent)", int(vc.get("sent", 0)))
        m[1].metric("Failed", int(vc.get("failed", 0)))
        m[2].metric("Pending", int(vc.get("pending", 0)))
        m[3].metric("Sending", int(vc.get("sending", 0)))

    _status_colors = {"sent": "#10B981", "failed": "#EF4444", "pending": "#F59E0B", "sending": "#3B82F6"}

    def _style_status(val):
        return f"background-color: {_status_colors.get(val, '')}; color: #ffffff; font-weight: bold; border-radius: 4px;" if val in _status_colors else ""

    _shown = df[cols].rename(columns={"status": "status (sent = accepted)"})
    _apply = getattr(_shown.style, "map", None) or _shown.style.applymap
    _styled = _apply(_style_status, subset=["status (sent = accepted)"])
    st.dataframe(_styled, hide_index=True, use_container_width=True)
    csv_download(df[cols], "⬇️ Download History (CSV)", "email_dispatch_history.csv", "hist_dl")

    with st.container(border=True):
        st.markdown("#### 🔁 Retry Failed Messages")
        failed = df[df["status"] == "failed"]
        if failed.empty:
            st.write("No failed messages in the current view.")
        else:
            opts = {int(r["id"]): r for r in failed.to_dict("records")}
            picks = st.multiselect("Failed messages to retry", list(opts),
                                   format_func=lambda i: f"#{i} {opts[i]['recipient_email']} (attempts: {opts[i]['attempt_count']})")
            interrupted = st.checkbox("Include messages interrupted by a crash (they may already have been accepted)")
            needs_live = any(opts[i]["is_test"] == 0 for i in picks)
            live_ok = st.checkbox("I confirm retrying LIVE messages to real recipients") if needs_live else True
            if st.button("Retry selected messages", disabled=not picks or not live_ok, type="primary"):
                try:
                    res = sending.retry_failed(conn, SMTPMailer(cfg), cfg, picks, include_interrupted=interrupted)
                    st.success(f"{res.accepted} accepted, {res.failed} failed again.")
                    for rid, why in res.skipped:
                        st.warning(f"#{rid} skipped: {why}")
                    if res.aborted:
                        st.error(res.abort_reason)
                except sending.SendingError as exc:
                    st.error(str(exc))

    with st.container(border=True):
        st.markdown("#### ⏱️ Recover Stuck Messages")
        minutes = st.number_input("Treat 'sending' rows older than (minutes)", min_value=0, value=15, step=5)
        if st.button("Mark stuck messages as failed (interrupted)"):
            n = sending.recover_stuck_sending(conn, int(minutes))
            st.success(f"{n} message(s) marked as interrupted. Check your mailbox Sent folder before retrying.")


# --------------------------------------------------------------------- login
def _admin_credentials() -> tuple:
    """Admin login credentials. Read from the environment; demo defaults otherwise."""
    user = (os.environ.get("ADMIN_USERNAME") or "admin").strip()
    secret = (os.environ.get("ADMIN_PASSWORD") or "admin@123").strip()
    return user, secret


def require_login() -> bool:
    """Render a modern executive login gate. Returns True once authenticated."""
    if st.session_state.get("_authenticated"):
        return True
    inject_css()

    st.markdown("<div style='height: clamp(24px, 6vh, 60px);'></div>", unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 1.25, 1])
    with center_col:
        st.markdown(
            """
            <div class="login-header-wrap">
              <div class="login-icon-badge">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 17a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9.5C2 7 4 5 6.5 5H17.5C20 5 22 7 22 9.5V17Z"></path>
                  <polyline points="22,7 12,13 2,7"></polyline>
                </svg>
              </div>
              <h1 class="login-title">Campus Outreach Engine</h1>
              <p class="login-subtitle">Email Automation & Intelligence Platform</p>
              <div>
                <span class="login-system-pill">
                  <span class="login-dot"></span> System Ready · Kerala Region
                </span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            st.markdown(
                "<div style='margin-bottom:14px; font-size:0.86rem; font-weight:600; color:#E2E8F0;'>"
                "Sign In with Administrator Credentials</div>",
                unsafe_allow_html=True,
            )
            in_user = st.text_input("Username", placeholder="Enter administrator username")
            in_secret = st.text_input("Password", type="password", placeholder="••••••••••••")
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Sign In to Platform", use_container_width=True, type="primary")

        if submitted:
            exp_user, exp_secret = _admin_credentials()
            if in_user.strip() == exp_user and in_secret.strip() == exp_secret:
                st.session_state["_authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid administrator username or password.")

        st.markdown(
            """
            <div class="login-footer-note">
              <span>🔒 Encrypted Admin Session · Configured in <code>.env</code></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return False


# ---------------------------------------------------------------- automation
def render_automation(conn, cfg: Config) -> None:
    """Automation tab: pipeline status, seed CSV upload, run-now, bulk approve."""
    from shortfundly import monitoring_db as mdb

    mdb.init_monitoring(conn)
    mstats = mdb.monitoring_stats(conn)

    # ---- Status overview ----
    with st.container(border=True):
        st.markdown("### 🤖 Autonomous Pipeline Telemetry")
        c = st.columns(4)
        c[0].metric("Colleges Tracked", mstats["colleges_tracked"])
        c[1].metric("Scraped Contacts", mstats["contacts_total"])
        c[2].metric("Auto-Approved", mstats["contacts_approved"])
        c[3].metric("Pending Review", mstats["pending_approvals"])

        last_run = mstats.get("last_run_at") or "Never"
        st.caption(f"Last automated execution cycle: **{last_run}**")

        col_a, col_b, col_c = st.columns(3)
        col_a.info(
            f"**Auto-Approve Engine:** {'✅ Enabled' if cfg.auto_approve_enabled else '❌ Disabled'}  \n"
            f"Confidence Score Threshold: **{cfg.auto_approve_threshold}/100**"
        )
        col_b.info(
            f"**Auto-Send Engine:** {'✅ Enabled' if cfg.auto_send_enabled else '❌ Disabled'}  \n"
            f"Mode: `{cfg.send_mode}` | Campaign: `{cfg.auto_send_campaign}`"
        )
        col_c.info(
            f"**Monitoring Schedule:** `{cfg.monitor_interval}`  \n"
            f"Target Region: **Kerala** | Seed CSV: `{cfg.seed_csv_path}`"
        )

    # ---- Run pipeline now ----
    with st.container(border=True):
        st.markdown("### ⚡ Trigger Pipeline Execution")
        st.write(
            "Execute a full pipeline cycle immediately from this panel: "
            "**Seed Sync → Live Monitoring → Auto-Approve → Contact Table Sync**.  \n"
            "*(Live email dispatch requires `AUTO_SEND_ENABLED=true` in `.env`)*"
        )
        dry = st.checkbox("Dry Run mode (simulate extraction, no database modifications or outgoing emails)", value=True, key="auto_dry")
        if st.button("🚀 Execute Pipeline Cycle Now", type="primary"):
            import threading
            result_holder = {}

            def _run():
                try:
                    import importlib.util
                    # Import worker as a module
                    spec = importlib.util.spec_from_file_location(
                        "worker_mod",
                        str(Path(__file__).resolve().parent / "worker.py")
                    )
                    w = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(w)
                    result_holder["result"] = w.run_once(verbose=False, dry_run=dry)
                except Exception as exc:
                    result_holder["error"] = str(exc)

            with st.spinner("Executing pipeline tasks…"):
                t = threading.Thread(target=_run)
                t.start()
                t.join(timeout=300)

            if "error" in result_holder:
                st.error(f"Pipeline error: {result_holder['error']}")
            elif "result" in result_holder:
                res = result_holder["result"]
                st.success("Pipeline cycle complete!")
                st.json(res)
            else:
                st.warning("Pipeline timed out or returned no response.")

    # ---- Seed CSV management ----
    with st.container(border=True):
        st.markdown("### 📋 Seed Institution Database")
        seed_path_raw = cfg.seed_csv_path or "data/seed_colleges.csv"
        if not Path(seed_path_raw).is_absolute():
            seed_path = str(Path(__file__).resolve().parent / seed_path_raw)
        else:
            seed_path = seed_path_raw

        if Path(seed_path).exists():
            try:
                seed_df = pd.read_csv(seed_path)
                st.caption(f"{len(seed_df)} institutions catalogued in `{seed_path_raw}`")
                st.dataframe(seed_df, hide_index=True, use_container_width=True)
                st.download_button(
                    "⬇️ Download Seed CSV",
                    seed_df.to_csv(index=False).encode("utf-8-sig"),
                    "seed_colleges.csv",
                    "text/csv",
                    key="dl_seed",
                )
            except Exception as exc:
                st.warning(f"Could not read seed CSV: {exc}")
        else:
            st.info(f"Seed CSV not found at `{seed_path_raw}`. It will be generated on first run.")

        st.markdown("**Upload Updated Seed CSV** (columns: `name`, `website`, `state`, `city`, `institution_type`):")
        uploaded = st.file_uploader("Upload CSV", type=["csv"], key="seed_upload")
        if uploaded is not None:
            try:
                new_df = pd.read_csv(uploaded)
                st.dataframe(new_df.head(10), hide_index=True)
                if st.button("💾 Save Uploaded Seed CSV", key="save_seed", type="primary"):
                    Path(seed_path).parent.mkdir(parents=True, exist_ok=True)
                    new_df.to_csv(seed_path, index=False)
                    st.success(f"Saved {len(new_df)} colleges to `{seed_path_raw}`.")
                    st.rerun()
            except Exception as exc:
                st.error(f"Could not parse CSV: {exc}")

    # ---- Monitored colleges ----
    with st.container(border=True):
        st.markdown("### 🏫 Monitored Institutions")
        try:
            colleges_df = pd.read_sql_query(
                "SELECT id, name, state, city, website, status, last_check_status, "
                "last_checked_at, monitoring_enabled FROM colleges ORDER BY name",
                conn,
            )
            if colleges_df.empty:
                st.info("No colleges tracked yet. Upload colleges to your seed CSV and run the pipeline.")
            else:
                st.caption(f"{len(colleges_df)} tracked institution(s)")
                st.dataframe(colleges_df, hide_index=True, use_container_width=True)
        except Exception:
            st.info("Monitoring schema not initialised yet. Run the pipeline once to initialise.")

    # ---- Bulk approve pending contacts ----
    with st.container(border=True):
        st.markdown("### ✅ Contact Verification & Bulk Approval")
        pending_count = mstats.get("pending_approvals", 0)
        st.write(
            f"**{pending_count}** contact record(s) pending review.  \n"
            "Approve all contacts meeting the confidence threshold, or inspect individually below."
        )
        thr = st.slider(
            "Confidence threshold (contacts scoring below this require manual inspection)",
            min_value=0, max_value=100, value=cfg.auto_approve_threshold, step=5,
            key="bulk_thr",
        )
        dry2 = st.checkbox("Dry run preview", value=True, key="bulk_dry")
        if st.button("⚡ Execute Bulk Approval", key="bulk_approve_btn", type="primary"):
            from shortfundly.auto_approve import auto_approve_pending, sync_approved_to_contacts
            with st.spinner("Scoring and approving contacts…"):
                appr = auto_approve_pending(conn, threshold=thr, dry_run=dry2)
                sync = sync_approved_to_contacts(conn, dry_run=dry2)
            label = "(DRY RUN) " if dry2 else ""
            st.success(
                f"{label}Approved **{appr['approved']}** contact(s), "
                f"skipped **{appr['skipped_low_score']}** (low score), "
                f"synced **{sync['synced']}** to main contacts directory."
            )
            st.rerun()

        try:
            pending_df = pd.read_sql_query(
                "SELECT cr.id, c.name AS college, cr.email, cr.source_url, cr.status, "
                "       c.website "
                "FROM contact_records cr "
                "JOIN colleges c ON cr.college_id = c.id "
                "WHERE cr.status IN ('discovered', 'pending_review') "
                "ORDER BY cr.collected_at DESC LIMIT 100",
                conn,
            )
            if not pending_df.empty:
                from shortfundly.auto_approve import confidence_score
                pending_df["score"] = pending_df.apply(
                    lambda r: confidence_score(r["email"], r["source_url"], r["website"]),
                    axis=1,
                )
                st.caption(f"{len(pending_df)} pending contact(s) shown (max 100)")
                st.dataframe(
                    pending_df[["id", "college", "email", "source_url", "status", "score"]],
                    hide_index=True,
                    use_container_width=True,
                )
        except Exception:
            pass

    # ---- Worker log tail ----
    with st.container(border=True):
        st.markdown("### 📄 Worker Engine Activity Log")
        log_path = Path(__file__).resolve().parent / "data" / "worker.log"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            st.code("\n".join(lines[-50:]), language="")
        else:
            st.info("No worker log found yet. Run the worker process to view live logs.")


# --------------------------------------------------------------------- main
def main() -> None:
    if not require_login():
        return
    cfg = load_config()
    conn = db.connect(cfg.db_path)
    try:
        ts.ensure_default_template(conn)
        sending.recover_stuck_sending(conn, older_than_minutes=60)
        inject_css()
        hero(
            "Shortfundly Campus Outreach Engine",
            "Official Institutional Outreach Platform · Kerala Region · Personalised Dispatch & Verification",
            mode=cfg.send_mode,
            state="Kerala",
            user="Arjumaan",
        )
        sender = render_sidebar(conn, cfg)
        show_flash()
        tabs = st.tabs(["Dashboard", "Contacts", "Templates", "Send", "History", "⚡ Automation"])
        with tabs[0]:
            st.caption("Real-time telemetry and metrics for contacts and deliverability.")
            render_dashboard(conn)
        with tabs[1]:
            st.caption("Manage official college contact records across Kerala and partner states.")
            sub = st.tabs(["Browse & Edit", "Import", "Add Contact", "Verification", "Export"])
            with sub[0]:
                render_browse(conn)
            with sub[1]:
                render_import(conn)
            with sub[2]:
                render_add(conn)
            with sub[3]:
                render_verification(conn)
            with sub[4]:
                render_export(conn)
        with tabs[2]:
            st.caption("Compose, personalise, and maintain multi-variant outreach proposals.")
            render_templates(conn, sender)
        with tabs[3]:
            st.caption("Select recipients, review live personalised previews, attach assets, and dispatch.")
            render_send(conn, cfg, sender)
        with tabs[4]:
            st.caption("Comprehensive delivery logs, error diagnostics, and automated retry system.")
            render_history(conn, cfg)
        with tabs[5]:
            st.caption("Autonomous monitoring engine: continuous discovery, contact scoring, and pipeline controls.")
            render_automation(conn, cfg)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
