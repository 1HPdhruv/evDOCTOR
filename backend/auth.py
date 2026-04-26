"""
==========================================================================
  AUTH MODULE — JWT-Based Authentication
  --------------------------------------------------------------------------
  Provides user registration, login, and identity verification.
  Uses stdlib hashlib PBKDF2-SHA256 for password hashing (no bcrypt dep)
  and python-jose for JWTs.
==========================================================================
"""

import os
import hashlib
import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models

SECRET_KEY = os.environ.get("SECRET_KEY", "evtroubleshooter-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# ---------------------------------------------------------------------------
# Password hashing — PBKDF2-SHA256 via stdlib (no external dep issues)
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = _secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"pbkdf2$sha256$260000${salt}${key.hex()}"

def verify_password(plain: str, stored: str) -> bool:
    try:
        _, algo, iters, salt, key_hex = stored.split("$")
        key = hashlib.pbkdf2_hmac(algo, plain.encode(), salt.encode(), int(iters))
        return key.hex() == key_hex
    except Exception:
        return False

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    full_name: Optional[str]

class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


# ---------------------------------------------------------------------------
# Dependency — get current user from token (returns None if unauthenticated)
# ---------------------------------------------------------------------------
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[models.User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None
    return get_user_by_email(db, email)

def require_user(current_user: Optional[models.User] = Depends(get_current_user)):
    """Dependency that raises 401 if not authenticated."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return current_user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/register", response_model=LoginResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email})
    return LoginResponse(access_token=token, user_id=user.id, email=user.email, full_name=user.full_name)


@router.post("/login", response_model=LoginResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email + password, returns JWT."""
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.email})
    return LoginResponse(access_token=token, user_id=user.id, email=user.email, full_name=user.full_name)


@router.get("/me", response_model=UserOut)
def get_me(current_user: models.User = Depends(require_user)):
    """Get current authenticated user profile."""
    return current_user
