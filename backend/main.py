"""
==========================================================================
  evTROUBLESHOOTER BACKEND v2 — FastAPI Application
  --------------------------------------------------------------------------
  Endpoints:
    POST /api/diagnose          — ML diagnosis
    GET  /api/history           — Recent searches
    POST /api/feedback          — Submit feedback
    GET  /api/lookup/{code}     — OBD-II direct code lookup
    GET  /api/autocomplete      — Symptom autocomplete
    POST /api/share             — Create shareable diagnosis link
    GET  /api/share/{slug}      — Retrieve shared diagnosis
    POST /api/auth/register     — Register
    POST /api/auth/login        — Login
    GET  /api/auth/me           — Current user
    CRUD /api/vehicles          — Garage management
    CRUD /api/saved             — Saved diagnoses
    GET  /api/analytics/*       — Dashboard analytics
==========================================================================
"""

import os
import json
import secrets
from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import models
import schemas
from database import engine, get_db
from ml_engine import ml_engine
from auth import router as auth_router, get_current_user
from routers.vehicles import router as vehicles_router
from routers.saved import router as saved_router
from routers.analytics import router as analytics_router

# Create all DB tables
models.Base.metadata.create_all(bind=engine)

# ── Rate Limiter ──
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="evTROUBLESHOOTER API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ──
app.include_router(auth_router)
app.include_router(vehicles_router)
app.include_router(saved_router)
app.include_router(analytics_router)

# Pre-build autocomplete suggestions from training data
_autocomplete_suggestions: list = []


@app.on_event("startup")
def startup_event():
    global _autocomplete_suggestions
    from init_db import init_db
    init_db()
    db = next(get_db())
    try:
        ml_engine.train(db)
        # Build autocomplete from training text
        faults = db.query(models.FaultCode).all()
        seen = set()
        for f in faults:
            if f.training_text:
                for phrase in f.training_text.split(","):
                    phrase = phrase.strip().lower()
                    if phrase and phrase not in seen:
                        seen.add(phrase)
                        _autocomplete_suggestions.append(phrase)
        _autocomplete_suggestions.sort()
    finally:
        db.close()


@app.get("/")
def health_check():
    return {"status": "ok", "service": "evTROUBLESHOOTER API", "version": "2.0.0"}


# ==========================================================================
# DIAGNOSIS
# ==========================================================================
@app.post("/api/diagnose", response_model=schemas.DiagnosisResponse)
@limiter.limit("30/minute")
def diagnose(request: Request, req: schemas.DiagnosisRequest, db: Session = Depends(get_db),
             current_user: Optional[models.User] = Depends(get_current_user)):
    """Run ML diagnosis. Rate-limited to 30/min per IP."""
    prediction = ml_engine.predict(req.symptom_text, db)

    if not prediction["success"]:
        return schemas.DiagnosisResponse(success=False, message=prediction["message"])

    results = prediction["results"]
    expert  = prediction.get("expert_breakdown")

    # Save to search history
    history_id = None
    if results:
        top = results[0]
        fault_record = db.query(models.FaultCode).filter(models.FaultCode.code == top["code"]).first()
        history = models.SearchHistory(
            symptom_text=req.symptom_text,
            predicted_issue=top["issue"],
            predicted_code=top["code"],
            confidence=top["confidence"],
            fault_id=fault_record.id if fault_record else None,
            user_id=current_user.id if current_user else None,
            model_breakdown=json.dumps(expert) if expert else None,
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        history_id = history.id

    return schemas.DiagnosisResponse(
        success=True,
        results=results,
        expert_breakdown=expert,
        search_id=history_id,
    )


# ==========================================================================
# FEEDBACK
# ==========================================================================
@app.post("/api/feedback", response_model=schemas.FeedbackResponse)
def submit_feedback(req: schemas.FeedbackRequest, db: Session = Depends(get_db)):
    feedback = models.Feedback(
        symptom_text=req.symptom_text,
        predicted_issue=req.predicted_issue,
        was_helpful=req.was_helpful,
        comment=req.comment,
    )
    db.add(feedback)

    # Active Learning — queue unhelpful predictions for future retraining
    if not req.was_helpful:
        queue_entry = models.ActiveLearningQueue(
            symptom_text=req.symptom_text,
            feedback_comment=req.comment,
        )
        db.add(queue_entry)

    db.commit()
    db.refresh(feedback)
    return schemas.FeedbackResponse(message="Thank you for your feedback!", feedback_id=feedback.id)


# ==========================================================================
# SEARCH HISTORY
# ==========================================================================
@app.get("/api/history", response_model=List[schemas.SearchHistoryResponse])
def get_history(limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)):
    return (
        db.query(models.SearchHistory)
        .order_by(models.SearchHistory.searched_at.desc())
        .limit(limit)
        .all()
    )


