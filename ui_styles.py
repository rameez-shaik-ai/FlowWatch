from __future__ import annotations

import streamlit as st


APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

:root {
    --ink: #1e2b22;
    --muted: #5f6d62;
    --line: rgba(30, 43, 34, 0.1);
    --panel: rgba(255, 255, 255, 0.96);
    --accent: #3cc52b;
    --accent-2: #2a9f2f;
    --accent-3: #19311f;
    --glow: rgba(60, 197, 43, 0.14);
    --sidebar-top: #f7f9f4;
    --sidebar-bottom: #eef4eb;
    --page-top: #ffffff;
    --page-bottom: #f5f7f1;
    --hero-top: #4fd22f;
    --hero-bottom: #43c92a;
    --hero-text: #132117;
    --chip-bg: rgba(255, 255, 255, 0.3);
}

@media (prefers-color-scheme: dark) {
    :root {
        --ink: #eef7f0;
        --muted: #c1d2c5;
        --line: rgba(131, 190, 143, 0.18);
        --panel: rgba(10, 27, 30, 0.94);
        --accent: #49d84f;
        --accent-2: #8be48e;
        --accent-3: #eef7f0;
        --glow: rgba(73, 216, 79, 0.18);
        --sidebar-top: #071d31;
        --sidebar-bottom: #0b3150;
        --page-top: #081112;
        --page-bottom: #0d1818;
        --hero-top: #0f4021;
        --hero-bottom: #0d311b;
        --hero-text: #eef7f0;
        --chip-bg: rgba(73, 216, 79, 0.14);
    }
}

html, body, [class*="css"] {
    font-family: "Poppins", "Segoe UI", Arial, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top right, rgba(60, 197, 43, 0.08), transparent 24%),
        radial-gradient(circle at top left, rgba(224, 255, 113, 0.16), transparent 18%),
        linear-gradient(180deg, var(--page-top) 0%, var(--page-bottom) 100%);
}

.block-container {
    padding-top: 1.6rem;
    padding-bottom: 2.4rem;
    max-width: 1240px;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--sidebar-top) 0%, var(--sidebar-bottom) 100%);
    border-right: 1px solid rgba(25, 49, 31, 0.08);
}

[data-testid="stSidebar"] * {
    color: #1f2e23;
}

[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stCheckbox label,
[data-testid="stSidebar"] .stRadio label {
    color: #3f5446;
}

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
[data-testid="stSidebar"] textarea {
    background: rgba(255, 255, 255, 0.88);
    color: #1f2e23;
    border-radius: 14px;
}

.hero-shell {
    background: linear-gradient(135deg, var(--hero-top) 0%, var(--hero-bottom) 100%);
    border: 1px solid rgba(18, 73, 28, 0.08);
    border-radius: 30px;
    padding: 1.35rem 1.45rem 1.4rem 1.45rem;
    box-shadow: 0 22px 60px rgba(57, 111, 41, 0.12);
    position: relative;
    overflow: hidden;
}

.hero-shell::after {
    content: "";
    position: absolute;
    top: -16px;
    right: -10px;
    width: 280px;
    height: 280px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.34), transparent 60%);
}

.hero-kicker {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #204323;
    background: var(--chip-bg);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 999px;
    padding: 0.46rem 0.82rem;
    width: fit-content;
}

.hero-title {
    font-size: 2.9rem;
    line-height: 0.98;
    font-weight: 800;
    margin: 0.85rem 0 0.6rem 0;
    color: var(--hero-text);
}

.hero-copy {
    color: rgba(19, 33, 23, 0.82);
    font-size: 1.02rem;
    line-height: 1.65;
    max-width: 58rem;
    margin: 0;
}

.flow-line {
    display: flex;
    flex-wrap: wrap;
    gap: 0.7rem;
    margin-top: 1.05rem;
}

.flow-pill,
.status-chip {
    border-radius: 999px;
    padding: 0.48rem 0.85rem;
    font-size: 0.84rem;
    font-weight: 800;
}

.flow-pill {
    background: rgba(255, 255, 255, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.32);
    color: #16321d;
}

.status-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.62rem;
    margin-top: 0.72rem;
}

.status-chip.ready {
    color: #0f6f2d;
    background: rgba(244, 255, 145, 0.96);
}

.status-chip.warn {
    color: #845300;
    background: rgba(255, 211, 88, 0.9);
}

.status-chip.band {
    color: #17331c;
    background: rgba(255, 255, 255, 0.82);
}

.command-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 1rem 1.05rem;
    box-shadow: 0 12px 34px rgba(30, 43, 34, 0.05);
    height: 100%;
}

.command-card h4 {
    margin: 0 0 0.42rem 0;
    color: var(--ink);
    font-size: 1rem;
    font-weight: 800;
}

.command-card p {
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
    font-size: 0.92rem;
}

.agent-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 0.86rem;
    box-shadow: 0 12px 34px rgba(30, 43, 34, 0.05);
    position: relative;
    overflow: hidden;
    min-height: 158px;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.agent-card::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 4px;
    background: linear-gradient(90deg, var(--accent-2), var(--accent));
}

.agent-card.active {
    border-color: rgba(49, 196, 47, 0.4);
    box-shadow: 0 0 0 1px rgba(49, 196, 47, 0.16), 0 14px 36px var(--glow);
    animation: agentPulse 1.1s ease-in-out infinite;
}

.agent-card.done {
    border-color: rgba(23, 129, 58, 0.2);
}

.agent-card.waiting {
    opacity: 0.96;
}

