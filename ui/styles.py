from __future__ import annotations

import streamlit as st


APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --background: #F7FAF8;
    --surface: #FFFFFF;
    --surface2: #F0FDF4;
    --border: #D6EADF;
    --primary: #16A34A;
    --primary-soft: rgba(22, 163, 74, 0.10);
    --text: #0F172A;
    --muted: #64748B;
    --warning: #D97706;
    --critical: #DC2626;
    --blue: #0284C7;
    --purple: #7C3AED;
    --shadow: 0 18px 36px rgba(15, 23, 42, 0.06);
}

@media (prefers-color-scheme: dark) {
    :root {
        --background: #07130D;
        --surface: #0E1F16;
        --surface2: #12291D;
        --border: rgba(74, 222, 128, 0.18);
        --primary: #22C55E;
        --primary-soft: rgba(34, 197, 94, 0.14);
        --text: #F8FAFC;
        --muted: #A7F3D0;
        --warning: #F59E0B;
        --critical: #EF4444;
        --blue: #38BDF8;
        --purple: #A78BFA;
        --shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
    }
}

html, body, [class*="css"] {
    font-family: "Inter", "Segoe UI", Roboto, Arial, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.08), transparent 24%),
        linear-gradient(180deg, var(--background) 0%, color-mix(in srgb, var(--background) 80%, black 20%) 100%);
}

.block-container {
    max-width: 1260px;
    padding-top: 1.15rem;
    padding-bottom: 2rem;
}

[data-testid="stSidebar"] {
    background: color-mix(in srgb, var(--surface) 72%, #0A1A12 28%);
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] * {
    color: var(--text);
}

[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stCheckbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--text) !important;
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p {
    font-size: 0.88rem !important;
}

[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
[data-testid="stSidebar"] textarea {
    background: color-mix(in srgb, var(--surface) 92%, transparent);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 12px;
}

[data-testid="stSidebar"] .stRadio > div {
    gap: 0.2rem;
}

[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: transparent !important;
    border: 1px solid var(--border);
    border-radius: 16px;
}

.compact-header {
    background: linear-gradient(180deg, color-mix(in srgb, var(--surface2) 70%, transparent), color-mix(in srgb, var(--surface) 95%, transparent));
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 0.95rem 1.1rem 1rem 1.1rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}

.header-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--primary-soft);
    color: var(--primary);
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.header-main {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 1rem;
    margin-top: 0.75rem;
}

.header-main h1 {
    margin: 0;
    color: var(--text);
    font-size: clamp(2.2rem, 4vw, 2.6rem);
    line-height: 1;
    font-weight: 800;
}

.header-main p {
    margin: 0.35rem 0 0 0;
    color: var(--muted);
    font-size: 0.95rem;
    line-height: 1.45;
}

.header-chip-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.5rem;
}

.status-chip-ui {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.42rem 0.74rem;
    font-size: 0.78rem;
    font-weight: 700;
    border: 1px solid transparent;
    white-space: nowrap;
}

.status-chip-ui.success {
    background: var(--primary-soft);
    color: var(--primary);
    border-color: var(--border);
}

.status-chip-ui.warning {
    background: color-mix(in srgb, var(--warning) 14%, transparent);
    color: var(--warning);
    border-color: color-mix(in srgb, var(--warning) 30%, transparent);
}

.status-chip-ui.info {
    background: color-mix(in srgb, var(--blue) 14%, transparent);
    color: var(--blue);
    border-color: color-mix(in srgb, var(--blue) 30%, transparent);
}

.status-chip-ui.neutral {
    background: color-mix(in srgb, var(--surface2) 70%, transparent);
    color: var(--muted);
    border-color: var(--border);
}

.status-chip-ui.critical {
    background: color-mix(in srgb, var(--critical) 14%, transparent);
    color: var(--critical);
    border-color: color-mix(in srgb, var(--critical) 30%, transparent);
}

.summary-card, .empty-state-card, [data-testid="stVerticalBlock"] > div[data-testid="stContainer"],
[data-testid="stMetric"], [data-testid="stExpander"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    box-shadow: var(--shadow);
}

.summary-card {
    padding: 1rem 1.05rem;
    min-height: 182px;
}

.summary-eyebrow {
    margin: 0 0 0.7rem 0;
    font-size: 0.76rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 700;
}

.incident-score {
    font-size: 2.25rem;
    line-height: 1;
    font-weight: 800;
    color: var(--text);
    margin-bottom: 0.5rem;
}

.incident-status-row {
    margin-bottom: 0.7rem;
}

.incident-meta {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    color: var(--muted);
    font-size: 0.88rem;
}

.incident-card.good {
    background: linear-gradient(180deg, color-mix(in srgb, var(--primary-soft) 45%, var(--surface) 55%), var(--surface));
}

.incident-card.warning {
    background: linear-gradient(180deg, color-mix(in srgb, var(--warning) 10%, var(--surface) 90%), var(--surface));
}

.incident-card.poor {
    background: linear-gradient(180deg, color-mix(in srgb, var(--critical) 10%, var(--surface) 90%), var(--surface));
}

.workflow-card {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.workflow-stepper {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    width: 100%;
    flex-wrap: nowrap;
    margin-top: auto;
}

.workflow-step {
    display: flex;
    align-items: center;
    flex: 1;
    min-width: 0;
    min-width: 120px;
    border: 1px solid rgba(74, 222, 128, 0.22);
    border-radius: 16px;
    padding: 0.85rem 0.9rem;
    background: rgba(14, 31, 22, 0.82);
    overflow: hidden;
}

.workflow-step-inner {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    min-width: 0;
}

.workflow-icon {
    width: 36px;
    height: 36px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.25);
    flex-shrink: 0;
}

