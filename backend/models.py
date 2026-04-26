"""
==========================================================================
  ORM MODELS — evTROUBLESHOOTER Database Schema (v2)
  --------------------------------------------------------------------------
  Full DBMS concept coverage across 8 tables:
    FaultCode, SearchHistory, Feedback (existing, enhanced)
    User, Vehicle, SavedDiagnosis, ActiveLearningQueue, DiagnosisShare (new)

  DBMS Concepts:
    PK, FK, Unique, NOT NULL, CHECK, Default, Index (single + composite),
    Relationships (1:N, N:1), Cascade Delete, ON DELETE SET NULL/CASCADE
==========================================================================
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime,
    ForeignKey, CheckConstraint, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


def _now():
    return datetime.now(timezone.utc)


# ==========================================================================
# TABLE 1: FaultCode  (master reference table)
# ==========================================================================
class FaultCode(Base):
    __tablename__ = "fault_codes"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    code        = Column(String(10), unique=True, nullable=False, index=True)
    description = Column(String(200), nullable=False)
    category    = Column(String(50),  nullable=False, index=True)
    severity    = Column(String(20),  nullable=False)
    solution    = Column(Text, nullable=False)
    steps       = Column(Text, nullable=True)   # pipe-separated
    training_text = Column(Text, nullable=True)

    # DBMS: Relationships — one FaultCode → many searches, shares
    searches = relationship("SearchHistory", back_populates="fault", cascade="all, delete-orphan")
    shares   = relationship("DiagnosisShare", back_populates="fault_code")

    __table_args__ = (
        CheckConstraint(
            "severity IN ('Critical','High','Medium','Low')",
            name="ck_fault_severity",
        ),
    )

    def __repr__(self):
        return f"<FaultCode code='{self.code}'>"


# ==========================================================================
# TABLE 2: User  (auth table)
# DBMS: Unique on email, NOT NULL on password_hash, Default on created_at
# ==========================================================================
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(120), nullable=True)
    created_at    = Column(DateTime, default=_now, nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)

    # DBMS: 1:N Relationships (parent → children)
    vehicles       = relationship("Vehicle", back_populates="user", cascade="all, delete-orphan")
    saved_diagnoses = relationship("SavedDiagnosis", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User email='{self.email}'>"


# ==========================================================================
# TABLE 3: Vehicle  (garage table)
# DBMS: FK → users.id (CASCADE), composite index on (user_id, make, model)
# ==========================================================================
class Vehicle(Base):
    __tablename__ = "vehicles"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    make       = Column(String(60), nullable=False)    # e.g. Tesla
    model      = Column(String(60), nullable=False)    # e.g. Model 3
    year       = Column(Integer,    nullable=False)    # e.g. 2022
    vin        = Column(String(17), nullable=True)     # Vehicle Identification Number
    nickname   = Column(String(60), nullable=True)     # user-defined label
    created_at = Column(DateTime, default=_now, nullable=False)

    user = relationship("User", back_populates="vehicles")

    __table_args__ = (
        # DBMS: Composite Index — fast lookup of all vehicles for a user
        Index("ix_vehicle_user_make_model", "user_id", "make", "model"),
        # DBMS: CHECK — year must be reasonable
        CheckConstraint("year >= 2000 AND year <= 2035", name="ck_vehicle_year"),
    )

    def __repr__(self):
        return f"<Vehicle {self.year} {self.make} {self.model}>"


# ==========================================================================
# TABLE 4: SearchHistory  (diagnosis log)
# DBMS: FK → fault_codes.id (SET NULL), FK → users.id (SET NULL), composite index
# ==========================================================================
class SearchHistory(Base):
    __tablename__ = "search_history"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    symptom_text    = Column(Text, nullable=False, index=True)
    fault_id        = Column(Integer, ForeignKey("fault_codes.id", ondelete="SET NULL"), nullable=True)
    user_id         = Column(Integer, ForeignKey("users.id",  ondelete="SET NULL"), nullable=True)
    predicted_issue = Column(String(200), nullable=True)
    predicted_code  = Column(String(10),  nullable=True)
    confidence      = Column(Float,  nullable=True)
    # Expert mode: per-model breakdown stored as JSON string
    model_breakdown = Column(Text, nullable=True)
    searched_at     = Column(DateTime, default=_now, nullable=False, index=True)

    # DBMS: Relationships
    fault    = relationship("FaultCode", back_populates="searches")
    feedbacks = relationship("Feedback", back_populates="search", cascade="all, delete-orphan")
    saved     = relationship("SavedDiagnosis", back_populates="search", cascade="all, delete-orphan")
    share     = relationship("DiagnosisShare", back_populates="search", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_search_code_time", "predicted_code", "searched_at"),
    )

    def __repr__(self):
        return f"<SearchHistory id={self.id} code='{self.predicted_code}'>"


# ==========================================================================
# TABLE 5: Feedback  (user ratings)
# DBMS: FK → search_history.id (CASCADE), NOT NULL on was_helpful
# ==========================================================================
class Feedback(Base):
    __tablename__ = "feedback"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    search_id       = Column(Integer, ForeignKey("search_history.id", ondelete="CASCADE"), nullable=True)
    symptom_text    = Column(Text, nullable=True)
    predicted_issue = Column(String(200), nullable=True)
    was_helpful     = Column(Boolean, nullable=False)
    comment         = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=_now, nullable=False)

    search = relationship("SearchHistory", back_populates="feedbacks")

    def __repr__(self):
        return f"<Feedback id={self.id} helpful={self.was_helpful}>"


# ==========================================================================
# TABLE 6: SavedDiagnosis  (bookmarks)
# DBMS: FK → users.id (CASCADE), FK → search_history.id (CASCADE)
#        Unique(user_id, search_id) — user can save a diagnosis only once
# ==========================================================================
class SavedDiagnosis(Base):
    __tablename__ = "saved_diagnoses"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id",          ondelete="CASCADE"), nullable=False)
    search_id  = Column(Integer, ForeignKey("search_history.id", ondelete="CASCADE"), nullable=False)
    notes      = Column(Text, nullable=True)
    saved_at   = Column(DateTime, default=_now, nullable=False)

    user   = relationship("User",          back_populates="saved_diagnoses")
    search = relationship("SearchHistory", back_populates="saved")

    __table_args__ = (
        # DBMS: Unique Constraint — no duplicate bookmarks
        UniqueConstraint("user_id", "search_id", name="uq_saved_user_search"),
    )

    def __repr__(self):
        return f"<SavedDiagnosis user={self.user_id} search={self.search_id}>"


# ==========================================================================
# TABLE 7: ActiveLearningQueue  (wrong predictions for future retraining)
# DBMS: Simple table, index on rejected_at for batch processing
# ==========================================================================
class ActiveLearningQueue(Base):
    __tablename__ = "active_learning_queue"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    symptom_text = Column(Text, nullable=False)
    feedback_comment = Column(Text, nullable=True)
    rejected_at  = Column(DateTime, default=_now, nullable=False, index=True)
    processed    = Column(Boolean, default=False, nullable=False)  # True after retraining

    def __repr__(self):
        return f"<ActiveLearningQueue id={self.id} processed={self.processed}>"


# ==========================================================================
# TABLE 8: DiagnosisShare  (shareable public links)
# DBMS: Unique slug, FK → search_history.id (CASCADE), FK → fault_codes.id (SET NULL)
# ==========================================================================
class DiagnosisShare(Base):
    __tablename__ = "diagnosis_shares"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    slug        = Column(String(16), unique=True, nullable=False, index=True)
    search_id   = Column(Integer, ForeignKey("search_history.id", ondelete="CASCADE"), nullable=False)
    fault_code_id = Column(Integer, ForeignKey("fault_codes.id",  ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime, default=_now, nullable=False)

    search     = relationship("SearchHistory", back_populates="share")
    fault_code = relationship("FaultCode",     back_populates="shares")

    def __repr__(self):
        return f"<DiagnosisShare slug='{self.slug}'>"
