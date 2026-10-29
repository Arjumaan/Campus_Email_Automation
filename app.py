"""Campus Outreach Email Automation - Streamlit dashboard.

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

st.set_page_config(page_title="Campus Outreach Email Automation", page_icon="✉️", layout="wide")

VERIFICATION_OPTIONS = ["All", "verified", "unverified"]

# --------------------------------------------------------------- UI / styling


def _logo_html(size_px: int = 56) -> str:
    """Return an SVG logo emblem for Campus Outreach Email Automation."""
    return (
        f'<div class="sf-hero-icon" style="width:{size_px}px; height:{size_px}px; border-radius:16px; '
        f'background:linear-gradient(135deg, rgba(37,99,235,0.24) 0%, rgba(17,24,39,0.95) 100%); '
        f'border:1px solid rgba(59,130,246,0.45); display:flex; align-items:center; justify-content:center; '
        f'box-shadow:0 10px 24px -4px rgba(37,99,235,0.4); color:#3B82F6; flex-shrink:0;">'
        f'<svg width="{int(size_px*0.52)}" height="{int(size_px*0.52)}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M22 17a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9.5C2 7 4 5 6.5 5H17.5C20 5 22 7 22 9.5V17Z"></path>'
        f'<polyline points="22,7 12,13 2,7"></polyline>'
        f'</svg></div>'
    )


_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Material+Icons&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

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
::-webkit-scrollbar-thumb:hover { background: #2563EB; }

/* ---- Animations ---- */
@keyframes sfFadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes sfPulseGlow { 0%, 100% { box-shadow: 0 0 12px rgba(37,99,235,0.25); } 50% { box-shadow: 0 0 26px rgba(59,130,246,0.6); } }
@keyframes sfPulseDot { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.35); opacity: 0.6; } }

/* ---- Modern Executive Hero Header ---- */
.sf-hero {
  border-radius: 18px;
  padding: 20px 26px;
  margin-bottom: 20px;
  color: #fff;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14) 0%, rgba(17, 24, 40, 0.95) 50%, rgba(10, 14, 22, 0.98) 100%);
  border: 1px solid rgba(59, 130, 246, 0.25);
  backdrop-filter: blur(20px);
  box-shadow: 0 16px 40px -8px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(59, 130, 246, 0.12);
  animation: sfFadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}
.sf-hero-row { display: flex; align-items: center; justify-content: space-between; gap: 18px; flex-wrap: wrap; }
.sf-hero-left { display: flex; align-items: center; gap: 16px; }
.sf-hero-text h1 { margin: 0; font-size: 1.85rem; font-weight: 800; letter-spacing: -0.025em; color: #ffffff; }
.sf-hero-text p { margin: 0.25rem 0 0; opacity: 0.88; font-size: 0.92rem; color: #94A3B8; }
.sf-hero-pills { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

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
  background: linear-gradient(155deg, rgba(20, 27, 42, 0.75) 0%, rgba(13, 17, 27, 0.9) 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 14px !important;
  padding: 16px 20px !important;
  box-shadow: 0 10px 28px -4px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
  animation: sfFadeUp 0.5s ease both;
  backdrop-filter: blur(12px) !important;
}
div[data-testid="stMetric"]:hover {
  transform: translateY(-3px) !important;
  border-color: rgba(59, 130, 246, 0.45) !important;
  box-shadow: 0 14px 32px -4px rgba(37, 99, 235, 0.22), inset 0 1px 0 rgba(59, 130, 246, 0.2) !important;
}
div[data-testid="stMetric"] label {
  font-size: 0.78rem !important;
  font-weight: 700 !important;
  color: #94A3B8 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
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
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
  color: #FFFFFF !important;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4) !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {
  display: none !important;
}

/* ---- Buttons ---- */
button[kind="primary"], .stButton > button[type="primary"] {
  background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em !important;
  padding: 0.55rem 1.35rem !important;
  box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35) !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
button[kind="primary"]:hover, .stButton > button[type="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.55) !important;
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
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
  border-color: #2563EB !important;
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
  border-color: #2563EB !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25) !important;
}

/* ---- Glass Containers & Cards ---- */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(160deg, rgba(18, 25, 40, 0.8) 0%, rgba(11, 15, 25, 0.95) 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.07) !important;
  border-radius: 18px !important;
  padding: 24px 26px !important;
  box-shadow: 0 14px 36px -6px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
  backdrop-filter: blur(16px) !important;
  margin-bottom: 20px !important;
  animation: sfFadeUp 0.5s ease both;
}

/* ---- Modern Sidebar Navigation Menu ---- */
[data-testid="stSidebar"] [data-testid="stRadio"] {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  margin-top: 4px !important;
}
/* Hide radio group title / widget label */
[data-testid="stSidebar"] [data-testid="stRadio"] > label,
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stWidgetLabel"] {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
}
/* Hide the radio input and selection indicators */
[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"],
[data-testid="stSidebar"] [data-testid="stRadio"] div[data-testid="stWidgetSelectionIndicator"],
[data-testid="stSidebar"] [data-testid="stRadio"] div[class*="WidgetSelectionIndicator"],
[data-testid="stSidebar"] [data-testid="stRadio"] div[class*="RadioIndicator"] {
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  height: 0 !important;
  opacity: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  position: absolute !important;
  pointer-events: none !important;
}
/* In Streamlit radio labels, Child 1 is the circle, Child 2 is the text wrapper */
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-of-type {
  display: none !important;
  visibility: hidden !important;
  width: 0 !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}
/* Force Child 2 (text container) and markdown container to be fully visible */
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:last-of-type,
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:last-child,
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] {
  display: flex !important;
  align-items: center !important;
  visibility: visible !important;
  opacity: 1 !important;
  width: 100% !important;
  color: inherit !important;
}
/* Style the navigation button */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.06) !important;
  border-radius: 12px !important;
  padding: 10px 14px !important;
  color: #94A3B8 !important;
  font-weight: 600 !important;
  font-size: 0.92rem !important;
  cursor: pointer !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  width: 100% !important;
  box-sizing: border-box !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: rgba(37, 99, 235, 0.09) !important;
  color: #FFFFFF !important;
  border-color: rgba(59, 130, 246, 0.3) !important;
  transform: translateX(3px) !important;
}
/* Active navigation button */
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.22) 0%, rgba(19, 27, 42, 0.95) 100%) !important;
  border: 1px solid rgba(59, 130, 246, 0.5) !important;
  border-left: 4px solid #2563EB !important;
  color: #FFFFFF !important;
  box-shadow: 0 4px 18px -2px rgba(37, 99, 235, 0.35) !important;
  font-weight: 700 !important;
}
/* Force navigation text and emojis to be clearly visible */
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] span {
  display: inline-block !important;
  visibility: visible !important;
  opacity: 1 !important;
  color: inherit !important;
  font-size: 0.92rem !important;
  font-weight: inherit !important;
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1.4 !important;
  white-space: nowrap !important;
  overflow: visible !important;
}

/* ---- Executive KPI Components ---- */
.kpi-card {
  background: linear-gradient(155deg, rgba(20, 28, 44, 0.8) 0%, rgba(12, 17, 27, 0.95) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px 22px;
  box-shadow: 0 10px 30px -4px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
  height: 100%;
}
.kpi-card:hover {
  transform: translateY(-3px);
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 16px 36px -6px rgba(37, 99, 235, 0.2), inset 0 1px 0 rgba(59, 130, 246, 0.25);
}
.kpi-card-glow {
  position: absolute;
  top: 0;
  right: 0;
  width: 80px;
  height: 80px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.15) 0%, transparent 70%);
  pointer-events: none;
}
.kpi-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.kpi-icon-pill {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.kpi-badge {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 3px 10px;
  border-radius: 9999px;
  text-transform: uppercase;
}
.kpi-badge-rose, .kpi-badge-blue { background: rgba(37, 99, 235, 0.15); color: #93C5FD; border: 1px solid rgba(59, 130, 246, 0.35); }
.kpi-badge-emerald { background: rgba(16, 185, 129, 0.15); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.3); }
.kpi-badge-amber { background: rgba(245, 158, 11, 0.15); color: #FCD34D; border: 1px solid rgba(245, 158, 11, 0.3); }
.kpi-badge-purple { background: rgba(168, 85, 247, 0.15); color: #D8B4FE; border: 1px solid rgba(168, 85, 247, 0.3); }
.kpi-value {
  font-size: 2.1rem;
  font-weight: 800;
  color: #FFFFFF;
  letter-spacing: -0.03em;
  line-height: 1.1;
  margin-bottom: 4px;
}
.kpi-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: #E2E8F0;
  margin-bottom: 4px;
}
.kpi-subtext {
  font-size: 0.78rem;
  color: #94A3B8;
  line-height: 1.4;
}

/* ---- Hub Leaderboard Item ---- */
.hub-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  margin-bottom: 8px;
  transition: all 0.2s ease;
}
.hub-item:hover {
  background: rgba(37, 99, 235, 0.08);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateX(2px);
}
.hub-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: #F1F5F9;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hub-badge {
  font-size: 0.8rem;
  font-weight: 700;
  color: #60A5FA;
  background: rgba(37, 99, 235, 0.14);
  padding: 2px 10px;
  border-radius: 9999px;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

/* ---- Assurance Shield Banner ---- */
.assurance-banner {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.09) 0%, rgba(15, 23, 42, 0.95) 100%);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-left: 4px solid #10B981;
  border-radius: 14px;
  padding: 16px 20px;
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.sidebar-spacer {
  height: 18px;
}

/* ---- Sidebar Profile & Widgets ---- */
.sf-profile-card {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12) 0%, rgba(19, 27, 42, 0.8) 100%);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.sf-profile-avatar {
  width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.15rem; font-weight: 800; color: white;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.45);
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
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.22) 0%, rgba(37, 99, 235, 0.05) 100%);
  border: 1px solid rgba(59, 130, 246, 0.4);
  box-shadow: 0 10px 28px -4px rgba(37, 99, 235, 0.35);
  color: #3B82F6;
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
  border-top: 2px solid #2563EB !important;
  border-radius: 20px !important;
  padding: 26px 28px !important;
  box-shadow: 0 20px 48px -12px rgba(0, 0, 0, 0.65), 0 0 1px 1px rgba(255, 255, 255, 0.04) !important;
}
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
def render_sidebar_and_nav(conn, cfg: Config) -> tuple[str, dict]:
    """Render the executive sidebar:
    1. TOP: Platform brand header + main navigation menu (migrated from top bar).
    2. DOWN: Operational controls (Dispatch safeguards, sender profile, user details, sign out).
    """
    with st.sidebar:
        # 1. Top Brand Header
        st.markdown(
            """
            <div style="display:flex; align-items:center; gap:12px; padding:6px 2px 16px 2px; border-bottom:1px solid rgba(255,255,255,0.08); margin-bottom:14px;">
              <div style="width:42px; height:42px; border-radius:12px; background:linear-gradient(135deg, rgba(37,99,235,0.25) 0%, rgba(37,99,235,0.06) 100%); border:1px solid rgba(59,130,246,0.4); display:flex; align-items:center; justify-content:center; color:#3B82F6; box-shadow:0 6px 16px rgba(37,99,235,0.3); flex-shrink:0;">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 17a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9.5C2 7 4 5 6.5 5H17.5C20 5 22 7 22 9.5V17Z"></path>
                  <polyline points="22,7 12,13 2,7"></polyline>
                </svg>
              </div>
              <div style="min-width:0;">
                <div style="font-size:1.02rem; font-weight:800; color:#FFFFFF; letter-spacing:-0.02em; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Campus Outreach</div>
                <div style="font-size:0.75rem; color:#94A3B8; font-weight:500;">Email Automation · Kerala</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("PLATFORM NAVIGATION")
        nav_options = [
            "📊  Dashboard",
            "📇  Contacts Directory",
            "✉️  Email Templates",
            "🚀  Send & Dispatch",
            "📜  Delivery History",
            "⚡  Autonomous Pipeline",
            "📄  Worker Engine Logs",
        ]
        active_page = st.radio(
            "Navigation Menu",
            nav_options,
            label_visibility="collapsed",
            key="_main_nav_radio",
        )

        # 2. DOWN IN SIDEBAR (operational controls migrated downwards)
        st.markdown("<div class='sidebar-spacer'></div>", unsafe_allow_html=True)
        st.divider()

        st.caption("SYSTEM CONTROLS & SAFEGUARDS")

        # Safeguards Expander
        with st.expander("🛡️ Dispatch Safeguards", expanded=False):
            if cfg.send_mode == "live":
                st.error("⚡ **LIVE MODE ENABLED**\n\nReal emails permitted after explicit two-factor typing confirmation.")
            else:
                st.success(
                    f"🛡️ **TEST MODE (Safe)**\n\nEvery email safely intercepted and routed to:\n`{cfg.test_recipient or 'arjumaan21@gmail.com'}`"
                )
            st.caption("SMTP Service: " + ("✅ Configured" if cfg.smtp_configured else "⚠️ Not configured (.env)"))
            if st.button("🔍 Test SMTP Connection", disabled=not cfg.smtp_configured, use_container_width=True, key="side_test_smtp"):
                try:
                    SMTPMailer(cfg).check_connection()
                    st.success("✅ SMTP authenticated successfully.")
                except Exception as exc:  # noqa: BLE001
                    err_msg = str(exc)
                    if hasattr(exc, "smtp_error") and isinstance(exc.smtp_error, bytes):
                        err_msg = exc.smtp_error.decode("utf-8", errors="replace")
                    st.error(cfg.redact(f"❌ {type(exc).__name__}: {err_msg}"))

        # Sender Profile Expander
        current_sender = get_sender(conn, cfg)
        with st.expander("✍️ Sender Profile", expanded=False):
            st.caption("Applied dynamically across `{sender_name}` and `{sender_title}` variables.")
            with st.form("sender_form_down"):
                name = st.text_input("Sender name", value=current_sender["sender_name"])
                title = st.text_input("Sender title", value=current_sender["sender_title"])
                if st.form_submit_button("Save sender details", use_container_width=True):
                    db.set_setting(conn, "sender_name", name.strip() or "Arjumaan")
                    db.set_setting(conn, "sender_title", title.strip())
                    st.success("Sender profile saved.")
                    st.rerun()

        # User Profile Card & Sign out at bottom
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
        if st.button("🚪 Sign out", use_container_width=True, key="side_sign_out"):
            st.session_state.pop("_authenticated", None)
            st.rerun()

        st.markdown(
            """
            <div style="margin-top:10px; padding:10px 12px; border-radius:10px; background:#0B0E14; border:1px solid #1D2638; font-size:0.73rem; color:#64748B;">
              <div><strong>Region:</strong> Kerala (129 Institutions)</div>
              <div><strong>Platform:</strong> Campus Outreach v2.5</div>
              <div><strong>Account:</strong> arjumaan21@gmail.com</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return active_page, current_sender


def _navigate_to(target: str) -> None:
    """Safely navigate to another page via button on_click callback before widget instantiation."""
    st.session_state["_main_nav_radio"] = target


# ---------------------------------------------------------------- dashboard
def render_dashboard(conn) -> None:
    s = stats_mod.get_stats(conn)
    colleges_total = conn.execute("SELECT COUNT(*) FROM colleges").fetchone()[0]
    total_contacts = s["contacts_total"] or 0
    verified_contacts = s["contacts_verified"] or 0
    unverified_contacts = s["contacts_unverified"] or 0
    dup_groups = s["duplicate_college_groups"] or 0
    dup_members = s["duplicate_college_contacts"] or 0
    pct_ver = (verified_contacts / total_contacts * 100) if total_contacts else 0.0

    # 1. Executive Metric Deck (4 distinct glass cards)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-card-glow"></div>
              <div class="kpi-card-top">
                <div class="kpi-icon-pill">🏛️</div>
                <span class="kpi-badge kpi-badge-blue">Kerala Network</span>
              </div>
              <div class="kpi-value">{colleges_total}</div>
              <div class="kpi-title">Discovered Colleges</div>
              <div class="kpi-subtext">Mapped across 14 Kerala revenue districts</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-card-glow"></div>
              <div class="kpi-card-top">
                <div class="kpi-icon-pill">📇</div>
                <span class="kpi-badge kpi-badge-emerald">100% Kerala</span>
              </div>
              <div class="kpi-value">{total_contacts}</div>
              <div class="kpi-title">Direct Outreach Leads</div>
              <div class="kpi-subtext">Verified institutional decision-makers</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-card-glow"></div>
              <div class="kpi-card-top">
                <div class="kpi-icon-pill">🛡️</div>
                <span class="kpi-badge kpi-badge-amber">{pct_ver:.0f}% Verified</span>
              </div>
              <div class="kpi-value">{unverified_contacts}</div>
              <div class="kpi-title">Pending Verification</div>
              <div class="kpi-subtext">Ready for MX sweep & format checks</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f"""
            <div class="kpi-card">
              <div class="kpi-card-glow"></div>
              <div class="kpi-card-top">
                <div class="kpi-icon-pill">👥</div>
                <span class="kpi-badge kpi-badge-purple">{dup_groups} Clusters</span>
              </div>
              <div class="kpi-value">{dup_members}</div>
              <div class="kpi-title">Multi-Stakeholder Contacts</div>
              <div class="kpi-subtext">Colleges with multiple official desks</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 2. Operations Launchpad (Instant Action Tiles)
    with st.container(border=True):
        st.markdown(
            "<div style='font-size:0.95rem; font-weight:700; color:#F8FAFC; margin-bottom:12px; display:flex; align-items:center; gap:8px;'>"
            "<span>⚡ Operations Launchpad</span><span style='font-size:0.75rem; color:#94A3B8; font-weight:500;'>Direct Workflow Shortcuts</span></div>",
            unsafe_allow_html=True,
        )
        q1, q2, q3, q4 = st.columns(4)
        q1.button(
            "🚀  Launch Dispatch Queue",
            use_container_width=True,
            key="dash_q_send",
            on_click=_navigate_to,
            args=("🚀  Send & Dispatch",),
        )
        q2.button(
            "📇  Manage Kerala Contacts",
            use_container_width=True,
            key="dash_q_contacts",
            on_click=_navigate_to,
            args=("📇  Contacts Directory",),
        )
        q3.button(
            "✉️  Review Email Templates",
            use_container_width=True,
            key="dash_q_tmpl",
            on_click=_navigate_to,
            args=("✉️  Email Templates",),
        )
        q4.button(
            "⚡  Autonomous Pipeline",
            use_container_width=True,
            key="dash_q_auto",
            on_click=_navigate_to,
            args=("⚡  Autonomous Pipeline",),
        )

    # 3. Kerala Regional Hubs & Decision-Maker Matrix (2 Columns)
    col_left, col_right = st.columns(2)

    with col_left:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:0.98rem; font-weight:700; color:#FFFFFF; margin-bottom:14px; display:flex; align-items:center; gap:8px;'>"
                "<span>📍 Kerala Regional Educational Hubs</span></div>",
                unsafe_allow_html=True,
            )
            top_cities = conn.execute(
                "SELECT city, COUNT(*) AS n FROM contacts GROUP BY city ORDER BY n DESC LIMIT 6"
            ).fetchall()
            col_city_map = dict(
                conn.execute("SELECT city, COUNT(*) FROM colleges GROUP BY city").fetchall()
            )

            for city_row in top_cities:
                city_name = city_row["city"]
                c_cnt = city_row["n"]
                inst_cnt = col_city_map.get(city_name, 0)
                st.markdown(
                    f"""
                    <div class="hub-item">
                      <div class="hub-title"><span>🏛️</span> {city_name}</div>
                      <div style="display:flex; align-items:center; gap:10px;">
                        <span style="font-size:0.75rem; color:#94A3B8;">{inst_cnt} Institutions</span>
                        <span class="hub-badge">{c_cnt} Direct Leads</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_right:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:0.98rem; font-weight:700; color:#FFFFFF; margin-bottom:14px; display:flex; align-items:center; gap:8px;'>"
                "<span>🎓 Institutional Stakeholders & Desks</span></div>",
                unsafe_allow_html=True,
            )
            dept_counts = conn.execute(
                "SELECT department, COUNT(*) AS n FROM contacts GROUP BY department ORDER BY n DESC LIMIT 6"
            ).fetchall()

            for dept_row in dept_counts:
                dept_name = dept_row["department"] or "General Administration"
                cnt = dept_row["n"]
                st.markdown(
                    f"""
                    <div class="hub-item">
                      <div class="hub-title"><span>👤</span> {dept_name}</div>
                      <span class="kpi-badge kpi-badge-purple">{cnt} Authorities</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # 4. Live Delivery Telemetry Console & Interception Shield
    with st.container(border=True):
        st.markdown(
            "<div style='font-size:0.98rem; font-weight:700; color:#FFFFFF; margin-bottom:14px; display:flex; align-items:center; gap:8px;'>"
            "<span>📡 Email Dispatch Telemetry & Interception Console</span></div>",
            unsafe_allow_html=True,
        )
        e = s["emails_live"]
        t = s["emails_test"]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Pending In Queue", e["pending"])
        c2.metric("In Flight (Sending)", e["sending"])
        c3.metric("Accepted by SMTP", e["sent"])
        c4.metric("Dispatch Failed", e["failed"])
        c5.metric("Total Messages Tracked", e["total"])

        st.markdown(
            """
            <div class="assurance-banner">
              <div style="font-size:1.5rem; flex-shrink:0;">🛡️</div>
              <div style="font-size:0.84rem; color:#E2E8F0; line-height:1.45;">
                <strong>Safe Interception Active:</strong> In Test Mode, every outgoing proposal is safely intercepted and delivered to 
                <code>arjumaan21@gmail.com</code>. <em>'Accepted'</em> confirms explicit SMTP server acknowledgment for relay.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


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
    c1.download_button("⬇️ Download CSV", ct.export_csv(df), "kerala_campus_contacts.csv", "text/csv", key="dl_csv")
    c2.download_button("📊 Download Excel (.xlsx)", ct.export_xlsx(df), "kerala_campus_contacts.xlsx",
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
              <h1 class="login-title">Campus Outreach Email Automation</h1>
              <p class="login-subtitle">Official Institutional Outreach Platform · Kerala Region</p>
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

def render_worker_logs() -> None:
    """Dedicated console for background autonomous worker process logs."""
    log_path = Path(__file__).resolve().parent / "data" / "worker.log"

    with st.container(border=True):
        st.markdown(
            "<div style='font-size:1.15rem; font-weight:800; color:#FFFFFF; margin-bottom:14px; display:flex; align-items:center; gap:10px;'>"
            "<span style='width:36px; height:36px; border-radius:10px; background:rgba(37,99,235,0.15); border:1px solid rgba(59,130,246,0.3); display:inline-flex; align-items:center; justify-content:center; color:#3B82F6;'>📄</span>"
            "<span>Autonomous Worker Engine Activity Console</span></div>",
            unsafe_allow_html=True,
        )

        if not log_path.exists():
            st.info("No worker log file found at `data/worker.log`. Start the worker process to generate live activity telemetry.")
            return

        raw_text = log_path.read_text(encoding="utf-8", errors="replace")
        all_lines = raw_text.splitlines()
        file_size_kb = log_path.stat().st_size / 1024

        # Telemetry metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Log Entries", len(all_lines))
        m2.metric("Log File Size", f"{file_size_kb:.1f} KB")
        info_count = sum(1 for line in all_lines if "[INFO]" in line)
        warn_count = sum(1 for line in all_lines if "[WARNING]" in line or "[ERROR]" in line)
        m3.metric("Information Events", info_count)
        m4.metric("Warnings & Errors", warn_count)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Filter controls
        f1, f2, f3 = st.columns([2, 1, 1])
        filter_keyword = f1.text_input(
            "🔍 Filter keyword",
            placeholder="Search text (e.g. discovery, approve, sync, error)...",
            key="worker_log_search",
        )
        line_count = f2.selectbox("Line limit", [50, 100, 200, 500, "All"], index=0, key="worker_log_lines")
        log_level = f3.selectbox("Event level", ["All", "INFO", "WARNING", "ERROR"], index=0, key="worker_log_level")

        lines_to_display = all_lines
        if log_level != "All":
            lines_to_display = [l for l in lines_to_display if f"[{log_level}]" in l]
        if filter_keyword.strip():
            kw = filter_keyword.strip().lower()
            lines_to_display = [l for l in lines_to_display if kw in l.lower()]

        if line_count != "All" and isinstance(line_count, int):
            lines_to_display = lines_to_display[-line_count:]

        st.caption(f"Displaying {len(lines_to_display)} event line(s) · Tailing `data/worker.log`")

        if lines_to_display:
            st.code("\n".join(lines_to_display), language="log")
        else:
            st.info("No log events match the specified filter criteria.")

        # Quick Actions
        a1, a2 = st.columns([1, 1])
        a1.download_button(
            "⬇️ Download Full Log File (.log)",
            raw_text.encode("utf-8"),
            "worker.log",
            "text/plain",
            use_container_width=True,
            key="dl_worker_log_btn",
        )
        if a2.button("🔄 Refresh Log Stream", use_container_width=True, key="refresh_worker_logs"):
            st.rerun()


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
        active_page, sender = render_sidebar_and_nav(conn, cfg)
        hero(
            "Campus Outreach Email Automation",
            "Official Institutional Outreach Platform · Kerala Region · Personalised Dispatch & Verification",
            mode=cfg.send_mode,
            state="Kerala",
            user="Arjumaan",
        )
        show_flash()

        if "Dashboard" in active_page:
            st.caption("Real-time telemetry and metrics for contacts and deliverability across Kerala.")
            render_dashboard(conn)
        elif "Contacts" in active_page:
            st.caption("Manage official college contact records across Kerala.")
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
        elif "Templates" in active_page:
            st.caption("Compose, personalise, and maintain multi-variant outreach proposals.")
            render_templates(conn, sender)
        elif "Send" in active_page or "Dispatch" in active_page:
            st.caption("Select recipients, review live personalised previews, attach assets, and dispatch.")
            render_send(conn, cfg, sender)
        elif "History" in active_page:
            st.caption("Comprehensive delivery logs, error diagnostics, and automated retry system.")
            render_history(conn, cfg)
        elif "Pipeline" in active_page or "Automation" in active_page:
            st.caption("Autonomous monitoring engine: continuous discovery, contact scoring, and pipeline controls.")
            render_automation(conn, cfg)
        elif "Worker" in active_page or "Logs" in active_page:
            st.caption("Live streaming activity logs, diagnostics, and background worker telemetry.")
            render_worker_logs()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
