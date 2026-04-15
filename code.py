import pandas as pd
import numpy as np
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.calibration import CalibratedClassifierCV

# ── Synonym augmentation ─────────────────────────────────────────────────────
SYNONYM_MAP = {
    "not working": ["broken", "dead", "failed", "malfunctioning"],
    "error": ["fault", "issue", "problem", "malfunction"],
    "overheating": ["too hot", "thermal issue", "high temperature"],
    "battery": ["batt", "battery pack", "power cell"],
    "motor": ["drive motor", "electric motor", "traction motor"],
    "noise": ["sound", "whine", "grinding", "humming"],
    "low": ["weak", "insufficient", "poor", "degraded"],
    "not responding": ["offline", "unresponsive", "comm lost"],
    "sensor": ["transducer", "detector", "probe"],
    "leak": ["leaking", "seeping", "dripping"],
}


def augment_text(text):
    """Generate augmented training variants."""
    variants = [text]
    phrases = [p.strip() for p in text.split(",")]
    for _ in range(2):
        shuffled = phrases.copy()
        random.shuffle(shuffled)
        variants.append(", ".join(shuffled))
    for original, synonyms in SYNONYM_MAP.items():
        if original in text.lower():
            for syn in random.sample(synonyms, min(2, len(synonyms))):
                variants.append(text.lower().replace(original, syn))
    return variants


# ── Load and prepare ──────────────────────────────────────────────────────────
df = pd.read_csv("EV_DTC_Dataset.csv")

random.seed(42)
np.random.seed(42)

aug_X, aug_y = [], []
for _, row in df.iterrows():
    augmented = augment_text(row["TrainingText"])
    aug_X.extend(augmented)
    aug_y.extend([row["Description"]] * len(augmented))

# Vectorizer
tfidf = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    sublinear_tf=True,
    max_features=8000,
)
X_vec = tfidf.fit_transform(aug_X)

# Train ensemble
lr = LogisticRegression(max_iter=1000, C=5.0, solver="lbfgs")
sgd = CalibratedClassifierCV(SGDClassifier(loss="modified_huber", max_iter=1000, random_state=42), cv=3)
nb = MultinomialNB(alpha=0.5)

lr.fit(X_vec, aug_y)
sgd.fit(X_vec, aug_y)
nb.fit(X_vec, aug_y)


# ── Prediction ────────────────────────────────────────────────────────────────
def predict_fault(symptom_text, top_k=3):
    """Return top-k predictions from ensemble."""
    vec = tfidf.transform([symptom_text])

    proba_lr = lr.predict_proba(vec)[0]
    proba_sgd = sgd.predict_proba(vec)[0]
    proba_nb = nb.predict_proba(vec)[0]

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
            "rank": len(results) + 1,
            "issue": desc,
            "code": row["Code"],
            "confidence": round(conf * 100, 1),
            "severity": row.get("Severity", "Medium"),
            "category": row.get("Category", "General"),
            "fix": row["Solution"],
            "steps": steps,
        })

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────
SEVERITY_COLORS = {
    "Critical": "\033[91m",  # Red
    "High": "\033[93m",      # Yellow
    "Medium": "\033[33m",    # Orange-ish
    "Low": "\033[92m",       # Green
}
RESET = "\033[0m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"

print()
print(f"{CYAN}{BOLD}{'='*60}{RESET}")
print(f"{CYAN}{BOLD}  evDOCTOR — AI EV Fault Diagnosis (Ensemble Model){RESET}")
print(f"{CYAN}{BOLD}{'='*60}{RESET}")
print(f"{DIM}  {len(df)} fault codes | 3 ML models | Type 'quit' to exit{RESET}")
print()

while True:
    user_input = input(f"{BOLD}Describe symptoms: {RESET}").strip()
    if user_input.lower() in ["quit", "exit", "q"]:
        print(f"\n{CYAN}Goodbye!{RESET}\n")
        break

    if not user_input:
        print(f"{DIM}  Please enter some symptoms.{RESET}\n")
        continue

    results = predict_fault(user_input)

    print(f"\n{CYAN}{BOLD}{'─'*60}{RESET}")
    print(f"{CYAN}{BOLD}  DIAGNOSIS RESULTS{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}\n")

    for pred in results:
        sev_color = SEVERITY_COLORS.get(pred["severity"], "")
        conf_bar = "█" * int(pred["confidence"] / 5) + "░" * (20 - int(pred["confidence"] / 5))

        print(f"  {BOLD}#{pred['rank']}  [{pred['code']}]  {pred['issue']}{RESET}")
        print(f"      Severity: {sev_color}{BOLD}{pred['severity']}{RESET}  |  Category: {pred['category']}")
        print(f"      Confidence: {pred['confidence']}%  {DIM}{conf_bar}{RESET}")
        print(f"      Fix: {pred['fix']}")

        if pred["steps"]:
            print(f"      {DIM}Steps:{RESET}")
            for i, step in enumerate(pred["steps"], 1):
                print(f"        {CYAN}{i}.{RESET} {step}")

        print()

    print(f"{'─'*60}\n")
