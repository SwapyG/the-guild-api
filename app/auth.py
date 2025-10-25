# app/auth.py (Production Ready - Diagnostics Removed)

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from . import schemas, models
from .database import get_db
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """
    Fetches a user by email (without extra data) and verifies their password.
    Returns the user object on success, None on failure.
    """
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_with_profile(db: Session, email: str) -> Optional[models.User]:
    """
    Fetches a user by email, eagerly loading all profile relationships.
    """
    return (
        db.query(models.User)
        .options(
            joinedload(models.User.skills).joinedload(models.UserSkill.skill),
            joinedload(models.User.led_missions),
            joinedload(models.User.assigned_roles).joinedload(
                models.MissionRole.mission
            ),
        )
        .filter(models.User.email == email)
        .first()
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_with_profile(db, email=email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_manager_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role not in [
        models.UserRoleEnum.Manager,
        models.UserRoleEnum.Admin,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Requires Manager or Admin role.",
        )
    return current_user


async def get_current_admin_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role != models.UserRoleEnum.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Requires Admin role.",
        )
    return current_user
