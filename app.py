import streamlit as st
import pandas as pd
import numpy as np
import random
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import VotingClassifier
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

# ── Supabase setup ───────────────────────────────────────────────────────────
from supabase import create_client

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="evDOCTOR — AI EV Fault Diagnosis",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject Premium CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Import Google fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ── Root variables ── */
:root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-card: rgba(17, 24, 39, 0.7);
    --bg-glass: rgba(255,255,255,0.04);
    --border-glass: rgba(255,255,255,0.08);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-cyan: #22d3ee;
    --accent-blue: #3b82f6;
    --accent-purple: #a855f7;
    --accent-green: #10b981;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-orange: #f97316;
    --glow-cyan: 0 0 20px rgba(34,211,238,0.3);
    --glow-blue: 0 0 20px rgba(59,130,246,0.3);
    --glow-green: 0 0 20px rgba(16,185,129,0.25);
    --glow-amber: 0 0 20px rgba(245,158,11,0.25);
    --glow-red: 0 0 20px rgba(239,68,68,0.3);
    --radius: 16px;
    --radius-sm: 10px;
}

/* ── Global overrides ── */
html, body, [data-testid="stAppViewContainer"], .main, [data-testid="stApp"] {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
[data-testid="stHeader"], header {
    background: transparent !important;
}
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 6px; }

