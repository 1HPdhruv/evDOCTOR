"""
==========================================================================
  VEHICLES ROUTER — Garage Management
  --------------------------------------------------------------------------
  CRUD endpoints for a user's registered EVs.
  Requires JWT authentication via require_user dependency.
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

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


class VehicleIn(BaseModel):
    make: str
    model: str
    year: int
    vin: Optional[str] = None
    nickname: Optional[str] = None


class VehicleOut(BaseModel):
    id: int
    make: str
    model: str
    year: int
    vin: Optional[str]
    nickname: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


@router.get("", response_model=List[VehicleOut])
def list_vehicles(
    current_user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """List all vehicles in the user's garage."""
    return db.query(models.Vehicle).filter(models.Vehicle.user_id == current_user.id).all()


@router.post("", response_model=VehicleOut, status_code=201)
def add_vehicle(
    data: VehicleIn,
    current_user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Add a new vehicle to the user's garage."""
    vehicle = models.Vehicle(user_id=current_user.id, **data.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=204)
def delete_vehicle(
    vehicle_id: int,
    current_user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Remove a vehicle from the user's garage."""
    vehicle = db.query(models.Vehicle).filter(
        models.Vehicle.id == vehicle_id,
        models.Vehicle.user_id == current_user.id,
    ).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    db.delete(vehicle)
    db.commit()