.agent-head {
    display: flex;
    align-items: flex-start;
    gap: 0.72rem;
    margin-bottom: 0.38rem;
}

.agent-icon {
    width: 42px;
    height: 42px;
    border-radius: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.05rem;
    background: linear-gradient(135deg, rgba(60, 197, 43, 0.12), rgba(30, 43, 34, 0.07));
    color: var(--accent-3);
    flex: 0 0 auto;
}

.agent-state {
    min-width: 0;
    flex: 1;
}

.agent-name {
    font-size: 0.95rem;
    font-weight: 800;
    color: var(--ink);
    margin: 0;
    line-height: 1.2;
}

.agent-role {
    margin: 0.14rem 0 0 0;
    color: var(--muted);
    font-size: 0.74rem;
    line-height: 1.25;
}

.agent-message {
    color: var(--muted);
    font-size: 0.7rem;
    line-height: 1.38;
    margin-top: 0.3rem;
    min-height: 2rem;
    max-height: 2.9rem;
    overflow: hidden;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
}

.agent-badge {
    border-radius: 999px;
    padding: 0.2rem 0.56rem;
    font-size: 0.7rem;
    font-weight: 800;
    white-space: nowrap;
}

.agent-badge.active {
    background: rgba(49, 196, 47, 0.15);
    color: #0e7731;
}

.agent-badge.done {
    background: rgba(49, 196, 47, 0.12);
    color: #0f6f2d;
}

.agent-badge.waiting {
    background: rgba(79, 101, 125, 0.12);
    color: #556c86;
}

.agent-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: auto;
    padding-top: 0.55rem;
}

.agent-led {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #a2b3c1;
}

.agent-led.active {
    background: var(--accent);
    box-shadow: 0 0 0 8px rgba(49, 196, 47, 0.13);
    animation: ledBlink 0.9s ease-in-out infinite;
}

.agent-led.done {
    background: var(--accent-2);
}

.agent-led.waiting {
    background: #aab8c6;
}

.kpi-pill {
    padding: 0.58rem 0.8rem;
    border-radius: 16px;
    background: rgba(60, 197, 43, 0.08);
    border: 1px solid rgba(60, 197, 43, 0.12);
    margin-bottom: 0.6rem;
}

.kpi-pill strong {
    display: block;
    font-size: 1rem;
    color: var(--ink);
}

.kpi-pill span {
    font-size: 0.79rem;
    color: var(--muted);
}

@keyframes agentPulse {
    0% { transform: translateY(0); box-shadow: 0 0 0 0 rgba(49, 196, 47, 0.14), 0 12px 34px rgba(22, 50, 79, 0.04); }
    50% { transform: translateY(-2px); box-shadow: 0 0 0 8px rgba(49, 196, 47, 0.08), 0 16px 40px rgba(22, 50, 79, 0.06); }
    100% { transform: translateY(0); box-shadow: 0 0 0 0 rgba(49, 196, 47, 0.14), 0 12px 34px rgba(22, 50, 79, 0.04); }
}

@keyframes ledBlink {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.55; transform: scale(1.15); }
}

[data-testid="stMetric"] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 0.66rem 0.9rem;
    box-shadow: 0 10px 28px rgba(22, 50, 79, 0.04);
}

[data-testid="stMetricLabel"] {
    color: var(--muted);
    font-weight: 700;
}

[data-testid="stMetricValue"] {
    color: var(--ink);
}

.section-title {
    font-size: 1.08rem;
    font-weight: 800;
    color: var(--ink);
    margin-bottom: 0.42rem;
}

.compact-note {
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.5;
    margin-bottom: 0.55rem;
}

.stButton > button {
    background: linear-gradient(90deg, #309f2a 0%, #56d930 100%);
    border: none;
    color: #142017;
    font-weight: 800;
    border-radius: 16px;
    padding: 0.82rem 1rem;
    box-shadow: 0 12px 26px rgba(60, 197, 43, 0.2);
}

.stButton > button:hover {
    background: linear-gradient(90deg, #258c25 0%, #47c92a 100%);
}

@media (prefers-color-scheme: dark) {
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar-top) 0%, var(--sidebar-bottom) 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    [data-testid="stSidebar"] * {
        color: #eef7f0;
    }

    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stNumberInput label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stRadio label {
        color: #c1d2c5;
    }

    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stNumberInput input,
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
    [data-testid="stSidebar"] textarea {
        background: rgba(9, 22, 24, 0.88);
        color: #eef7f0;
    }

    .hero-shell,
    .command-card,
    .agent-card,
    [data-testid="stMetric"],
    [data-testid="stExpander"],
    [data-testid="stHorizontalBlock"] > div > [data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
        background: linear-gradient(180deg, rgba(10, 27, 30, 0.96) 0%, rgba(8, 20, 22, 0.95) 100%) !important;
        border-color: var(--line) !important;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.24) !important;
    }

    .kpi-pill {
        background: rgba(73, 216, 79, 0.1);
        border-color: rgba(73, 216, 79, 0.14);
    }

    .kpi-pill span,
    .agent-role,
    .agent-message,
    .command-card p,
    [data-testid="stMetricLabel"],
    .stCaption,
    .stMarkdown p,
    .stText,
    .stWrite {
        color: var(--muted) !important;
    }

    .agent-name,
    .command-card h4,
    .section-title,
    [data-testid="stMetricValue"] {
        color: var(--ink) !important;
    }

    .hero-title,
    .hero-kicker,
    .hero-copy,
    .flow-pill {
        color: var(--hero-text) !important;
    }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
