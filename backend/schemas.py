from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class DiagnosisRequest(BaseModel):
    symptom_text: str


class DiagnosisResult(BaseModel):
    issue: str
    code: str
    confidence: float
    severity: str
    category: str
    fix: str
    steps: List[str]
    fault_id: Optional[int] = None


class DiagnosisResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    results: Optional[List[DiagnosisResult]] = None
    expert_breakdown: Optional[Dict[str, float]] = None  # LR, SGD, NB per-model scores
    search_id: Optional[int] = None                      # For saving/sharing


class FeedbackRequest(BaseModel):
    symptom_text: str
    predicted_issue: str
    was_helpful: bool
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    message: str
    feedback_id: int


class SearchHistoryResponse(BaseModel):
    id: int
    symptom_text: str
    predicted_issue: Optional[str] = None
    predicted_code: Optional[str] = None
    confidence: Optional[float] = None
    searched_at: datetime

    class Config:
        from_attributes = True
