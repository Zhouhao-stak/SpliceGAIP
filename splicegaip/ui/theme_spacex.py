"""SpaceX-inspired design theme for SpliceGAIP UI.

Based on the SpaceX design language: pure black canvas, minimal chrome,
austere typography, and full-bleed imagery.
"""

import streamlit as st


def apply_spacex_theme():
    """Apply SpaceX design system to Streamlit app."""

    st.set_page_config(
        page_title="SpliceGAIP",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # SpaceX Design System CSS
    spacex_css = """
    <style>
    /* ===== Global Reset & Base ===== */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    :root {
        /* Colors - Pure Black Canvas */
        --color-primary: #000000;
        --color-ink: #000000;
        --color-on-primary: #ffffff;
        --color-on-primary-mute: #f0f0fa;
        --color-canvas-night: #000000;
        --color-canvas-night-soft: #0a0a0a;
        --color-canvas-light: #ffffff;
        --color-canvas-cool: #f0f0fa;
        --color-hairline-on-dark: #3a3a3f;
        --color-hairline-on-light: #e0e0e8;
        --color-link-on-dark: #ffffff;
        --color-ink-mute: #5a5a5f;

        /* Typography */
        --font-display: "D-DIN-Bold", "Arial Narrow", Arial, Verdana, sans-serif;
        --font-body: "D-DIN", Arial, Verdana, sans-serif;

        /* Spacing */
        --spacing-xxs: 4px;
        --spacing-xs: 8px;
        --spacing-sm: 12px;
        --spacing-md: 16px;
        --spacing-lg: 18px;
        --spacing-xl: 24px;
        --spacing-xxl: 32px;
        --spacing-huge: 48px;

        /* Rounded corners */
        --rounded-xs: 4px;
        --rounded-sm: 8px;
        --rounded-md: 16px;
        --rounded-pill: 32px;
        --rounded-full: 9999px;
    }

    /* ===== Main Background - Pure Black ===== */
    .stApp {
        background: var(--color-canvas-night);
        color: var(--color-on-primary);
    }

    /* ===== Typography - D-DIN Style ===== */
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-display);
        font-weight: 700;
        letter-spacing: 1.2px;
        line-height: 1.2;
        color: var(--color-on-primary);
        text-transform: uppercase;
    }

    h1 {
        font-size: 60px;
        letter-spacing: 1.6px;
    }

    h2 {
        font-size: 48px;
        letter-spacing: 0.96px;
    }

    h3 {
        font-size: 36px;
        letter-spacing: 0.72px;
    }

    p, .stText {
        font-family: var(--font-body);
        font-size: 16px;
        font-weight: 400;
        line-height: 1.7;
        letter-spacing: 0.32px;
        color: var(--color-on-primary-mute);
    }

    /* ===== Buttons - Ghost Pills ===== */
    .stButton > button,
    button[kind="primary"] {
        font-family: var(--font-display);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 1.17px;
        text-transform: uppercase;
        background-color: transparent;
        color: var(--color-on-primary);
        border: 2px solid var(--color-on-primary);
        border-radius: var(--rounded-pill);
        padding: 18px 24px;
        transition: all 0.3s ease;
    }

    .stButton > button:hover,
    button[kind="primary"]:hover {
        background-color: var(--color-on-primary);
        color: var(--color-primary);
    }

    /* ===== Cards - Minimal Dark ===== */
    .css-1r6slb0, .stCard {
        background-color: var(--color-canvas-night-soft);
        border: 1px solid var(--color-hairline-on-dark);
        border-radius: var(--rounded-sm);
    }

    /* ===== Sidebar - Dark Overlay ===== */
    [data-testid="stSidebar"] {
        background-color: var(--color-canvas-night-soft);
        border-right: 1px solid var(--color-hairline-on-dark);
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--color-on-primary);
    }

    /* ===== Input Fields - Dark Theme ===== */
    .stTextInput input,
    .stSelectbox select,
    .stTextArea textarea {
        background-color: var(--color-canvas-night-soft);
        color: var(--color-on-primary);
        border: 1px solid var(--color-hairline-on-dark);
        border-radius: var(--rounded-xs);
    }

    .stTextInput input:focus,
    .stSelectbox select:focus,
    .stTextArea textarea:focus {
        border-color: var(--color-on-primary);
    }

    /* ===== DataFrames/Tables - Dark ===== */
    .stDataFrame, table {
        background-color: var(--color-canvas-night-soft);
        color: var(--color-on-primary);
    }

    th {
        background-color: var(--color-canvas-night);
        color: var(--color-on-primary);
        font-family: var(--font-display);
        text-transform: uppercase;
        letter-spacing: 0.96px;
    }

    td {
        border-bottom: 1px solid var(--color-hairline-on-dark);
    }

    /* ===== Metrics/KPIs - Bold Display ===== */
    [data-testid="stMetricValue"] {
        font-family: var(--font-display);
        font-size: 48px;
        font-weight: 700;
        color: var(--color-on-primary);
    }

    [data-testid="stMetricLabel"] {
        font-family: var(--font-body);
        font-size: 12px;
        letter-spacing: 0.96px;
        text-transform: uppercase;
        color: var(--color-ink-mute);
    }

    /* ===== Progress Bars - Minimal ===== */
    .stProgress > div > div > div > div {
        background-color: var(--color-on-primary);
    }

    /* ===== Tabs - Understated ===== */
    button[data-baseweb="tab"] {
        font-family: var(--font-display);
        text-transform: uppercase;
        letter-spacing: 0.96px;
        color: var(--color-ink-mute);
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--color-on-primary);
        border-bottom: 2px solid var(--color-on-primary);
    }

    /* ===== Expander/Accordion - Ghost Outline ===== */
    .streamlit-expanderHeader {
        background-color: var(--color-canvas-night-soft);
        color: var(--color-on-primary);
        border: 1px solid var(--color-hairline-on-dark);
        border-radius: var(--rounded-sm);
    }

    /* ===== File Uploader - Dark ===== */
    .stFileUploader > div {
        background-color: var(--color-canvas-night-soft);
        border: 2px dashed var(--color-hairline-on-dark);
        border-radius: var(--rounded-sm);
    }

    /* ===== Footer Divider ===== */
    hr {
        border-color: var(--color-hairline-on-dark);
    }

    /* ===== Links ===== */
    a {
        color: var(--color-link-on-dark);
        text-decoration: underline;
    }

    a:hover {
        color: var(--color-on-primary-mute);
    }

    /* ===== Remove Streamlit Branding ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ===== Full-Bleed Hero Section ===== */
    .hero-section {
        background: linear-gradient(180deg, var(--color-canvas-night) 0%, var(--color-canvas-night-soft) 100%);
        padding: var(--spacing-huge) 0;
        text-align: center;
    }

    .hero-title {
        font-size: 80px;
        font-weight: 700;
        letter-spacing: 1.6px;
        line-height: 0.95;
        margin-bottom: var(--spacing-xl);
    }

    .hero-subtitle {
        font-size: 16px;
        letter-spacing: 0.96px;
        text-transform: uppercase;
        color: var(--color-ink-mute);
        line-height: 2.0;
    }

    /* ===== Micro Eyebrow Text ===== */
    .eyebrow {
        font-size: 12px;
        letter-spacing: 0.96px;
        text-transform: uppercase;
        color: var(--color-ink-mute);
        line-height: 2.0;
        margin-bottom: var(--spacing-xs);
    }

    /* ===== Hairline Dividers ===== */
    .hairline {
        height: 1px;
        background-color: var(--color-hairline-on-dark);
        margin: var(--spacing-xxl) 0;
    }
    </style>
    """

    st.markdown(spacex_css, unsafe_allow_html=True)


def hero_section(title: str, subtitle: str = ""):
    """Render a full-bleed hero section."""
    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-title">{title}</div>
        {f'<div class="hero-subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def eyebrow(text: str):
    """Render micro eyebrow text (section label)."""
    st.markdown(f'<div class="eyebrow">{text}</div>', unsafe_allow_html=True)


def hairline():
    """Render a hairline divider."""
    st.markdown('<div class="hairline"></div>', unsafe_allow_html=True)
