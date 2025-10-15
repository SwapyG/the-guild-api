# app/auth.py (Updated for Skill Ledger)

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

# --- Security Configuration ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# --- Core Auth Functions ---


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

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


# --- THIS FUNCTION IS NOW UPGRADED ---
def get_user(db: Session, email: str) -> Optional[models.User]:
    """
    Fetches a user from the database by their email,
    eagerly loading their skills and skill details in the same query.
    """
    return (
        db.query(models.User)
        .options(joinedload(models.User.skills).joinedload(models.UserSkill.skill))
        .filter(models.User.email == email)
        .first()
    )


# ------------------------------------


# --- RBAC Security Dependencies ---


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    """
    Decodes the token, validates the user, and returns the complete user object.
    """
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
        role: Optional[str] = payload.get("role")
        if email is None or role is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email, role=role)
    except JWTError:
        raise credentials_exception

    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_manager_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """Dependency that ensures the user is a 'Manager' or 'Admin'."""
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
    """Dependency that ensures the user is an 'Admin'."""
    if current_user.role != models.UserRoleEnum.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Requires Admin role.",
        )
    return current_user
