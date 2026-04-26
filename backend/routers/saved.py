"""
==========================================================================
  SAVED DIAGNOSES ROUTER — Bookmark Management
  --------------------------------------------------------------------------
  Allows authenticated users to save and retrieve diagnosis bookmarks.
==========================================================================
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from database import get_db
import models
from auth import require_user

router = APIRouter(prefix="/api/saved", tags=["saved"])


class SaveIn(BaseModel):
    search_id: int
    notes: Optional[str] = None


class SavedOut(BaseModel):
    id: int
    search_id: int
    notes: Optional[str]
    saved_at: datetime
    symptom_text: Optional[str] = None
    predicted_issue: Optional[str] = None
    predicted_code: Optional[str] = None
    confidence: Optional[float] = None
    class Config:
        from_attributes = True


@router.get("", response_model=List[SavedOut])
def list_saved(
    current_user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """List all saved diagnoses for the current user."""
    rows = (
        db.query(models.SavedDiagnosis)
        .filter(models.SavedDiagnosis.user_id == current_user.id)
        .order_by(models.SavedDiagnosis.saved_at.desc())
        .all()
    )
    result = []
    for row in rows:
        search = row.search
        result.append(SavedOut(
            id=row.id,
            search_id=row.search_id,
            notes=row.notes,
            saved_at=row.saved_at,
            symptom_text=search.symptom_text if search else None,
            predicted_issue=search.predicted_issue if search else None,
            predicted_code=search.predicted_code if search else None,
            confidence=search.confidence if search else None,
        ))
    return result


@router.post("", status_code=201)
def save_diagnosis(
    data: SaveIn,
    current_user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Bookmark a diagnosis."""
    # Check search exists
    search = db.query(models.SearchHistory).filter(models.SearchHistory.id == data.search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    # Upsert (unique constraint on user_id + search_id)
    existing = db.query(models.SavedDiagnosis).filter(
        models.SavedDiagnosis.user_id == current_user.id,
        models.SavedDiagnosis.search_id == data.search_id,
    ).first()
    if existing:
        existing.notes = data.notes
        db.commit()
        return {"message": "Updated", "id": existing.id}
    saved = models.SavedDiagnosis(user_id=current_user.id, search_id=data.search_id, notes=data.notes)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return {"message": "Saved", "id": saved.id}


@router.delete("/{saved_id}", status_code=204)
def delete_saved(
    saved_id: int,
    current_user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Remove a saved diagnosis bookmark."""
    row = db.query(models.SavedDiagnosis).filter(
        models.SavedDiagnosis.id == saved_id,
        models.SavedDiagnosis.user_id == current_user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(row)
    db.commit()
