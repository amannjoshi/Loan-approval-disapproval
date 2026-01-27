"""
XAI Dashboard for Loan Approval - Professional Banking Interface
================================================================
Enterprise-grade loan assessment system with transparent AI decisions.

Author: Loan Analytics Team  
Version: 3.0.0
Last Updated: January 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_generator import generate_synthetic_data, INDIAN_CITIES, LOAN_PURPOSES
from models.loan_model import LoanApprovalModel, generate_human_explanation
from utils.fairness_analyzer import (
    FairnessAnalyzer, create_age_groups, create_income_groups,
    generate_fairness_summary_text
)

# ═══════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="LoanWise Pro | Smart Lending Platform",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════
# PROFESSIONAL CSS STYLING
# ═══════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* ═══════════════════════════════════════════════════════════════
       ROOT VARIABLES & THEME
       ═══════════════════════════════════════════════════════════════ */
    :root {
        --primary-blue: #0052CC;
        --primary-dark: #003D99;
        --secondary-blue: #4C9AFF;
        --accent-gold: #FFAB00;
        --success-green: #36B37E;
        --success-light: #E3FCEF;
        --error-red: #DE350B;
        --error-light: #FFEBE6;
        --warning-orange: #FF8B00;
        --warning-light: #FFF4E5;
        --neutral-900: #091E42;
        --neutral-700: #253858;
        --neutral-500: #5E6C84;
        --neutral-300: #B3BAC5;
        --neutral-100: #F4F5F7;
        --neutral-50: #FAFBFC;
        --white: #FFFFFF;
        --shadow-sm: 0 1px 2px rgba(9, 30, 66, 0.08);
        --shadow-md: 0 4px 8px rgba(9, 30, 66, 0.08), 0 2px 4px rgba(9, 30, 66, 0.04);
        --shadow-lg: 0 8px 16px rgba(9, 30, 66, 0.1), 0 4px 8px rgba(9, 30, 66, 0.08);
        --shadow-xl: 0 12px 24px rgba(9, 30, 66, 0.15), 0 8px 16px rgba(9, 30, 66, 0.1);
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 16px;
        --radius-xl: 24px;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       GLOBAL STYLES
       ═══════════════════════════════════════════════════════════════ */
    .main {
        background: linear-gradient(180deg, #F8FAFC 0%, #EEF2F7 100%);
        padding: 0;
    }
    
    .block-container {
        padding: 2rem 3rem 3rem 3rem;
        max-width: 1400px;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* ═══════════════════════════════════════════════════════════════
       TYPOGRAPHY
       ═══════════════════════════════════════════════════════════════ */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--neutral-900);
        font-weight: 600;
    }
    
    p, span, div {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       HEADER BANNER
       ═══════════════════════════════════════════════════════════════ */
    .header-banner {
        background: linear-gradient(135deg, #0052CC 0%, #003D99 50%, #172B4D 100%);
        margin: -2rem -3rem 2rem -3rem;
        padding: 2rem 3rem;
        border-radius: 0 0 24px 24px;
        box-shadow: var(--shadow-lg);
        position: relative;
        overflow: hidden;
    }
    
    .header-banner::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 400px;
        height: 100%;
        background: url("data:image/svg+xml,%3Csvg width='400' height='200' viewBox='0 0 400 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0,100 Q100,0 200,100 T400,100' fill='none' stroke='rgba(255,255,255,0.1)' stroke-width='2'/%3E%3Cpath d='M0,150 Q100,50 200,150 T400,150' fill='none' stroke='rgba(255,255,255,0.08)' stroke-width='2'/%3E%3Ccircle cx='350' cy='50' r='80' fill='rgba(255,255,255,0.03)'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: right center;
    }
    
    .header-logo {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 8px;
    }
    
    .header-logo-icon {
        width: 52px;
        height: 52px;
        background: linear-gradient(135deg, #FFAB00 0%, #FF8B00 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        box-shadow: 0 4px 12px rgba(255, 171, 0, 0.3);
    }
    
    .header-title {
        color: white;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .header-subtitle {
        color: rgba(255, 255, 255, 0.85);
        font-size: 1.05rem;
        margin: 4px 0 0 0;
        font-weight: 400;
    }
    
    .header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        padding: 6px 14px;
        border-radius: 20px;
        color: white;
        font-size: 0.8rem;
        margin-top: 16px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       SIDEBAR STYLING
       ═══════════════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border-right: 1px solid #E1E5EB;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }
    
    .sidebar-header {
        text-align: center;
        padding: 1rem 1.5rem 1.5rem;
        border-bottom: 1px solid #E1E5EB;
        margin-bottom: 1rem;
    }
    
    .sidebar-logo {
        width: 64px;
        height: 64px;
        background: linear-gradient(135deg, #0052CC 0%, #003D99 100%);
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 12px;
        font-size: 32px;
        box-shadow: var(--shadow-md);
    }
    
    .sidebar-brand {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--neutral-900);
        margin: 0;
    }
    
    .sidebar-tagline {
        font-size: 0.85rem;
        color: var(--neutral-500);
        margin: 4px 0 0 0;
    }
    
    /* Sidebar Stats */
    .sidebar-stats {
        background: linear-gradient(135deg, #F8FAFC 0%, #EEF2F7 100%);
        border-radius: 12px;
        padding: 16px;
        margin: 1rem;
        border: 1px solid #E1E5EB;
    }
    
    .stat-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #E1E5EB;
    }
    
    .stat-item:last-child {
        border-bottom: none;
    }
    
    .stat-label {
        font-size: 0.85rem;
        color: var(--neutral-500);
    }
    
    .stat-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--neutral-900);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       CARDS & CONTAINERS
       ═══════════════════════════════════════════════════════════════ */
    .card {
        background: white;
        border-radius: var(--radius-lg);
        padding: 24px;
        box-shadow: var(--shadow-md);
        border: 1px solid rgba(0, 0, 0, 0.04);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .card:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-2px);
    }
    
    .card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--neutral-100);
    }
    
    .card-icon {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }
    
    .card-icon.blue { background: #E6F0FF; color: var(--primary-blue); }
    .card-icon.green { background: var(--success-light); color: var(--success-green); }
    .card-icon.orange { background: var(--warning-light); color: var(--warning-orange); }
    .card-icon.red { background: var(--error-light); color: var(--error-red); }
    
    .card-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: var(--neutral-900);
        margin: 0;
    }
    
    .card-subtitle {
        font-size: 0.85rem;
        color: var(--neutral-500);
        margin: 2px 0 0 0;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       DECISION RESULTS
       ═══════════════════════════════════════════════════════════════ */
    .decision-container {
        border-radius: var(--radius-xl);
        padding: 32px;
        margin: 24px 0;
        position: relative;
        overflow: hidden;
    }
    
    .decision-approved {
        background: linear-gradient(135deg, #E3FCEF 0%, #C1F4D5 100%);
        border: 2px solid #36B37E;
    }
    
    .decision-denied {
        background: linear-gradient(135deg, #FFEBE6 0%, #FFD5CC 100%);
        border: 2px solid #DE350B;
    }
    
    .decision-icon {
        width: 72px;
        height: 72px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 36px;
        margin-bottom: 16px;
        box-shadow: var(--shadow-md);
    }
    
    .decision-approved .decision-icon {
        background: linear-gradient(135deg, #36B37E 0%, #00875A 100%);
        color: white;
    }
    
    .decision-denied .decision-icon {
        background: linear-gradient(135deg, #DE350B 0%, #BF2600 100%);
        color: white;
    }
    
    .decision-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0 0 8px 0;
    }
    
    .decision-approved .decision-title { color: #006644; }
    .decision-denied .decision-title { color: #BF2600; }
    
    .decision-message {
        font-size: 1.05rem;
        color: var(--neutral-700);
        margin: 0;
        line-height: 1.6;
    }
    
    .decision-confidence {
        position: absolute;
        top: 24px;
        right: 24px;
        text-align: right;
    }
    
    .confidence-label {
        font-size: 0.8rem;
        color: var(--neutral-500);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .confidence-value {
        font-size: 2rem;
        font-weight: 700;
    }
    
    .decision-approved .confidence-value { color: #006644; }
    .decision-denied .confidence-value { color: #BF2600; }
    
    /* ═══════════════════════════════════════════════════════════════
       FACTOR CARDS
       ═══════════════════════════════════════════════════════════════ */
    .factor-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    
    .factor-item {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px 20px;
        background: white;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
        border-left: 4px solid transparent;
    }
    
    .factor-item:hover {
        box-shadow: var(--shadow-md);
        transform: translateX(4px);
    }
    
    .factor-positive { 
        border-left-color: var(--success-green);
        background: linear-gradient(90deg, rgba(54, 179, 126, 0.05) 0%, white 100%);
    }
    
    .factor-negative { 
        border-left-color: var(--error-red);
        background: linear-gradient(90deg, rgba(222, 53, 11, 0.05) 0%, white 100%);
    }
    
    .factor-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
    }
    
    .factor-positive .factor-icon {
        background: var(--success-light);
        color: var(--success-green);
    }
    
    .factor-negative .factor-icon {
        background: var(--error-light);
        color: var(--error-red);
    }
    
    .factor-content {
        flex: 1;
    }
    
    .factor-name {
        font-weight: 600;
        color: var(--neutral-900);
        margin-bottom: 2px;
    }
    
    .factor-value {
        font-size: 0.9rem;
        color: var(--neutral-500);
    }
    
    .factor-impact {
        font-weight: 700;
        font-size: 1.1rem;
        padding: 6px 12px;
        border-radius: 8px;
    }
    
    .factor-positive .factor-impact {
        background: var(--success-light);
        color: var(--success-green);
    }
    
    .factor-negative .factor-impact {
        background: var(--error-light);
        color: var(--error-red);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       FORM STYLING
       ═══════════════════════════════════════════════════════════════ */
    .form-section {
        background: white;
        border-radius: var(--radius-lg);
        padding: 28px;
        box-shadow: var(--shadow-md);
        margin-bottom: 24px;
        border: 1px solid rgba(0, 0, 0, 0.04);
    }
    
    .form-section-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--neutral-900);
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--neutral-100);
    }
    
    .form-section-icon {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        background: linear-gradient(135deg, #E6F0FF 0%, #CCE0FF 100%);
        color: var(--primary-blue);
    }
    
    /* Streamlit Input Overrides */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #E1E5EB;
        padding: 12px 16px;
        font-size: 0.95rem;
        transition: all 0.2s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(0, 82, 204, 0.15);
    }
    
    .stSelectbox > div > div {
        border-radius: 10px;
        border: 2px solid #E1E5EB;
    }
    
    .stSlider > div > div > div {
        background: var(--primary-blue);
    }
    
    .stNumberInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #E1E5EB;
        padding: 12px 16px;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       BUTTONS
       ═══════════════════════════════════════════════════════════════ */
    .stButton > button {
        background: linear-gradient(135deg, #0052CC 0%, #003D99 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 16px 32px;
        font-weight: 600;
        font-size: 1.05rem;
        letter-spacing: 0.3px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 82, 204, 0.25);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #003D99 0%, #002966 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 82, 204, 0.35);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       METRICS & STATS
       ═══════════════════════════════════════════════════════════════ */
    .metric-card {
        background: white;
        border-radius: var(--radius-lg);
        padding: 24px;
        text-align: center;
        box-shadow: var(--shadow-md);
        border: 1px solid rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
    }
    
    .metric-icon {
        width: 56px;
        height: 56px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        margin: 0 auto 16px;
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--neutral-900);
        margin-bottom: 4px;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: var(--neutral-500);
        font-weight: 500;
    }
    
    .metric-change {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 20px;
        margin-top: 8px;
    }
    
    .metric-change.positive {
        background: var(--success-light);
        color: var(--success-green);
    }
    
    .metric-change.negative {
        background: var(--error-light);
        color: var(--error-red);
    }
    
    /* ═══════════════════════════════════════════════════════════════
       TABS
       ═══════════════════════════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--neutral-100);
        padding: 6px;
        border-radius: 12px;
        gap: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 500;
        color: var(--neutral-500);
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.5);
        color: var(--neutral-700);
    }
    
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: var(--primary-blue) !important;
        font-weight: 600;
        box-shadow: var(--shadow-sm);
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 24px;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       ALERTS & NOTIFICATIONS
       ═══════════════════════════════════════════════════════════════ */
    .alert {
        display: flex;
        align-items: flex-start;
        gap: 16px;
        padding: 20px 24px;
        border-radius: var(--radius-md);
        margin: 16px 0;
    }
    
    .alert-info {
        background: linear-gradient(135deg, #E6F0FF 0%, #CCE0FF 100%);
        border: 1px solid #4C9AFF;
    }
    
    .alert-success {
        background: linear-gradient(135deg, #E3FCEF 0%, #C1F4D5 100%);
        border: 1px solid var(--success-green);
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #FFF4E5 0%, #FFE4BC 100%);
        border: 1px solid var(--warning-orange);
    }
    
    .alert-error {
        background: linear-gradient(135deg, #FFEBE6 0%, #FFD5CC 100%);
        border: 1px solid var(--error-red);
    }
    
    .alert-icon {
        font-size: 24px;
        flex-shrink: 0;
    }
    
    .alert-content {
        flex: 1;
    }
    
    .alert-title {
        font-weight: 600;
        margin-bottom: 4px;
        color: var(--neutral-900);
    }
    
    .alert-message {
        font-size: 0.95rem;
        color: var(--neutral-700);
        line-height: 1.5;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       IMPROVEMENT TIPS
       ═══════════════════════════════════════════════════════════════ */
    .tips-container {
        background: linear-gradient(135deg, #FFFAE6 0%, #FFF1B8 100%);
        border: 1px solid #FFAB00;
        border-radius: var(--radius-lg);
        padding: 24px;
        margin-top: 24px;
    }
    
    .tips-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
    }
    
    .tips-icon {
        font-size: 28px;
    }
    
    .tips-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: var(--neutral-900);
        margin: 0;
    }
    
    .tip-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid rgba(255, 171, 0, 0.3);
    }
    
    .tip-item:last-child {
        border-bottom: none;
    }
    
    .tip-number {
        width: 28px;
        height: 28px;
        background: #FFAB00;
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        flex-shrink: 0;
    }
    
    .tip-text {
        color: var(--neutral-700);
        line-height: 1.5;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       FAIRNESS GAUGE
       ═══════════════════════════════════════════════════════════════ */
    .fairness-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 20px;
        border-radius: 30px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    
    .fairness-good {
        background: linear-gradient(135deg, #E3FCEF 0%, #C1F4D5 100%);
        color: #006644;
        border: 1px solid #36B37E;
    }
    
    .fairness-warning {
        background: linear-gradient(135deg, #FFF4E5 0%, #FFE4BC 100%);
        color: #974F0C;
        border: 1px solid #FF8B00;
    }
    
    .fairness-poor {
        background: linear-gradient(135deg, #FFEBE6 0%, #FFD5CC 100%);
        color: #BF2600;
        border: 1px solid #DE350B;
    }
    
    /* ═══════════════════════════════════════════════════════════════
       RESPONSIVE
       ═══════════════════════════════════════════════════════════════ */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
        
        .header-banner {
            margin: -1rem -1rem 1.5rem -1rem;
            padding: 1.5rem;
            border-radius: 0 0 16px 16px;
        }
        
        .header-title {
            font-size: 1.5rem;
        }
        
        .decision-container {
            padding: 24px;
        }
        
        .decision-confidence {
            position: relative;
            top: auto;
            right: auto;
            text-align: left;
            margin-top: 16px;
        }
    }
    
    /* ═══════════════════════════════════════════════════════════════
       ANIMATIONS
       ═══════════════════════════════════════════════════════════════ */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-in {
        animation: fadeInUp 0.5s ease forwards;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE & CACHING
# ═══════════════════════════════════════════════════════════════════

@st.cache_resource
def load_or_train_model():
    """Load existing model or train a new one."""
    model = LoanApprovalModel()
    model_path = 'models/loan_model.pkl'
    
    if os.path.exists(model_path):
        try:
            model.load_model(model_path)
            return model, "loaded"
        except Exception as e:
            pass
    
    df = generate_synthetic_data(n_samples=5000)
    model.train(df)
    model.save_model(model_path)
    return model, "trained"


@st.cache_data
def get_training_data():
    """Get or generate training data."""
    data_path = 'data/loan_applications.csv'
    
    if os.path.exists(data_path):
        return pd.read_csv(data_path)
    
    df = generate_synthetic_data(n_samples=5000)
    os.makedirs('data', exist_ok=True)
    df.to_csv(data_path, index=False)
    return df


# ═══════════════════════════════════════════════════════════════════
# VISUALIZATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def create_contribution_chart(explanation, prediction_result):
    """Create professional horizontal bar chart for feature contributions."""
    
    contributions = explanation['all_contributions'][:10]
    
    features = [c['display_name'] for c in contributions]
    values = [c['contribution'] for c in contributions]
    colors = ['#36B37E' if v > 0 else '#DE350B' for v in values]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=features,
        x=values,
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color=colors, width=1)
        ),
        text=[f'{v:+.3f}' for v in values],
        textposition='outside',
        textfont=dict(size=12, family='Segoe UI'),
        hovertemplate='<b>%{y}</b><br>Impact Score: %{x:.3f}<extra></extra>'
    ))
    
    fig.add_vline(x=0, line_dash="solid", line_color="#B3BAC5", line_width=2)
    
    fig.update_layout(
        title=dict(
            text='<b>Factor Impact Analysis</b><br><span style="font-size:12px;color:#5E6C84;">How each factor influenced the decision</span>',
            font=dict(size=18, family='Segoe UI', color='#091E42'),
            x=0
        ),
        xaxis=dict(
            title='Impact on Approval Score',
            titlefont=dict(size=13, color='#5E6C84'),
            gridcolor='#F4F5F7',
            zerolinecolor='#B3BAC5',
            tickfont=dict(color='#5E6C84')
        ),
        yaxis=dict(
            gridcolor='#F4F5F7',
            autorange='reversed',
            tickfont=dict(color='#253858', size=12)
        ),
        height=420,
        margin=dict(l=20, r=60, t=80, b=60),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Segoe UI, sans-serif')
    )
    
    return fig


def create_gauge_chart(probability, title="Approval Likelihood"):
    """Create professional gauge chart."""
    
    if probability >= 0.6:
        color = '#36B37E'
    elif probability >= 0.4:
        color = '#FFAB00'
    else:
        color = '#DE350B'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=probability * 100,
        number=dict(
            suffix='%',
            font=dict(size=48, family='Segoe UI', color='#091E42')
        ),
        gauge=dict(
            axis=dict(
                range=[0, 100],
                tickwidth=2,
                tickcolor='#B3BAC5',
                tickfont=dict(size=11, color='#5E6C84')
            ),
            bar=dict(color=color, thickness=0.8),
            bgcolor='white',
            borderwidth=3,
            bordercolor='#E1E5EB',
            steps=[
                dict(range=[0, 40], color='#FFEBE6'),
                dict(range=[40, 60], color='#FFF4E5'),
                dict(range=[60, 100], color='#E3FCEF')
            ],
            threshold=dict(
                line=dict(color='#091E42', width=3),
                thickness=0.8,
                value=50
            )
        )
    ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=30, r=30, t=30, b=30),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Segoe UI, sans-serif')
    )
    
    return fig


def create_waterfall_chart(explanation, prediction_result):
    """Create waterfall chart showing score progression."""
    
    contributions = explanation['all_contributions']
    base_value = explanation['base_value']
    
    sorted_contrib = sorted(contributions, key=lambda x: abs(x['contribution']), reverse=True)[:6]
    
    names = ['Base Score']
    values = [base_value]
    measures = ['absolute']
    
    running = base_value
    for c in sorted_contrib:
        name = c['display_name'][:18] + '...' if len(c['display_name']) > 18 else c['display_name']
        names.append(name)
        values.append(c['contribution'])
        measures.append('relative')
        running += c['contribution']
    
    names.append('Final Score')
    values.append(running)
    measures.append('total')
    
    fig = go.Figure(go.Waterfall(
        orientation='v',
        measure=measures,
        x=names,
        y=values,
        text=[f'{v:.2f}' for v in values],
        textposition='outside',
        textfont=dict(size=11, family='Segoe UI', color='#091E42'),
        connector=dict(line=dict(color='#B3BAC5', width=1, dash='dot')),
        decreasing=dict(marker=dict(color='#DE350B')),
        increasing=dict(marker=dict(color='#36B37E')),
        totals=dict(marker=dict(color='#0052CC'))
    ))
    
    fig.update_layout(
        title=dict(
            text='<b>Score Journey</b><br><span style="font-size:12px;color:#5E6C84;">From base rate to final decision</span>',
            font=dict(size=18, family='Segoe UI', color='#091E42'),
            x=0
        ),
        xaxis=dict(
            tickangle=-35,
            tickfont=dict(size=11, color='#253858')
        ),
        yaxis=dict(
            title='Score',
            titlefont=dict(size=13, color='#5E6C84'),
            gridcolor='#F4F5F7',
            tickfont=dict(color='#5E6C84')
        ),
        height=400,
        margin=dict(l=20, r=20, t=80, b=100),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,
        font=dict(family='Segoe UI, sans-serif')
    )
    
    return fig


def create_fairness_chart(fairness_data, attribute):
    """Create fairness comparison bar chart."""
    
    groups = list(fairness_data['group_metrics'].keys())
    rates = [m['approval_rate'] * 100 for m in fairness_data['group_metrics'].values()]
    counts = [m['sample_size'] for m in fairness_data['group_metrics'].values()]
    
    avg_rate = sum(rates) / len(rates)
    
    colors = ['#0052CC' if abs(r - avg_rate) < 8 else '#FFAB00' for r in rates]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=groups,
        y=rates,
        marker=dict(
            color=colors,
            line=dict(color=colors, width=1)
        ),
        text=[f'{r:.1f}%' for r in rates],
        textposition='outside',
        textfont=dict(size=13, family='Segoe UI'),
        hovertemplate='<b>%{x}</b><br>Approval Rate: %{y:.1f}%<br>Sample Size: %{customdata}<extra></extra>',
        customdata=counts
    ))
    
    fig.add_hline(
        y=avg_rate, 
        line_dash="dash", 
        line_color="#FF8B00", 
        line_width=2,
        annotation_text=f"Average: {avg_rate:.1f}%",
        annotation_position="right",
        annotation_font=dict(size=12, color='#FF8B00', family='Segoe UI')
    )
    
    fig.update_layout(
        title=dict(
            text=f'<b>Approval Rates by {attribute.replace("_", " ").title()}</b>',
            font=dict(size=16, family='Segoe UI', color='#091E42'),
            x=0
        ),
        xaxis=dict(
            title='',
            tickfont=dict(size=12, color='#253858')
        ),
        yaxis=dict(
            title='Approval Rate (%)',
            titlefont=dict(size=12, color='#5E6C84'),
            gridcolor='#F4F5F7',
            range=[0, max(rates) * 1.25],
            tickfont=dict(color='#5E6C84')
        ),
        height=360,
        margin=dict(l=20, r=20, t=60, b=40),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Segoe UI, sans-serif')
    )
    
    return fig


def create_feature_importance_chart(importance_df):
    """Create horizontal bar chart for feature importance."""
    
    top_features = importance_df.head(10)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=top_features['display_name'],
        x=top_features['importance'],
        orientation='h',
        marker=dict(
            color=top_features['importance'],
            colorscale='Blues',
            line=dict(color='#0052CC', width=1)
        ),
        text=[f'{v:.3f}' for v in top_features['importance']],
        textposition='outside',
        textfont=dict(size=11, family='Segoe UI'),
        hovertemplate='<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text='<b>What Matters Most</b><br><span style="font-size:12px;color:#5E6C84;">Top factors influencing loan decisions</span>',
            font=dict(size=18, family='Segoe UI', color='#091E42'),
            x=0
        ),
        xaxis=dict(
            title='Importance Score',
            titlefont=dict(size=13, color='#5E6C84'),
            gridcolor='#F4F5F7',
            tickfont=dict(color='#5E6C84')
        ),
        yaxis=dict(
            categoryorder='total ascending',
            tickfont=dict(size=12, color='#253858')
        ),
        height=450,
        margin=dict(l=20, r=60, t=80, b=60),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family='Segoe UI, sans-serif')
    )
    
    return fig


# ═══════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════

def main():
    # ─────────────────────────────────────────────────────────────────
    # HEADER BANNER
    # ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="header-banner">
        <div class="header-logo">
            <div class="header-logo-icon">🏦</div>
            <div>
                <h1 class="header-title">LoanWise Pro</h1>
                <p class="header-subtitle">Intelligent Lending with Transparent AI Decisions</p>
            </div>
        </div>
        <div class="header-badge">
            <span>🔒</span> RBI Compliant • Secure • Fair Lending
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Load model
    with st.spinner('Initializing AI Engine...'):
        model, status = load_or_train_model()
        training_data = get_training_data()
    
    # ─────────────────────────────────────────────────────────────────
    # SIDEBAR
    # ─────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <div class="sidebar-logo">🏦</div>
            <h2 class="sidebar-brand">LoanWise Pro</h2>
            <p class="sidebar-tagline">Smart Lending Platform</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        page = st.radio(
            "Navigate",
            ["🎯 New Application", "📊 Fairness Monitor", "📈 Analytics", "ℹ️ About"],
            label_visibility="collapsed"
        )
        
        # Stats
        st.markdown("---")
        approval_rate = training_data['loan_approved'].mean() * 100
        avg_amount = training_data['loan_amount'].mean()
        
        st.markdown(f"""
        <div class="sidebar-stats">
            <div style="font-weight: 600; color: #091E42; margin-bottom: 12px;">📊 Platform Stats</div>
            <div class="stat-item">
                <span class="stat-label">Approval Rate</span>
                <span class="stat-value">{approval_rate:.1f}%</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Avg. Loan Amount</span>
                <span class="stat-value">₹{avg_amount/100000:.1f}L</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Total Processed</span>
                <span class="stat-value">{len(training_data):,}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Footer
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; padding: 8px; color: #5E6C84; font-size: 0.8rem;">
            <div>Version 3.0.0</div>
            <div>© 2026 LoanWise Pro</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # PAGE: NEW APPLICATION
    # ═══════════════════════════════════════════════════════════════
    
    if page == "🎯 New Application":
        
        st.markdown("""
        <div class="alert alert-info">
            <div class="alert-icon">💡</div>
            <div class="alert-content">
                <div class="alert-title">Quick & Transparent Assessment</div>
                <div class="alert-message">Fill in the applicant's details below. Our AI will analyze the application and provide a clear explanation of the decision.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # FORM SECTION 1: Personal Information
        st.markdown("""
        <div class="form-section">
            <div class="form-section-title">
                <div class="form-section-icon">👤</div>
                Personal Information
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            applicant_name = st.text_input("Full Name", value="Priya Sharma")
        with col2:
            age = st.number_input("Age", min_value=21, max_value=65, value=28)
        with col3:
            gender = st.selectbox("Gender", ["Female", "Male"])
        with col4:
            city = st.selectbox("City", INDIAN_CITIES, index=INDIAN_CITIES.index("Agra"))
        
        col5, col6, col7 = st.columns(3)
        
        with col5:
            education = st.selectbox("Education", ["High School", "Graduate", "Post Graduate", "Professional"])
        with col6:
            marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced"])
        with col7:
            num_dependents = st.number_input("Dependents", min_value=0, max_value=10, value=1)
        
        # FORM SECTION 2: Employment Details
        st.markdown("""
        <div class="form-section">
            <div class="form-section-title">
                <div class="form-section-icon">💼</div>
                Employment Details
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            employment_type = st.selectbox("Employment Type", ["Salaried", "Self-Employed", "Business Owner", "Government", "Retired"])
        with col2:
            industry = st.selectbox("Industry", ["Information Technology", "Banking & Finance", "Healthcare", "Education", "Manufacturing", "Retail", "Real Estate", "Government", "Other"])
        with col3:
            years_at_job = st.number_input("Years at Current Job", min_value=0, max_value=40, value=3)
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            monthly_income = st.number_input("Monthly Income (₹)", min_value=15000, max_value=1000000, value=45000, step=5000)
        with col5:
            existing_emi = st.number_input("Existing EMI (₹)", min_value=0, max_value=500000, value=8000, step=1000)
        with col6:
            num_existing_loans = st.number_input("Existing Loans", min_value=0, max_value=10, value=1)
        
        # FORM SECTION 3: Credit Profile
        st.markdown("""
        <div class="form-section">
            <div class="form-section-title">
                <div class="form-section-icon">📊</div>
                Credit Profile
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            cibil_score = st.slider("CIBIL Score", min_value=300, max_value=900, value=680)
            if cibil_score >= 750:
                st.caption("🟢 Excellent")
            elif cibil_score >= 700:
                st.caption("🟢 Good")
            elif cibil_score >= 650:
                st.caption("🟡 Fair")
            else:
                st.caption("🔴 Needs Improvement")
            
        with col2:
            credit_history_years = st.number_input("Credit History (Years)", min_value=0, max_value=30, value=3)
        with col3:
            late_payments = st.number_input("Late Payments (2 Years)", min_value=0, max_value=20, value=2)
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            has_defaults = st.checkbox("Has Previous Defaults", value=False)
        with col5:
            owns_property = st.checkbox("Owns Property", value=False)
        with col6:
            savings_balance = st.number_input("Savings Balance (₹)", min_value=0, max_value=5000000, value=120000, step=10000)
        
        years_with_bank = st.slider("Years with Bank", min_value=0, max_value=30, value=2)
        
        # FORM SECTION 4: Loan Request
        st.markdown("""
        <div class="form-section">
            <div class="form-section-title">
                <div class="form-section-icon">💰</div>
                Loan Request Details
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            loan_amount = st.number_input("Loan Amount (₹)", min_value=50000, max_value=5000000, value=500000, step=25000)
            st.caption(f"₹{loan_amount/100000:.2f} Lakhs")
        with col2:
            loan_tenure = st.selectbox("Tenure (Months)", [12, 24, 36, 48, 60, 72, 84], index=2)
        with col3:
            loan_purpose = st.selectbox("Purpose", LOAN_PURPOSES)
        
        # Calculate EMI preview
        interest_rate = 12.0
        monthly_rate = interest_rate / 12 / 100
        emi = (loan_amount * monthly_rate * (1 + monthly_rate)**loan_tenure) / ((1 + monthly_rate)**loan_tenure - 1)
        
        st.markdown(f"""
        <div style="background: #E6F0FF; padding: 16px 20px; border-radius: 10px; margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #5E6C84; font-size: 0.9rem;">Estimated Monthly EMI</span>
                    <div style="color: #0052CC; font-size: 1.4rem; font-weight: 700;">₹{emi:,.0f}</div>
                </div>
                <div style="text-align: right;">
                    <span style="color: #5E6C84; font-size: 0.9rem;">@ {interest_rate}% p.a.</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ASSESS BUTTON
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            assess_clicked = st.button("🔍  ASSESS LOAN ELIGIBILITY", use_container_width=True, type="primary")
        
        # ═══════════════════════════════════════════════════════════
        # RESULTS SECTION
        # ═══════════════════════════════════════════════════════════
        
        if assess_clicked:
            applicant_data = pd.DataFrame([{
                'applicant_name': applicant_name,
                'age': age,
                'gender': gender,
                'city': city,
                'education': education,
                'marital_status': marital_status,
                'num_dependents': num_dependents,
                'employment_type': employment_type,
                'industry': industry,
                'years_at_current_job': years_at_job,
                'monthly_income': monthly_income,
                'existing_emi': existing_emi,
                'num_existing_loans': num_existing_loans,
                'cibil_score': cibil_score,
                'credit_history_years': credit_history_years,
                'late_payments_last_2_years': late_payments,
                'has_defaults': has_defaults,
                'owns_property': owns_property,
                'savings_balance': savings_balance,
                'years_with_bank': years_with_bank,
                'loan_amount': loan_amount,
                'loan_tenure_months': loan_tenure,
                'loan_purpose': loan_purpose
            }])
            
            with st.spinner('🔄 Analyzing application with AI...'):
                prediction = model.predict(applicant_data)
                explanation = model.explain_prediction(applicant_data)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # DECISION DISPLAY
            if prediction['approved']:
                st.markdown(f"""
                <div class="decision-container decision-approved animate-in">
                    <div class="decision-icon">✓</div>
                    <h2 class="decision-title">Congratulations! Loan Approved</h2>
                    <p class="decision-message">
                        Dear <strong>{applicant_name}</strong>, we are pleased to inform you that your loan application 
                        for <strong>₹{loan_amount:,}</strong> has been <strong>approved</strong>.
                    </p>
                    <div class="decision-confidence">
                        <div class="confidence-label">Confidence Score</div>
                        <div class="confidence-value">{prediction['approval_probability']*100:.0f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="decision-container decision-denied animate-in">
                    <div class="decision-icon">✗</div>
                    <h2 class="decision-title">Application Not Approved</h2>
                    <p class="decision-message">
                        Dear <strong>{applicant_name}</strong>, after careful review of your application for 
                        <strong>₹{loan_amount:,}</strong>, we regret to inform you that it does not meet our 
                        current approval criteria.
                    </p>
                    <div class="decision-confidence">
                        <div class="confidence-label">Risk Assessment</div>
                        <div class="confidence-value">{prediction['denial_probability']*100:.0f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # KEY METRICS
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                dti = (existing_emi / monthly_income * 100) if monthly_income > 0 else 0
                dti_color = '#36B37E' if dti < 35 else '#FFAB00' if dti < 50 else '#DE350B'
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon" style="background: #E6F0FF; color: #0052CC;">📊</div>
                    <div class="metric-value" style="color: {dti_color};">{dti:.1f}%</div>
                    <div class="metric-label">Debt-to-Income</div>
                    <div class="metric-change {'positive' if dti < 35 else 'negative'}">
                        {'✓ Healthy' if dti < 35 else '⚠ High'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                cibil_color = '#36B37E' if cibil_score >= 700 else '#FFAB00' if cibil_score >= 600 else '#DE350B'
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon" style="background: #E3FCEF; color: #36B37E;">📈</div>
                    <div class="metric-value" style="color: {cibil_color};">{cibil_score}</div>
                    <div class="metric-label">CIBIL Score</div>
                    <div class="metric-change {'positive' if cibil_score >= 700 else 'negative'}">
                        {'✓ Good' if cibil_score >= 700 else '⚠ Fair'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                loan_income_ratio = loan_amount / (monthly_income * 12) if monthly_income > 0 else 0
                lir_color = '#36B37E' if loan_income_ratio <= 1 else '#FFAB00' if loan_income_ratio <= 2 else '#DE350B'
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon" style="background: #FFF4E5; color: #FF8B00;">💰</div>
                    <div class="metric-value" style="color: {lir_color};">{loan_income_ratio:.1f}x</div>
                    <div class="metric-label">Loan-to-Income</div>
                    <div class="metric-change {'positive' if loan_income_ratio <= 1 else 'negative'}">
                        {'✓ OK' if loan_income_ratio <= 1 else '⚠ Moderate'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                stability_score = min(100, years_at_job * 15 + credit_history_years * 8)
                stab_color = '#36B37E' if stability_score >= 60 else '#FFAB00' if stability_score >= 30 else '#DE350B'
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-icon" style="background: #FFEBE6; color: #DE350B;">🏢</div>
                    <div class="metric-value" style="color: {stab_color};">{stability_score}</div>
                    <div class="metric-label">Stability Score</div>
                    <div class="metric-change {'positive' if stability_score >= 60 else 'negative'}">
                        {'✓ Strong' if stability_score >= 60 else '⚠ Building'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # EXPLANATION TABS
            st.markdown("### 📋 Decision Explanation")
            
            tab1, tab2, tab3 = st.tabs(["📊 Factor Analysis", "📈 Score Journey", "📝 Summary"])
            
            with tab1:
                st.markdown("""
                <div class="alert alert-info">
                    <div class="alert-icon">ℹ️</div>
                    <div class="alert-content">
                        <div class="alert-title">Understanding This Chart</div>
                        <div class="alert-message">
                            <strong style="color: #36B37E;">Green bars</strong> show factors that <strong>helped</strong> your application. 
                            <strong style="color: #DE350B;">Red bars</strong> show factors that <strong>worked against</strong> it.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                fig_contrib = create_contribution_chart(explanation, prediction)
                st.plotly_chart(fig_contrib, use_container_width=True)
            
            with tab2:
                st.markdown("""
                <div class="alert alert-info">
                    <div class="alert-icon">ℹ️</div>
                    <div class="alert-content">
                        <div class="alert-title">Score Progression</div>
                        <div class="alert-message">
                            This chart shows how your score built up from the base rate to the final decision.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                fig_waterfall = create_waterfall_chart(explanation, prediction)
                st.plotly_chart(fig_waterfall, use_container_width=True)
            
            with tab3:
                col_pos, col_neg = st.columns(2)
                
                with col_pos:
                    st.markdown("#### ✅ Factors in Your Favor")
                    if explanation['positive_factors']:
                        for factor in explanation['positive_factors'][:5]:
                            st.markdown(f"""
                            <div class="factor-item factor-positive">
                                <div class="factor-icon">✓</div>
                                <div class="factor-content">
                                    <div class="factor-name">{factor['display_name']}</div>
                                    <div class="factor-value">Value: {factor['original_value']}</div>
                                </div>
                                <div class="factor-impact">+{factor['contribution']:.3f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No significant positive factors identified.")
                
                with col_neg:
                    st.markdown("#### ⚠️ Areas of Concern")
                    if explanation['negative_factors']:
                        for factor in explanation['negative_factors'][:5]:
                            st.markdown(f"""
                            <div class="factor-item factor-negative">
                                <div class="factor-icon">!</div>
                                <div class="factor-content">
                                    <div class="factor-name">{factor['display_name']}</div>
                                    <div class="factor-value">Value: {factor['original_value']}</div>
                                </div>
                                <div class="factor-impact">{factor['contribution']:.3f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.success("No significant concerns identified!")
            
            # IMPROVEMENT TIPS (for denied applications)
            if not prediction['approved']:
                suggestions = []
                
                if cibil_score < 700:
                    suggestions.append(f"**Improve your CIBIL score** — Current: {cibil_score}. Pay bills on time and reduce credit utilization.")
                
                if late_payments > 0:
                    suggestions.append(f"**Clear payment history** — {late_payments} late payments recorded. Maintain timely payments.")
                
                dti = existing_emi / monthly_income if monthly_income > 0 else 1
                if dti > 0.35:
                    suggestions.append(f"**Reduce existing debt** — Debt-to-income: {dti*100:.0f}%. Pay off some existing loans.")
                
                if credit_history_years < 3:
                    suggestions.append("**Build credit history** — Longer credit history strengthens applications.")
                
                if loan_amount > monthly_income * 18:
                    suggestions.append(f"**Consider a smaller loan** — ₹{loan_amount:,} is high for your income.")
                
                if suggestions:
                    st.markdown(f"""
                    <div class="tips-container">
                        <div class="tips-header">
                            <div class="tips-icon">💡</div>
                            <h3 class="tips-title">How to Improve Your Chances</h3>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for i, suggestion in enumerate(suggestions, 1):
                        st.markdown(f"""
                        <div class="tip-item">
                            <div class="tip-number">{i}</div>
                            <div class="tip-text">{suggestion}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
    
    # ═══════════════════════════════════════════════════════════════
    # PAGE: FAIRNESS MONITOR
    # ═══════════════════════════════════════════════════════════════
    
    elif page == "📊 Fairness Monitor":
        st.markdown("### 📊 Fairness & Bias Monitoring Dashboard")
        
        st.markdown("""
        <div class="alert alert-info">
            <div class="alert-icon">🔍</div>
            <div class="alert-content">
                <div class="alert-title">AI Fairness Monitoring</div>
                <div class="alert-message">
                    This dashboard monitors our AI model for potential bias across different demographic groups.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.spinner("Analyzing model fairness..."):
            X = model.preprocess_data(training_data, is_training=False)
            predictions = model.model.predict(X)
            
            protected_attrs = pd.DataFrame({
                'gender': training_data['gender'],
                'age_group': create_age_groups(training_data['age']),
                'income_group': create_income_groups(training_data['monthly_income']),
                'employment_type': training_data['employment_type']
            })
            
            analyzer = FairnessAnalyzer(predictions, training_data['loan_approved'].values, protected_attrs)
            report = analyzer.generate_fairness_report(['gender', 'age_group', 'income_group', 'employment_type'])
        
        if report['summary']['overall_fair']:
            st.markdown("""
            <div class="alert alert-success">
                <div class="alert-icon">✅</div>
                <div class="alert-content">
                    <div class="alert-title">Fairness Check Passed</div>
                    <div class="alert-message">No significant bias detected across analyzed demographic groups.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert alert-warning">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <div class="alert-title">Attention Required</div>
                    <div class="alert-message">{report['summary']['issues_found']} potential fairness issue(s) detected.</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Gender Analysis")
            gender_data = report['demographic_parity']['gender']
            fig_gender = create_fairness_chart(gender_data, 'gender')
            st.plotly_chart(fig_gender, use_container_width=True)
            
            disparity = gender_data['max_disparity'] * 100
            badge_class = 'fairness-good' if disparity < 8 else 'fairness-warning'
            badge_text = '✓ Excellent' if disparity < 8 else '⚠ Acceptable'
            st.markdown(f'<div style="text-align: center;"><span class="fairness-badge {badge_class}">{badge_text} — {disparity:.1f}% disparity</span></div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### Age Group Analysis")
            age_data = report['demographic_parity']['age_group']
            fig_age = create_fairness_chart(age_data, 'age_group')
            st.plotly_chart(fig_age, use_container_width=True)
            
            disparity = age_data['max_disparity'] * 100
            badge_class = 'fairness-good' if disparity < 10 else 'fairness-warning'
            badge_text = '✓ Good' if disparity < 10 else '⚠ Moderate'
            st.markdown(f'<div style="text-align: center;"><span class="fairness-badge {badge_class}">{badge_text} — {disparity:.1f}% disparity</span></div>', unsafe_allow_html=True)
        
        with st.expander("📄 View Full Technical Report"):
            st.code(generate_fairness_summary_text(report), language=None)
    
    # ═══════════════════════════════════════════════════════════════
    # PAGE: ANALYTICS
    # ═══════════════════════════════════════════════════════════════
    
    elif page == "📈 Analytics":
        st.markdown("### 📈 Model Analytics & Insights")
        
        st.markdown("#### 🎯 Key Decision Factors")
        importance_df = model.get_feature_importance()
        fig_importance = create_feature_importance_chart(importance_df)
        st.plotly_chart(fig_importance, use_container_width=True)
        
        st.markdown("#### 📊 Application Data Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            training_data['cibil_range'] = pd.cut(
                training_data['cibil_score'],
                bins=[300, 500, 600, 700, 800, 900],
                labels=['300-500', '501-600', '601-700', '701-800', '801-900']
            )
            
            cibil_approval = training_data.groupby('cibil_range')['loan_approved'].agg(['mean']).reset_index()
            cibil_approval.columns = ['CIBIL Range', 'Approval Rate']
            cibil_approval['Approval Rate'] = cibil_approval['Approval Rate'] * 100
            
            fig_cibil = go.Figure()
            fig_cibil.add_trace(go.Bar(
                x=cibil_approval['CIBIL Range'],
                y=cibil_approval['Approval Rate'],
                marker_color=['#DE350B', '#FF8B00', '#FFAB00', '#36B37E', '#00875A'],
                text=[f'{r:.0f}%' for r in cibil_approval['Approval Rate']],
                textposition='outside'
            ))
            fig_cibil.update_layout(
                title='<b>Approval Rate by CIBIL Score</b>',
                xaxis_title='CIBIL Score Range',
                yaxis_title='Approval Rate (%)',
                height=350,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            st.plotly_chart(fig_cibil, use_container_width=True)
        
        with col2:
            fig_loan = go.Figure()
            fig_loan.add_trace(go.Histogram(
                x=training_data['loan_amount'] / 100000,
                nbinsx=25,
                marker_color='#0052CC'
            ))
            fig_loan.update_layout(
                title='<b>Loan Amount Distribution</b>',
                xaxis_title='Loan Amount (₹ Lakhs)',
                yaxis_title='Number of Applications',
                height=350,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            st.plotly_chart(fig_loan, use_container_width=True)
    
    # ═══════════════════════════════════════════════════════════════
    # PAGE: ABOUT
    # ═══════════════════════════════════════════════════════════════
    
    elif page == "ℹ️ About":
        st.markdown("### ℹ️ About LoanWise Pro")
        
        st.markdown("""
        #### What is Explainable AI (XAI)?
        
        Traditional AI models are "black boxes" — they make decisions but can't explain why.
        
        **LoanWise Pro changes this** by providing:
        
        ✅ **Crystal-clear explanations** for every decision  
        ✅ **Visual charts** that make complex AI simple  
        ✅ **Fairness monitoring** to ensure equal treatment  
        ✅ **Actionable tips** for denied applicants  
        
        ---
        
        #### How Does It Work?
        
        We use **SHAP (SHapley Additive exPlanations)** — a technique from game theory that 
        fairly distributes "credit" for a prediction among all input factors.
        
        ---
        
        #### Our Fairness Commitment
        
        We continuously monitor for bias across gender, age groups, income levels, and employment types.
        Our model complies with RBI fair lending guidelines.
        """)
        
        with st.expander("🔧 Technical Details"):
            st.markdown("""
            **Model Architecture:**
            - Algorithm: Gradient Boosting Classifier
            - Explainability: SHAP TreeExplainer
            - Features: 20 input variables
            - Accuracy: ~94.6%
            - AUC-ROC: ~0.99
            """)


if __name__ == "__main__":
    main()
