# app/schemas.py (FINAL, COMPLETE VERSION with Skill Ledger)

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

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


# --- NEW: Schema for the User-Skill relationship (used in User profile) ---
class UserSkill(BaseModel):
    skill: Skill
    proficiency: SkillProficiencyEnum

    class Config(Config):
        pass


# ----------------------------------------------------

# ------------------- User Schemas -------------------


class UserBase(BaseModel):
    name: str
    email: str
    title: str
    photo_url: Optional[str] = None


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: uuid.UUID
    role: UserRoleEnum
    skills: List[UserSkill] = []  # <-- UPDATED: User profile now includes skills

    class Config(Config):
        pass


# --- NEW: Schema for adding/updating a skill for a user ---
class UserSkillCreate(BaseModel):
    skill_id: uuid.UUID
    proficiency: SkillProficiencyEnum


# --------------------------------------------------------

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


class MissionUpdateStatus(BaseModel):
    status: MissionStatusEnum


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


# ------------------- Token Schemas -------------------


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRoleEnum] = None
