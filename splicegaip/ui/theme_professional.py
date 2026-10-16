"""Professional minimalist theme for SpliceGAIP.

Clean, restrained design inspired by SpaceX's austere aesthetic:
- Pure black/white palette (no colors)
- System fonts only
- Minimal chrome
- Generous whitespace
- Focus on data and content
"""

import streamlit as st


def apply_professional_theme():
    """Apply professional minimalist design system."""

    st.set_page_config(
        page_title="SpliceGAIP",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Professional Design System - Restrained & Clean
    professional_css = """
    <style>
    /* ===== Base Reset ===== */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    :root {
        /* Monochrome Palette - Professional Only */
        --black: #000000;
        --gray-900: #1a1a1a;
        --gray-700: #4a4a4a;
        --gray-500: #8a8a8a;
        --gray-300: #d0d0d0;
        --gray-100: #f5f5f5;
        --white: #ffffff;

        /* Typography - System Fonts */
        --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        --font-mono: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace;

        /* Spacing Scale */
        --space-1: 4px;
        --space-2: 8px;
        --space-3: 12px;
        --space-4: 16px;
        --space-5: 24px;
        --space-6: 32px;
        --space-7: 48px;
        --space-8: 64px;
    }

    /* ===== Background & Text ===== */
    .stApp {
        background-color: var(--white);
        color: var(--gray-900);
    }

    body {
        font-family: var(--font-sans);
        font-size: 15px;
        line-height: 1.6;
        color: var(--gray-900);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* ===== Headings - Clean Hierarchy ===== */
    h1 {
        font-size: 32px;
        font-weight: 600;
        letter-spacing: -0.5px;
        line-height: 1.2;
        color: var(--black);
        margin-bottom: var(--space-4);
    }

    h2 {
        font-size: 24px;
        font-weight: 600;
        letter-spacing: -0.3px;
        line-height: 1.3;
        color: var(--gray-900);
        margin-top: var(--space-6);
        margin-bottom: var(--space-3);
    }

    h3 {
        font-size: 18px;
        font-weight: 600;
        line-height: 1.4;
        color: var(--gray-900);
        margin-top: var(--space-5);
        margin-bottom: var(--space-2);
    }

    p {
        margin-bottom: var(--space-3);
        color: var(--gray-700);
    }

    /* ===== Buttons - Subtle & Functional ===== */
    .stButton > button {
        font-size: 14px;
        font-weight: 500;
        padding: 10px 20px;
        border-radius: 4px;
        transition: all 0.2s ease;
    }

    /* Primary button */
    button[kind="primary"] {
        background-color: var(--black);
        color: var(--white);
        border: 1px solid var(--black);
    }

    button[kind="primary"]:hover {
        background-color: var(--gray-900);
        border-color: var(--gray-900);
    }

    /* Secondary button */
    button[kind="secondary"] {
        background-color: transparent;
        color: var(--gray-900);
        border: 1px solid var(--gray-300);
    }

    button[kind="secondary"]:hover {
        border-color: var(--gray-700);
    }

    /* ===== Cards - Minimal Borders ===== */
    .css-1r6slb0, .stCard {
        background-color: var(--white);
        border: 1px solid var(--gray-100);
        border-radius: 6px;
        padding: var(--space-4);
    }

    /* ===== Sidebar - Light & Unobtrusive ===== */
    [data-testid="stSidebar"] {
        background-color: var(--gray-100);
        border-right: 1px solid var(--gray-300);
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        justify-content: flex-start;
    }

    /* ===== Input Fields - Clean Forms ===== */
    .stTextInput input,
    .stSelectbox select,
    .stTextArea textarea,
    .stNumberInput input {
        font-size: 14px;
        padding: 8px 12px;
        background-color: var(--white);
        border: 1px solid var(--gray-300);
        border-radius: 4px;
        color: var(--gray-900);
    }

    .stTextInput input:focus,
    .stSelectbox select:focus,
    .stTextArea textarea:focus {
        border-color: var(--gray-700);
        outline: none;
        box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.05);
    }

    /* ===== Data Tables - Professional Grid ===== */
    .stDataFrame {
        border: 1px solid var(--gray-100);
        border-radius: 4px;
    }

    table {
        font-size: 13px;
        border-collapse: collapse;
    }

    th {
        background-color: var(--gray-100);
        color: var(--gray-900);
        font-weight: 600;
        text-align: left;
        padding: 10px 12px;
        border-bottom: 2px solid var(--gray-300);
    }

    td {
        padding: 8px 12px;
        border-bottom: 1px solid var(--gray-100);
        color: var(--gray-700);
    }

    tr:hover {
        background-color: var(--gray-100);
    }

    /* ===== Metrics - Clear Numbers ===== */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 600;
        color: var(--black);
    }

    [data-testid="stMetricLabel"] {
        font-size: 12px;
        font-weight: 500;
        color: var(--gray-500);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ===== Code Blocks - Developer Friendly ===== */
    code, pre {
        font-family: var(--font-mono);
        font-size: 13px;
        background-color: var(--gray-100);
        border-radius: 4px;
    }

    /* ===== Tabs - Understated ===== */
    button[data-baseweb="tab"] {
        font-size: 14px;
        font-weight: 500;
        color: var(--gray-500);
        padding: 8px 16px;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--black);
        border-bottom: 2px solid var(--black);
    }

    /* ===== Progress Bars - Minimal ===== */
    .stProgress > div > div > div > div {
        background-color: var(--gray-900);
    }

    /* ===== File Uploader - Simple ===== */
    .stFileUploader > div {
        border: 2px dashed var(--gray-300);
        border-radius: 4px;
        padding: var(--space-5);
    }

    /* ===== Expander - Clean Accordion ===== */
    .streamlit-expanderHeader {
        font-size: 14px;
        font-weight: 500;
        color: var(--gray-900);
        background-color: var(--gray-100);
        border: 1px solid var(--gray-300);
        border-radius: 4px;
        padding: 12px 16px;
    }

    /* ===== Dividers - Hairline ===== */
    hr {
        border: none;
        border-top: 1px solid var(--gray-100);
        margin: var(--space-6) 0;
    }

    /* ===== Links - Subtle ===== */
    a {
        color: var(--gray-900);
        text-decoration: underline;
        text-underline-offset: 2px;
    }

    a:hover {
        color: var(--black);
    }

    /* ===== Hide Streamlit Branding ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ===== Layout Utilities ===== */
    .section-header {
        margin-bottom: var(--space-5);
        padding-bottom: var(--space-3);
        border-bottom: 1px solid var(--gray-100);
    }

    .muted {
        color: var(--gray-500);
        font-size: 13px;
    }

    .mono {
        font-family: var(--font-mono);
        font-size: 13px;
    }

    /* ===== White Space Management ===== */
    .stVerticalBlock > div {
        margin-bottom: var(--space-4);
    }

    /* Container max-width for readability */
    .block-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: var(--space-5) var(--space-6);
    }
    </style>
    """

    st.markdown(professional_css, unsafe_allow_html=True)


def section_header(title: str, subtitle: str = ""):
    """Render a clean section header with optional subtitle."""
    html = f'<div class="section-header"><h2>{title}</h2>'
    if subtitle:
        html += f'<p class="muted">{subtitle}</p>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def muted(text: str):
    """Render muted/subdued text."""
    st.markdown(f'<p class="muted">{text}</p>', unsafe_allow_html=True)


def mono(text: str):
    """Render monospace text (for IDs, code, etc.)."""
    st.markdown(f'<span class="mono">{text}</span>', unsafe_allow_html=True)