/* ── Hero Section ── */
.hero-container {
    text-align: center;
    padding: 3rem 1rem 2rem;
    position: relative;
}
.hero-container::before {
    content: '';
    position: absolute;
    top: -60px;
    left: 50%;
    transform: translateX(-50%);
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(34,211,238,0.08) 0%, rgba(59,130,246,0.04) 40%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}
.hero-title {
    font-size: 3.2rem;
    font-weight: 900;
    letter-spacing: -1.5px;
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
    position: relative;
    z-index: 1;
    animation: heroFadeIn 0.8s ease-out;
}
.hero-subtitle {
    font-size: 1.15rem;
    color: var(--text-secondary);
    font-weight: 400;
    letter-spacing: 0.3px;
    position: relative;
    z-index: 1;
    animation: heroFadeIn 1s ease-out 0.2s both;
}
.hero-badge {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 100px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    background: rgba(34,211,238,0.1);
    color: var(--accent-cyan);
    border: 1px solid rgba(34,211,238,0.2);
    margin-bottom: 1rem;
    position: relative;
    z-index: 1;
    animation: heroFadeIn 0.6s ease-out;
}
@keyframes heroFadeIn {
    from { opacity: 0; transform: translateY(15px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Glass Card ── */
.glass-card {
    background: var(--bg-glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius);
    padding: 1.8rem;
    margin-bottom: 1.2rem;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.glass-card:hover {
    border-color: rgba(255,255,255,0.14);
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}

/* ── Prediction Result Card ── */
.result-card {
    background: var(--bg-glass);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius);
    padding: 1.5rem 1.8rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    animation: cardSlideIn 0.5s ease-out both;
    transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
}
.result-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.3);
}
.result-card.rank-1 { animation-delay: 0.1s; }
.result-card.rank-2 { animation-delay: 0.25s; }
.result-card.rank-3 { animation-delay: 0.4s; }

.result-card.severity-critical { border-left: 4px solid var(--accent-red); }
.result-card.severity-critical:hover { border-color: var(--accent-red); box-shadow: var(--glow-red); }
.result-card.severity-high { border-left: 4px solid var(--accent-orange); }
.result-card.severity-high:hover { border-color: var(--accent-orange); box-shadow: var(--glow-amber); }
.result-card.severity-medium { border-left: 4px solid var(--accent-amber); }
.result-card.severity-medium:hover { border-color: var(--accent-amber); box-shadow: var(--glow-amber); }
.result-card.severity-low { border-left: 4px solid var(--accent-green); }
.result-card.severity-low:hover { border-color: var(--accent-green); box-shadow: var(--glow-green); }

@keyframes cardSlideIn {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Severity Badge ── */
.severity-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.severity-badge.critical { background: rgba(239,68,68,0.15); color: var(--accent-red); border: 1px solid rgba(239,68,68,0.3); }
.severity-badge.high     { background: rgba(249,115,22,0.15); color: var(--accent-orange); border: 1px solid rgba(249,115,22,0.3); }
.severity-badge.medium   { background: rgba(245,158,11,0.15); color: var(--accent-amber); border: 1px solid rgba(245,158,11,0.3); }
.severity-badge.low      { background: rgba(16,185,129,0.15); color: var(--accent-green); border: 1px solid rgba(16,185,129,0.3); }

/* ── Category Pill ── */
.category-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 100px;
    font-size: 0.68rem;
    font-weight: 600;
    background: rgba(59,130,246,0.12);
    color: var(--accent-blue);
    border: 1px solid rgba(59,130,246,0.2);
    margin-left: 6px;
}

/* ── Confidence bar ── */
.confidence-bar-container {
    background: rgba(255,255,255,0.06);
    border-radius: 10px;
    height: 8px;
    overflow: hidden;
    margin: 8px 0;
}
.confidence-bar-fill {
    height: 100%;
    border-radius: 10px;
    transition: width 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.conf-high   { background: linear-gradient(90deg, var(--accent-green), var(--accent-cyan)); }
.conf-medium { background: linear-gradient(90deg, var(--accent-amber), var(--accent-orange)); }
.conf-low    { background: linear-gradient(90deg, var(--accent-red), var(--accent-orange)); }

/* ── DTC Code ── */
.dtc-code {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 2px 10px;
    background: rgba(168, 85, 247, 0.12);
    color: var(--accent-purple);
    border: 1px solid rgba(168,85,247,0.25);
    border-radius: 6px;
    margin-right: 8px;
}

/* ── Rank badge ── */
.rank-badge {
    position: absolute;
    top: 12px;
    right: 16px;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 0.78rem;
}
.rank-1-badge { background: rgba(34,211,238,0.15); color: var(--accent-cyan); border: 1px solid rgba(34,211,238,0.35); }
.rank-2-badge { background: rgba(148,163,184,0.1); color: var(--text-secondary); border: 1px solid rgba(148,163,184,0.2); }
.rank-3-badge { background: rgba(100,116,139,0.1); color: var(--text-muted); border: 1px solid rgba(100,116,139,0.2); }

/* ── Steps ── */
.step-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.step-item:last-child { border-bottom: none; }
.step-number {
    min-width: 28px;
    height: 28px;
    border-radius: 50%;
    background: rgba(34,211,238,0.1);
    color: var(--accent-cyan);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.75rem;
    border: 1px solid rgba(34,211,238,0.2);
    flex-shrink: 0;
}
.step-text {
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.5;
    padding-top: 3px;
}

/* ── Stat cards ── */
.stat-card {
    background: var(--bg-glass);
    border: 1px solid var(--border-glass);
    border-radius: var(--radius-sm);
    padding: 1.2rem;
    text-align: center;
    transition: transform 0.2s, border-color 0.3s;
}
.stat-card:hover {
    transform: translateY(-2px);
    border-color: rgba(255,255,255,0.12);
}
.stat-value {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -1px;
}
.stat-label {
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

/* ── Fix section ── */
.fix-box {
    background: rgba(16,185,129,0.06);
    border: 1px solid rgba(16,185,129,0.15);
    border-radius: var(--radius-sm);
    padding: 1rem 1.2rem;
    margin-top: 0.8rem;
}
.fix-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--accent-green);
    margin-bottom: 4px;
}
.fix-text {
    color: var(--text-secondary);
    font-size: 0.92rem;
    line-height: 1.5;
}

/* ── Footer ── */
.footer {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
    color: var(--text-muted);
    font-size: 0.8rem;
    border-top: 1px solid var(--border-glass);
    margin-top: 3rem;
}
.footer a {
    color: var(--accent-cyan);
    text-decoration: none;
}

/* ── Streamlit overrides ── */
.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 1rem !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}
.stTextArea textarea:focus {
    border-color: var(--accent-cyan) !important;
    box-shadow: 0 0 0 2px rgba(34,211,238,0.15) !important;
}
.stTextArea label {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
}
.stButton > button {
    background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue)) !important;
    color: #0a0e1a !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 0.7rem 2.5rem !important;
    letter-spacing: 0.5px !important;
    transition: transform 0.2s, box-shadow 0.3s !important;
    width: 100% !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: var(--glow-cyan) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: var(--bg-glass) !important;
    border: 1px solid var(--border-glass) !important;
    border-radius: var(--radius-sm) !important;
}
[data-testid="stExpander"] summary {
    color: var(--text-secondary) !important;
}

