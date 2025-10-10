# app/schemas.py (Updated for RBAC)

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

# --- 1. Import the new UserRoleEnum ---
from .models import (
    SkillProficiencyEnum,
    MissionStatusEnum,
    PitchStatusEnum,
    UserRoleEnum,
)


class Config:
    from_attributes = True


# ------------------- Skill Schemas -------------------


class SkillBase(BaseModel):
    name: str


class SkillCreate(SkillBase):
    pass


class Skill(SkillBase):
    id: uuid.UUID

    class Config(Config):
        pass


# ------------------- User Schemas (UPDATED) -------------------


class UserBase(BaseModel):
    name: str
    email: str
    title: str
    photo_url: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: uuid.UUID
    # --- 2. Add the role field to the User read schema ---
    role: UserRoleEnum

    class Config(Config):
        pass


# ------------------- MissionRole Schemas -------------------


class MissionRoleBase(BaseModel):
    role_description: str
    skill_id_required: uuid.UUID
    proficiency_required: SkillProficiencyEnum


class MissionRoleCreate(MissionRoleBase):
    mission_id: uuid.UUID


class MissionRoleUpdate(BaseModel):
    assignee_user_id: uuid.UUID


class MissionRole(MissionRoleBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    assignee: Optional[User] = None
    required_skill: Skill

    class Config(Config):
        pass


# ------------------- Mission Schemas -------------------


class MissionBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: MissionStatusEnum = MissionStatusEnum.Proposed


class MissionCreate(MissionBase):
    roles: List[MissionRoleBase] = []


class Mission(MissionBase):
    id: uuid.UUID
    created_at: datetime
    lead: User
    lead_user_id: uuid.UUID
    roles: List[MissionRole] = []

    class Config(Config):
        pass


# ------------------- MissionPitch Schemas -------------------


class MissionPitchBase(BaseModel):
    pitch_text: str


class MissionPitchCreate(MissionPitchBase):
    user_id: uuid.UUID


class MissionPitch(MissionPitchBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    user_id: uuid.UUID
    status: PitchStatusEnum
    user: User

    class Config(Config):
        pass


# ------------------- Token Schemas (UPDATED) -------------------


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    # --- 3. Add role to the token payload data ---
    role: Optional[UserRoleEnum] = None


# --------------------------------------------------------
