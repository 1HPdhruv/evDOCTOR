from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import uuid


# ==========================================================================
# DIAGNOSIS
# ==========================================================================
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
    expert_breakdown: Optional[Dict[str, float]] = None
    search_id: Optional[int] = None


# ==========================================================================
# FEEDBACK
# ==========================================================================
class FeedbackRequest(BaseModel):
    symptom_text: str
    predicted_issue: str
    was_helpful: bool
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    message: str
    feedback_id: int


# ==========================================================================
# SEARCH HISTORY
# ==========================================================================
class SearchHistoryResponse(BaseModel):
    id: int
    symptom_text: str
    predicted_issue: Optional[str] = None
    predicted_code: Optional[str] = None
    confidence: Optional[float] = None
    searched_at: datetime

    class Config:
        from_attributes = True


# ==========================================================================
# USER / AUTH
# ==========================================================================
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# ==========================================================================
# VEHICLE
# ==========================================================================
class VehicleBase(BaseModel):
    make: str
    model: str
    year: int
    vin: Optional[str] = None
    nickname: Optional[str] = None
    color: Optional[str] = None
    mileage: Optional[int] = None
    battery_health: Optional[int] = None
    service_notes: Optional[str] = None
    last_service_date: Optional[datetime] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(VehicleBase):
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None


class VehicleResponse(VehicleBase):
    id: int
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================================================
# SAVED DIAGNOSIS
# ==========================================================================
class SavedDiagnosisCreate(BaseModel):
    search_id: int
    notes: Optional[str] = None


class SavedDiagnosisResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    search_id: int
    notes: Optional[str] = None
    saved_at: datetime

    class Config:
        from_attributes = True