/* Radio/feedback */
.stRadio label, .stTextInput label {
    color: var(--text-secondary) !important;
}
.stTextInput input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

/* Alerts */
.stSuccess, .stWarning, .stError {
    border-radius: var(--radius-sm) !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border-radius: var(--radius-sm) !important;
}

/* Separator */
hr {
    border-color: var(--border-glass) !important;
}

/* ── Pulse animation for predict button ── */
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 5px rgba(34,211,238,0.2); }
    50%      { box-shadow: 0 0 25px rgba(34,211,238,0.4); }
}
.stButton > button {
    animation: pulseGlow 3s infinite !important;
}
.stButton > button:hover {
    animation: none !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  DATA & MODEL
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_data():
    return pd.read_csv("EV_DTC_Dataset.csv")


# ── Synonym augmentation ─────────────────────────────────────────────────────
SYNONYM_MAP = {
    "not working": ["broken", "dead", "failed", "malfunctioning", "non-functional"],
    "error": ["fault", "issue", "problem", "malfunction", "failure"],
    "overheating": ["too hot", "thermal issue", "high temperature", "overheat"],
    "battery": ["batt", "battery pack", "power cell"],
    "motor": ["drive motor", "electric motor", "traction motor"],
    "charger": ["charging unit", "obc", "onboard charger"],
    "noise": ["sound", "whine", "grinding", "humming", "clicking"],
    "low": ["weak", "insufficient", "poor", "degraded", "reduced"],
    "not responding": ["offline", "unresponsive", "comm lost", "disconnected"],
    "sensor": ["transducer", "detector", "probe", "measurement device"],
    "leak": ["leaking", "seeping", "dripping", "fluid loss"],
}


def augment_text(text):
    """Generate augmented training variants by synonym replacement & phrase shuffling."""
    variants = [text]
    phrases = [p.strip() for p in text.split(",")]

    # Shuffle variants
    for _ in range(2):
        shuffled = phrases.copy()
        random.shuffle(shuffled)
        variants.append(", ".join(shuffled))

    # Synonym replacement
    for original, synonyms in SYNONYM_MAP.items():
        if original in text.lower():
            for syn in random.sample(synonyms, min(2, len(synonyms))):
                variants.append(text.lower().replace(original, syn))

    return variants


@st.cache_resource
def build_model(df):
    """Build ensemble model with data augmentation."""
    random.seed(42)
    np.random.seed(42)

    # Augment training data
    aug_X, aug_y = [], []
    for _, row in df.iterrows():
        text = row["TrainingText"]
        label = row["Description"]
        augmented = augment_text(text)
        aug_X.extend(augmented)
        aug_y.extend([label] * len(augmented))

    # Vectorizer
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=8000,
        min_df=1,
    )

    X_vec = tfidf.fit_transform(aug_X)

    # Ensemble classifiers
    lr = LogisticRegression(max_iter=1000, C=5.0, solver="lbfgs", multi_class="multinomial")
    sgd = CalibratedClassifierCV(SGDClassifier(loss="modified_huber", max_iter=1000, random_state=42), cv=3)
    nb = MultinomialNB(alpha=0.5)

    # Fit each
    lr.fit(X_vec, aug_y)
    sgd.fit(X_vec, aug_y)
    nb.fit(X_vec, aug_y)

    return tfidf, lr, sgd, nb


