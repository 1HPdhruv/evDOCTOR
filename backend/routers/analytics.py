"""
==========================================================================
  ANALYTICS ROUTER — Fault Trend Dashboard
  --------------------------------------------------------------------------
  Provides aggregated statistics for the admin/analytics dashboard.
==========================================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta, timezone
from typing import List
from pydantic import BaseModel

from database import get_db
import models

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class TopFaultItem(BaseModel):
    code: str
    issue: str
    count: int
    category: str
    severity: str


class DistributionItem(BaseModel):
    label: str
    count: int


class DailyItem(BaseModel):
    date: str
    count: int


@router.get("/top-faults", response_model=List[TopFaultItem])
def top_faults(limit: int = 10, db: Session = Depends(get_db)):
    """Top N most diagnosed fault codes."""
    rows = (
        db.query(
            models.SearchHistory.predicted_code,
            models.SearchHistory.predicted_issue,
            func.count(models.SearchHistory.id).label("count"),
        )
        .filter(models.SearchHistory.predicted_code.isnot(None))
        .group_by(models.SearchHistory.predicted_code, models.SearchHistory.predicted_issue)
        .order_by(desc("count"))
        .limit(limit)
        .all()
    )
    result = []
    for code, issue, count in rows:
        fault = db.query(models.FaultCode).filter(models.FaultCode.code == code).first()
        result.append(TopFaultItem(
            code=code or "",
            issue=issue or "",
            count=count,
            category=fault.category if fault else "Unknown",
            severity=fault.severity if fault else "Unknown",
        ))
    return result


@router.get("/severity-distribution", response_model=List[DistributionItem])
def severity_distribution(db: Session = Depends(get_db)):
    """Count of searches by severity level."""
    rows = (
        db.query(models.FaultCode.severity, func.count(models.SearchHistory.id).label("count"))
        .join(models.SearchHistory, models.SearchHistory.fault_id == models.FaultCode.id, isouter=True)
        .group_by(models.FaultCode.severity)
        .order_by(desc("count"))
        .all()
    )
    return [DistributionItem(label=r[0] or "Unknown", count=r[1]) for r in rows]


@router.get("/category-distribution", response_model=List[DistributionItem])
def category_distribution(db: Session = Depends(get_db)):
    """Count of searches by EV subsystem category."""
    rows = (
        db.query(models.FaultCode.category, func.count(models.SearchHistory.id).label("count"))
        .join(models.SearchHistory, models.SearchHistory.fault_id == models.FaultCode.id, isouter=True)
        .group_by(models.FaultCode.category)
        .order_by(desc("count"))
        .all()
    )
    return [DistributionItem(label=r[0] or "Unknown", count=r[1]) for r in rows]


@router.get("/daily-searches", response_model=List[DailyItem])
def daily_searches(days: int = 7, db: Session = Depends(get_db)):
    """Search volume per day over the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(
            func.date(models.SearchHistory.searched_at).label("date"),
            func.count(models.SearchHistory.id).label("count"),
        )
        .filter(models.SearchHistory.searched_at >= cutoff)
        .group_by(func.date(models.SearchHistory.searched_at))
        .order_by("date")
        .all()
    )
    return [DailyItem(date=str(r[0]), count=r[1]) for r in rows]


@router.get("/stats")
def overall_stats(db: Session = Depends(get_db)):
    """Overall platform statistics."""
    return {
        "total_fault_codes": db.query(models.FaultCode).count(),
        "total_searches": db.query(models.SearchHistory).count(),
        "total_feedback": db.query(models.Feedback).count(),
        "total_users": db.query(models.User).count(),
        "helpful_feedback_pct": _pct_helpful(db),
    }


def _pct_helpful(db: Session) -> float:
    total = db.query(models.Feedback).count()
    if total == 0:
        return 0.0
    helpful = db.query(models.Feedback).filter(models.Feedback.was_helpful == True).count()
    return round(helpful / total * 100, 1)
