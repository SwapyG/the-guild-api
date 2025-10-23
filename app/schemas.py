# app/schemas.py (FINAL - All Phase 1 Features)

import uuid
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal

from .models import (
    SkillProficiencyEnum,
    MissionStatusEnum,
    PitchStatusEnum,
    UserRoleEnum,
)


class Config:
    from_attributes = True


# --- NANO: THIS IS THE MISSING NOTIFICATION SCHEMA ---
class Notification(BaseModel):
    id: uuid.UUID
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config(Config):
        pass


# --------------------------------------------------


class SkillBase(BaseModel):
    name: str


class SkillCreate(SkillBase):
    pass


class Skill(SkillBase):
    id: uuid.UUID

    class Config(Config):
        pass


class UserSkill(BaseModel):
    skill: Skill
    proficiency: SkillProficiencyEnum

    class Config(Config):
        pass


# --- NANO: THIS SCHEMA IS ALSO REQUIRED FOR THE LIVING PROFILE ---
class MissionHistoryItem(BaseModel):
    mission_id: uuid.UUID
    mission_title: str
    role: str
    status: MissionStatusEnum

    class Config(Config):
        pass


# -------------------------------------------------------------


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
    skills: List[UserSkill] = []
    # NANO: THIS FIELD IS ALSO REQUIRED
    mission_history: List[MissionHistoryItem] = []

    class Config(Config):
        pass


class UserSkillCreate(BaseModel):
    skill_id: uuid.UUID
    proficiency: SkillProficiencyEnum


class MissionRoleBase(BaseModel):
    role_description: str
    skill_id_required: uuid.UUID
    proficiency_required: SkillProficiencyEnum


class MissionRoleCreate(MissionRoleBase):
    pass


class MissionRoleUpdate(BaseModel):
    assignee_user_id: uuid.UUID


class MissionRole(MissionRoleBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    assignee: Optional[User] = None
    required_skill: Skill

    class Config(Config):
        pass


class MissionBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: MissionStatusEnum = MissionStatusEnum.Proposed
    budget: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


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


class MissionPitchBase(BaseModel):
    pitch_text: str


class MissionPitchCreate(MissionPitchBase):
    pass


class MissionPitchUpdateStatus(BaseModel):
    status: PitchStatusEnum


class MissionPitch(MissionPitchBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    user_id: uuid.UUID
    status: PitchStatusEnum
    user: User

    class Config(Config):
        pass


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRoleEnum] = None