# ── Prediction engine ────────────────────────────────────────────────────────
def predict_fault(symptom_text, df, tfidf, lr, sgd, nb, top_k=3):
    """Return top-k predictions with confidence from ensemble averaging."""
    vec = tfidf.transform([symptom_text])

    # Get probabilities from each model
    proba_lr = lr.predict_proba(vec)[0]
    proba_sgd = sgd.predict_proba(vec)[0]
    proba_nb = nb.predict_proba(vec)[0]

    # Weighted ensemble average (LR gets more weight as it tends to be most accurate)
    avg_proba = 0.45 * proba_lr + 0.30 * proba_sgd + 0.25 * proba_nb

    classes = lr.classes_
    top_indices = np.argsort(avg_proba)[::-1][:top_k]

    results = []
    for idx in top_indices:
        desc = classes[idx]
        conf = float(avg_proba[idx])
        row = df[df["Description"] == desc].iloc[0]

        steps_raw = str(row.get("Steps", ""))
        steps = [s.strip() for s in steps_raw.split("|") if s.strip()] if steps_raw else []

        results.append({
            "issue": desc,
            "code": row["Code"],
            "confidence": round(conf, 4),
            "severity": row.get("Severity", "Medium"),
            "category": row.get("Category", "General"),
            "fix": row["Solution"],
            "steps": steps,
        })

    return results


# ── Supabase helpers ──────────────────────────────────────────────────────────
def save_search(symptom, issue, fix):
    supabase.table("search_history").insert({
        "symptom_text": symptom,
        "predicted_issue": issue,
        "suggested_fix": fix,
    }).execute()


def save_feedback(symptom, issue, helpful, comment):
    supabase.table("feedback").insert({
        "symptom_text": symptom,
        "predicted_issue": issue,
        "was_helpful": helpful,
        "comment": comment,
    }).execute()


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD MODEL ON LOAD
# ══════════════════════════════════════════════════════════════════════════════
df = load_data()
tfidf, lr, sgd, nb = build_model(df)