.workflow-copy {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1;
}

.workflow-label {
    color: var(--text);
    font-size: 0.95rem;
    font-weight: 800;
    white-space: nowrap;
    word-break: keep-all;
    overflow-wrap: normal;
}

.workflow-status {
    color: var(--muted);
    font-size: 0.78rem;
    margin-top: 0.2rem;
    white-space: nowrap;
}

.workflow-step.waiting {
    opacity: 0.75;
}

.workflow-step.active {
    border-color: rgba(34, 197, 94, 0.75);
    box-shadow:
        0 0 0 1px rgba(34, 197, 94, 0.22),
        0 16px 40px rgba(34, 197, 94, 0.12);
}

.workflow-step.done {
    border-color: rgba(34, 197, 94, 0.55);
    background: rgba(22, 101, 52, 0.22);
}

.workflow-step.done .workflow-icon,
.workflow-step.active .workflow-icon {
    background: rgba(34, 197, 94, 0.18);
    border-color: rgba(34, 197, 94, 0.4);
}

.flow-connector {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 36px;
    color: var(--primary);
    opacity: 0.45;
    font-size: 1.4rem;
    flex: 0 0 36px;
    align-self: center;
}

.flow-connector.active {
    opacity: 0.8;
    animation: pulseArrow 1.4s ease-in-out infinite;
}

@keyframes pulseArrow {
    0%, 100% {
        opacity: 0.45;
        transform: translateX(0);
    }
    50% {
        opacity: 1;
        transform: translateX(3px);
    }
}

.action-card h3 {
    margin: 0;
    color: var(--text);
    font-size: 1.15rem;
}

.action-card p {
    margin: 0.6rem 0 0.8rem 0;
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.55;
}

.action-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}

.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 0.9rem 0.95rem;
    box-shadow: var(--shadow);
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.kpi-label {
    margin: 0 0 0.55rem 0;
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 600;
}

.kpi-value {
    color: var(--text);
    font-size: clamp(1.55rem, 2.2vw, 1.95rem);
    line-height: 1.1;
    font-weight: 800;
    word-break: break-word;
}

.kpi-card.good {
    border-color: color-mix(in srgb, var(--primary) 32%, var(--border) 68%);
}

.kpi-card.warn {
    border-color: color-mix(in srgb, var(--warning) 40%, var(--border) 60%);
}

.kpi-card.poor {
    border-color: color-mix(in srgb, var(--critical) 42%, var(--border) 58%);
}

.empty-state-card {
    padding: 1.2rem 1.2rem;
    margin-top: 1rem;
}

.empty-state-card h3 {
    margin: 0 0 0.45rem 0;
    color: var(--text);
    font-size: 1.25rem;
}

.empty-state-card p {
    margin: 0;
    color: var(--muted);
    font-size: 0.94rem;
    line-height: 1.55;
}

[data-testid="stButton"] > button {
    background: linear-gradient(135deg, var(--primary) 0%, color-mix(in srgb, var(--primary) 78%, white 22%) 100%);
    border: 1px solid transparent;
    color: #ffffff;
    font-weight: 700;
    border-radius: 16px;
    padding: 0.52rem 0.95rem;
    min-height: 2.45rem;
    box-shadow: 0 10px 22px color-mix(in srgb, var(--primary) 24%, transparent);
    font-size: 0.92rem;
}

[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, color-mix(in srgb, var(--primary) 90%, black 10%) 0%, var(--primary) 100%);
}

[data-testid="stSidebar"] [data-testid="stButton"] > button {
    background: color-mix(in srgb, var(--surface2) 72%, transparent);
    border: 1px solid var(--border);
    color: var(--text);
    box-shadow: none;
    min-height: 2.5rem;
    font-size: 0.82rem;
    padding: 0.45rem 0.55rem;
}

[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: color-mix(in srgb, var(--surface2) 86%, transparent);
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.4rem;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
    background: color-mix(in srgb, var(--surface2) 70%, transparent);
    border: 1px solid var(--border);
    border-radius: 12px 12px 0 0;
    color: var(--muted);
    padding: 0.55rem 0.85rem;
}

[data-testid="stTabs"] [aria-selected="true"] {
    color: var(--text) !important;
    border-bottom-color: transparent !important;
}

[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
    padding: 1rem 1.05rem;
}

[data-testid="stTabs"] {
    margin-top: 1rem;
}

.result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    box-shadow: var(--shadow);
    padding: 1rem 1.05rem;
}

.result-card h3 {
    margin-top: 0;
    margin-bottom: 0.8rem;
    color: var(--text);
    font-size: 1.1rem;
}

.result-copy {
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.55;
}

.result-copy strong,
.result-copy b,
.result-copy h1,
.result-copy h2,
.result-copy h3,
.result-copy h4 {
    color: var(--text);
}

[data-testid="stExpander"] {
    overflow: hidden;
}

[data-testid="stHorizontalBlock"] {
    align-items: stretch;
}

[data-testid="column"] > div {
    height: 100%;
}

@media (max-width: 980px) {
    .header-main {
        flex-direction: column;
        align-items: flex-start;
    }

    .header-chip-row {
        justify-content: flex-start;
    }

    .workflow-stepper {
        flex-wrap: wrap;
    }

    .flow-connector {
        display: none;
    }

    .workflow-step {
        min-width: 180px;
    }
}

@media (max-width: 1100px) {
    .workflow-stepper {
        flex-wrap: wrap;
    }

    .flow-connector {
        display: none;
    }

    .workflow-step {
        min-width: 180px;
    }
}
</style>
"""


def apply_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
