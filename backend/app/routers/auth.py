from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import Session as DBSession
from sqlmodel import select

from ..database import get_session
from ..models import Session as AuthSession
from ..models import User, utcnow

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_DAYS = 30
PBKDF2_ROUNDS = 200_000


# ── password hashing (stdlib pbkdf2) ─────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return hmac.compare_digest(dk.hex(), expected)


# ── session helpers ──────────────────────────────────────

def create_session(db: DBSession, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token=token,
            user_id=user.id,
            expires_at=utcnow().replace(tzinfo=None) + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return token


def get_current_user(
    x_auth_token: str | None = Header(default=None),
    db: DBSession = Depends(get_session),
) -> User:
    if not x_auth_token:
        raise HTTPException(401, "Not authenticated")
    sess = db.get(AuthSession, x_auth_token)
    if not sess:
        raise HTTPException(401, "Invalid session")
    if sess.expires_at and sess.expires_at < utcnow().replace(tzinfo=None):
        db.delete(sess)
        db.commit()
        raise HTTPException(401, "Session expired")
    user = db.get(User, sess.user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user


# ── schemas ──────────────────────────────────────────────

class Credentials(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str


# ── routes ───────────────────────────────────────────────

@router.post("/signup", response_model=AuthResponse)
def signup(payload: Credentials, db: DBSession = Depends(get_session)):
    email = payload.email.lower().strip()
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    existing = db.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(409, "An account with that email already exists")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session(db, user)
    return AuthResponse(token=token, email=user.email)


@router.post("/login", response_model=AuthResponse)
def login(payload: Credentials, db: DBSession = Depends(get_session)):
    email = payload.email.lower().strip()
    user = db.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_session(db, user)
    return AuthResponse(token=token, email=user.email)


@router.post("/logout")
def logout(
    x_auth_token: str | None = Header(default=None),
    db: DBSession = Depends(get_session),
):
    if x_auth_token:
        sess = db.get(AuthSession, x_auth_token)
        if sess:
            db.delete(sess)
            db.commit()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "id": user.id}
