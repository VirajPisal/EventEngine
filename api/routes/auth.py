"""
Authentication Routes — Organizer and Participant registration & login
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext

from db.base import get_db_context
from config.settings import settings
from api.deps import get_current_user
from models.user import Organizer, ParticipantAccount
from utils.logger import logger

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Request / Response schemas ────────────────────────────────────────

class OrganizerRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)
    organization: str | None = None


class ParticipantRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Helper ────────────────────────────────────────────────────────────

def _create_jwt(payload: dict) -> str:
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── Organizer endpoints ──────────────────────────────────────────────

@router.post("/organizer/register", status_code=201)
async def register_organizer(body: OrganizerRegisterRequest):
    with get_db_context() as db:
        existing = db.query(Organizer).filter(Organizer.email == body.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered as organizer")

        organizer = Organizer(
            name=body.name,
            email=body.email,
            password_hash=pwd_context.hash(body.password),
            organization=body.organization,
        )
        db.add(organizer)
        db.flush()
        logger.info(f"[AUTH] Organizer registered: {body.email}")
        return {"message": "Organizer registered", "id": organizer.id, "email": organizer.email}


@router.post("/organizer/login")
async def login_organizer(body: LoginRequest):
    with get_db_context() as db:
        organizer = db.query(Organizer).filter(Organizer.email == body.email).first()
        if not organizer or not pwd_context.verify(body.password, organizer.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = _create_jwt({
            "sub": organizer.email,
            "role": "organizer",
            "id": organizer.id,
            "name": organizer.name,
        })
        logger.info(f"[AUTH] Organizer logged in: {body.email}")
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": "organizer",
            "name": organizer.name,
            "email": organizer.email,
        }


# ── Participant endpoints ─────────────────────────────────────────────

@router.post("/participant/register", status_code=201)
async def register_participant(body: ParticipantRegisterRequest):
    with get_db_context() as db:
        existing = db.query(ParticipantAccount).filter(ParticipantAccount.email == body.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered as participant")

        account = ParticipantAccount(
            name=body.name,
            email=body.email,
            password_hash=pwd_context.hash(body.password),
        )
        db.add(account)
        db.flush()
        logger.info(f"[AUTH] Participant registered: {body.email}")
        return {"message": "Participant registered", "id": account.id, "email": account.email}


@router.post("/participant/login")
async def login_participant(body: LoginRequest):
    with get_db_context() as db:
        account = db.query(ParticipantAccount).filter(ParticipantAccount.email == body.email).first()
        if not account or not pwd_context.verify(body.password, account.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = _create_jwt({
            "sub": account.email,
            "role": "participant",
            "id": account.id,
            "name": account.name,
        })
        logger.info(f"[AUTH] Participant logged in: {body.email}")
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": "participant",
            "name": account.name,
            "email": account.email,
        }


# ── Current user ──────────────────────────────────────────────────────

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "email": user.get("sub"),
        "role": user.get("role"),
        "name": user.get("name"),
        "id": user.get("id"),
    }