# ==========================================================================
# OBD-II CODE LOOKUP
# ==========================================================================
class LookupResponse(BaseModel):
    found: bool
    code: Optional[str] = None
    issue: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    fix: Optional[str] = None
    steps: Optional[List[str]] = None


@app.get("/api/lookup/{code}", response_model=LookupResponse)
def lookup_code(code: str, db: Session = Depends(get_db)):
    """Direct lookup of a DTC code (e.g. P0AC0)."""
    fault = db.query(models.FaultCode).filter(
        models.FaultCode.code == code.upper()
    ).first()
    if not fault:
        return LookupResponse(found=False)
    steps = [s.strip() for s in fault.steps.split("|") if s.strip()] if fault.steps else []
    return LookupResponse(
        found=True,
        code=fault.code,
        issue=fault.description,
        category=fault.category,
        severity=fault.severity,
        fix=fault.solution,
        steps=steps,
    )


# ==========================================================================
# AUTOCOMPLETE
# ==========================================================================
@app.get("/api/autocomplete")
def autocomplete(q: str = Query("", min_length=1), limit: int = 8):
    """Return prefix-matched symptom suggestions."""
    q_lower = q.lower().strip()
    if not q_lower:
        return []
    matches = [s for s in _autocomplete_suggestions if q_lower in s][:limit]
    return matches


# ==========================================================================
# SHAREABLE DIAGNOSIS LINKS
# ==========================================================================
class ShareRequest(BaseModel):
    search_id: int

class ShareResponse(BaseModel):
    slug: str
    url: str

class SharedDiagnosis(BaseModel):
    slug: str
    symptom_text: str
    predicted_issue: Optional[str]
    predicted_code: Optional[str]
    confidence: Optional[float]
    searched_at: str


@app.post("/api/share", response_model=ShareResponse)
def create_share(req: ShareRequest, db: Session = Depends(get_db)):
    """Create a shareable link for a diagnosis."""
    search = db.query(models.SearchHistory).filter(models.SearchHistory.id == req.search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    # Reuse existing share if present
    existing = db.query(models.DiagnosisShare).filter(
        models.DiagnosisShare.search_id == req.search_id
    ).first()
    if existing:
        return ShareResponse(slug=existing.slug, url=f"/share/{existing.slug}")

    slug = secrets.token_urlsafe(8)
    share = models.DiagnosisShare(
        slug=slug,
        search_id=req.search_id,
        fault_code_id=search.fault_id,
    )
    db.add(share)
    db.commit()
    return ShareResponse(slug=slug, url=f"/share/{slug}")


@app.get("/api/share/{slug}", response_model=SharedDiagnosis)
def get_share(slug: str, db: Session = Depends(get_db)):
    """Retrieve a shared diagnosis by its slug."""
    share = db.query(models.DiagnosisShare).filter(models.DiagnosisShare.slug == slug).first()
    if not share or not share.search:
        raise HTTPException(status_code=404, detail="Shared diagnosis not found")
    s = share.search
    return SharedDiagnosis(
        slug=slug,
        symptom_text=s.symptom_text,
        predicted_issue=s.predicted_issue,
        predicted_code=s.predicted_code,
        confidence=s.confidence,
        searched_at=s.searched_at.isoformat(),
    )