# ══════════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">AI-Powered Diagnostics</div>
    <div class="hero-title">evDOCTOR</div>
    <div class="hero-subtitle">Describe your EV symptoms — get an instant AI diagnosis with step-by-step troubleshooting</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Input Section ─────────────────────────────────────────────────────────────
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown(
    '<p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.8rem;">'
    '💡 <strong>Tip:</strong> Describe what you observe — sounds, warnings, error lights, performance changes. '
    'The more detail, the more accurate the diagnosis.</p>',
    unsafe_allow_html=True,
)
user_input = st.text_area(
    "Describe your EV symptoms",
    "",
    height=120,
    placeholder="e.g. battery not charging, range dropped, motor making noise at high speed, inverter overheating warning...",
)

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    predict_clicked = st.button("Diagnose Now", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


# ── Results ───────────────────────────────────────────────────────────────────
if predict_clicked:
    if not user_input.strip():
        st.warning("Please describe your EV symptoms before diagnosing.")
    else:
        with st.spinner("Analyzing symptoms with ensemble AI..."):
            predictions = predict_fault(user_input, df, tfidf, lr, sgd, nb, top_k=3)

        # Save top prediction to Supabase
        top = predictions[0]
        save_search(user_input, top["issue"], top["fix"])

        # Store in session for feedback
        st.session_state["last_predictions"] = predictions
        st.session_state["last_input"] = user_input

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Top prediction headline ──
        conf_pct = int(top["confidence"] * 100)
        conf_class = "conf-high" if conf_pct >= 60 else ("conf-medium" if conf_pct >= 30 else "conf-low")
        severity_lower = top["severity"].lower()

        st.markdown(f"""
        <div class="result-card rank-1 severity-{severity_lower}">
            <div class="rank-badge rank-1-badge">1</div>
            <div style="margin-bottom: 6px;">
                <span class="dtc-code">{top["code"]}</span>
                <span class="severity-badge {severity_lower}">{top["severity"]}</span>
                <span class="category-pill">{top["category"]}</span>
            </div>
            <h3 style="color: var(--text-primary); font-size: 1.2rem; font-weight: 700; margin: 8px 0 4px;">
                {top["issue"]}
            </h3>
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                <span style="color: var(--text-muted); font-size: 0.82rem; min-width: 90px;">Confidence: {conf_pct}%</span>
                <div class="confidence-bar-container" style="flex: 1;">
                    <div class="confidence-bar-fill {conf_class}" style="width: {conf_pct}%;"></div>
                </div>
            </div>
            <div class="fix-box">
                <div class="fix-label">Suggested Fix</div>
                <div class="fix-text">{top["fix"]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Step-by-step for top prediction ──
        if top["steps"]:
            with st.expander("📋 Step-by-Step Troubleshooting Guide", expanded=True):
                steps_html = ""
                for i, step in enumerate(top["steps"], 1):
                    steps_html += f"""
                    <div class="step-item">
                        <div class="step-number">{i}</div>
                        <div class="step-text">{step}</div>
                    </div>"""
                st.markdown(steps_html, unsafe_allow_html=True)

        # ── Alternative predictions ──
        if len(predictions) > 1:
            st.markdown(
                '<p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 1.5rem; margin-bottom: 0.5rem;">'
                'Other possible diagnoses:</p>',
                unsafe_allow_html=True,
            )
            for rank, pred in enumerate(predictions[1:], 2):
                p_conf = int(pred["confidence"] * 100)
                p_conf_class = "conf-high" if p_conf >= 60 else ("conf-medium" if p_conf >= 30 else "conf-low")
                p_sev = pred["severity"].lower()

                st.markdown(f"""
                <div class="result-card rank-{rank} severity-{p_sev}">
                    <div class="rank-badge rank-{rank}-badge">{rank}</div>
                    <div style="margin-bottom: 4px;">
                        <span class="dtc-code">{pred["code"]}</span>
                        <span class="severity-badge {p_sev}">{pred["severity"]}</span>
                        <span class="category-pill">{pred["category"]}</span>
                    </div>
                    <h4 style="color: var(--text-primary); font-size: 1.05rem; font-weight: 600; margin: 6px 0 3px;">
                        {pred["issue"]}
                    </h4>
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                        <span style="color: var(--text-muted); font-size: 0.78rem; min-width: 90px;">Confidence: {p_conf}%</span>
                        <div class="confidence-bar-container" style="flex: 1;">
                            <div class="confidence-bar-fill {p_conf_class}" style="width: {p_conf}%;"></div>
                        </div>
                    </div>
                    <div class="fix-box">
                        <div class="fix-label">Suggested Fix</div>
                        <div class="fix-text">{pred["fix"]}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if pred["steps"]:
                    with st.expander(f"📋 Steps for: {pred['issue'][:50]}..."):
                        s_html = ""
                        for i, step in enumerate(pred["steps"], 1):
                            s_html += f"""
                            <div class="step-item">
                                <div class="step-number">{i}</div>
                                <div class="step-text">{step}</div>
                            </div>"""
                        st.markdown(s_html, unsafe_allow_html=True)

        # ── Feedback ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(
            '<p style="color: var(--text-primary); font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem;">'
            'Was this diagnosis helpful?</p>',
            unsafe_allow_html=True,
        )
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            helpful = st.radio("Your feedback", ["Yes", "No"], horizontal=True, label_visibility="collapsed")
        comment = st.text_input("Additional comments (optional)")
        if st.button("Submit Feedback"):
            save_feedback(user_input, top["issue"], helpful == "Yes", comment)
            st.success("Thank you for your feedback!")
        st.markdown("</div>", unsafe_allow_html=True)


# ── Search History ────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("View Recent Searches"):
    history = supabase.table("search_history").select("*").order("searched_at", desc=True).limit(10).execute()
    if history.data:
        st.dataframe(pd.DataFrame(history.data), use_container_width=True)
    else:
        st.markdown(
            '<p style="color: var(--text-muted);">No searches yet.</p>',
            unsafe_allow_html=True,
        )


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <strong style="color: var(--text-secondary);">evDOCTOR</strong> — AI-Powered EV Fault Diagnosis<br>
    Built with Ensemble ML &bull; 127+ Fault Codes &bull; 16 EV Subsystems<br><br>
    Made by <a href="https://github.com/1HPdhruv" target="_blank">Dhruv</a> &bull;
    <a href="https://github.com/1HPdhruv/evDOCTOR" target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True)
