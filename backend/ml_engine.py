"""
==========================================================================
  ML ENGINE v2 — joblib Model Persistence + Expert Mode
  --------------------------------------------------------------------------
  Changes from v1:
    - Save trained model to model_cache/model.pkl with joblib
    - Load from cache on startup (skip retraining if fault count unchanged)
    - Return per-model breakdown (LR%, SGD%, NB%) for Expert Mode
==========================================================================
"""

import os
import json
import numpy as np
import random
import re
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.calibration import CalibratedClassifierCV
from sqlalchemy.orm import Session
from models import FaultCode

# Cache directory alongside this file
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "model.pkl")
CACHE_META = os.path.join(CACHE_DIR, "meta.json")


class MLEngine:
    """Ensemble ML engine with joblib caching and expert mode breakdown."""

    def __init__(self):
        self.tfidf = None
        self.lr = None
        self.sgd = None
        self.nb = None
        self.is_trained = False
        self.confidence_threshold = 0.15

    # ── EV keyword set for OOD detection ──
    EV_KEYWORDS = {
        "battery", "motor", "inverter", "charger", "charging", "brake", "steering",
        "sensor", "voltage", "current", "temperature", "coolant", "pump", "fan",
        "fuse", "relay", "contactor", "bms", "ecu", "module", "controller",
        "hvac", "heater", "compressor", "ac", "air", "cooling", "thermal",
        "regenerative", "regen", "power", "drive", "drivetrain", "gearbox",
        "suspension", "damper", "shock", "wheel", "bearing", "cv", "axle",
        "abs", "eps", "horn", "wiper", "window", "door", "lock", "light",
        "airbag", "seatbelt", "camera", "radar", "parking", "cruise", "lane",
        "blind", "collision", "warning", "fault", "error", "noise", "vibration",
        "leak", "overheating", "not working", "broken", "dead", "failed", "hot",
        "cold", "low", "high", "range", "mileage", "soc", "soh", "charge",
        "discharge", "12v", "hv", "connector", "wiring", "cable", "insulation",
        "software", "update", "speed", "acceleration", "torque", "efficiency",
        "converter", "obc", "ccs", "chademo", "plug", "port", "tpms", "tire",
        "pressure", "key", "fob", "obd", "resolver", "stator", "rotor",
        "winding", "phase", "igbt", "capacitor", "derating", "reduced",
    }

    SYNONYM_MAP = {
        "not working": ["broken", "dead", "failed", "malfunctioning", "inoperative"],
        "error": ["fault", "issue", "problem", "malfunction", "failure"],
        "overheating": ["too hot", "thermal issue", "high temperature", "overheat"],
        "battery": ["batt", "battery pack", "power cell", "accumulator"],
        "motor": ["drive motor", "electric motor", "traction motor"],
        "charger": ["charging unit", "obc", "onboard charger"],
        "noise": ["sound", "whine", "grinding", "humming", "clicking"],
        "low": ["weak", "insufficient", "poor", "degraded", "reduced"],
        "not responding": ["offline", "unresponsive", "comm lost", "disconnected"],
        "sensor": ["transducer", "detector", "probe"],
        "leak": ["leaking", "seeping", "dripping", "fluid loss"],
        "warning": ["alert", "alarm", "indicator", "light on"],
        "fault": ["error", "issue", "problem", "defect"],
        "vibration": ["shaking", "trembling", "oscillation", "shudder"],
    }

    def _has_ev_relevance(self, text: str) -> bool:
        text_lower = text.lower()
        for kw in self.EV_KEYWORDS:
            if kw in text_lower:
                return True
        return False

    def augment_text(self, text: str) -> list:
        variants = [text]
        if not isinstance(text, str) or not text.strip():
            return variants
        phrases = [p.strip() for p in text.split(",")]
        for _ in range(3):
            shuffled = phrases.copy()
            random.shuffle(shuffled)
            variants.append(", ".join(shuffled))
        for original, synonyms in self.SYNONYM_MAP.items():
            if original in text.lower():
                for syn in random.sample(synonyms, min(2, len(synonyms))):
                    variants.append(text.lower().replace(original, syn))
        variants.append(text.lower())
        seen, unique = set(), []
        for v in variants:
            if v not in seen:
                seen.add(v); unique.append(v)
        return unique

    # ── Cache helpers ──
    def _save_cache(self, fault_count: int):
        os.makedirs(CACHE_DIR, exist_ok=True)
        payload = {
            "tfidf": self.tfidf,
            "lr": self.lr,
            "sgd": self.sgd,
            "nb": self.nb,
        }
        joblib.dump(payload, CACHE_FILE)
        with open(CACHE_META, "w") as f:
            json.dump({"fault_count": fault_count}, f)
        print(f"[ML Engine] Model saved to cache (fault_count={fault_count}).")

    def _load_cache(self, fault_count: int) -> bool:
        """Returns True if cache is valid and loaded successfully."""
        if not os.path.exists(CACHE_FILE) or not os.path.exists(CACHE_META):
            return False
        try:
            with open(CACHE_META) as f:
                meta = json.load(f)
            if meta.get("fault_count") != fault_count:
                print("[ML Engine] Cache invalidated — fault count changed.")
                return False
            payload = joblib.load(CACHE_FILE)
            self.tfidf = payload["tfidf"]
            self.lr    = payload["lr"]
            self.sgd   = payload["sgd"]
            self.nb    = payload["nb"]
            self.is_trained = True
            print(f"[ML Engine] Loaded from cache (fault_count={fault_count}).")
            return True
        except Exception as e:
            print(f"[ML Engine] Cache load failed: {e}")
            return False

    def train(self, db: Session):
        faults = db.query(FaultCode).all()
        if not faults:
            print("[ML Engine] No data to train on.")
            return

        # Try cache first
        if self._load_cache(len(faults)):
            return

        random.seed(42); np.random.seed(42)

        aug_X, aug_y = [], []
        for row in faults:
            if not row.training_text:
                continue
            for variant in self.augment_text(row.training_text):
                aug_X.append(variant)
                aug_y.append(row.description)

        if not aug_X:
            return

        print(f"[ML Engine] Training on {len(aug_X)} samples ({len(faults)} fault codes)...")

        self.tfidf = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2),
            sublinear_tf=True, max_features=10000, min_df=1,
        )
        X_vec = self.tfidf.fit_transform(aug_X)

        self.lr = LogisticRegression(max_iter=2000, C=5.0, solver="lbfgs")
        self.lr.fit(X_vec, aug_y)

        base_sgd = SGDClassifier(loss="modified_huber", max_iter=2000, random_state=42)
        base_sgd.fit(X_vec, aug_y)
        self.sgd = CalibratedClassifierCV(estimator=base_sgd, cv="prefit")
        self.sgd.fit(X_vec, aug_y)

        self.nb = MultinomialNB(alpha=0.3)
        self.nb.fit(X_vec, aug_y)

        self.is_trained = True
        print("[ML Engine] Training complete.")
        self._save_cache(len(faults))

    def predict(self, symptom_text: str, db: Session, top_k: int = 3) -> dict:
        if not self.is_trained:
            self.train(db)
            if not self.is_trained:
                return {"success": False, "message": "Model not initialized."}

        cleaned = symptom_text.strip()
        if len(cleaned) < 3:
            return {"success": False, "message": "Input too short. Please describe your EV symptoms."}

        if not self._has_ev_relevance(cleaned):
            return {
                "success": False,
                "message": "Invalid input. Please describe an EV-related issue (e.g. 'battery not charging', 'motor noise').",
            }

        vec = self.tfidf.transform([cleaned])
        proba_lr  = self.lr.predict_proba(vec)[0]
        proba_sgd = self.sgd.predict_proba(vec)[0]
        proba_nb  = self.nb.predict_proba(vec)[0]

        # Weighted ensemble
        avg_proba = 0.45 * proba_lr + 0.30 * proba_sgd + 0.25 * proba_nb

        # Temperature scaling
        T = 0.3
        avg_proba = np.power(avg_proba + 1e-12, 1 / T)
        avg_proba = avg_proba / np.sum(avg_proba)

        max_confidence = float(np.max(avg_proba))
        if max_confidence < self.confidence_threshold:
            return {"success": False, "message": "Confidence too low. Please describe the symptom in more detail."}

        classes = self.lr.classes_
        top_indices = np.argsort(avg_proba)[::-1][:top_k]

        # ── Expert mode: per-model breakdown for top prediction ──
        top_idx = top_indices[0]
        # Scale individual model probas with same temperature
        def _scale(p):
            p = np.power(p + 1e-12, 1 / T)
            return p / np.sum(p)
        s_lr  = _scale(proba_lr)
        s_sgd = _scale(proba_sgd)
        s_nb  = _scale(proba_nb)
        expert_breakdown = {
            "lr":  round(float(s_lr[top_idx]),  4),
            "sgd": round(float(s_sgd[top_idx]), 4),
            "nb":  round(float(s_nb[top_idx]),  4),
        }

        results = []
        for idx in top_indices:
            desc = classes[idx]
            conf = float(avg_proba[idx])
            row  = db.query(FaultCode).filter(FaultCode.description == desc).first()
            if not row:
                continue
            steps = [s.strip() for s in str(row.steps).split("|") if s.strip()] if row.steps else []
            results.append({
                "issue":     desc,
                "code":      row.code,
                "confidence": round(conf, 4),
                "severity":  row.severity or "Medium",
                "category":  row.category or "General",
                "fix":       row.solution,
                "steps":     steps,
                "fault_id":  row.id,
            })

        if not results:
            return {"success": False, "message": "No matching fault codes found."}

        return {"success": True, "results": results, "expert_breakdown": expert_breakdown}


ml_engine = MLEngine()
