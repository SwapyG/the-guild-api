# app/schemas.py (Definitive Fix - The Fortress Wall Protocol)

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
    InviteStatusEnum,
)


class Config:
    from_attributes = True


# --- Base Schemas (simple, for creation, no nested objects) ---


class UserBase(BaseModel):
    name: str
    email: str
    title: str
    photo_url: Optional[str] = None


class SkillBase(BaseModel):
    name: str


class MissionPitchBase(BaseModel):
    pitch_text: str


class MissionBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: MissionStatusEnum = MissionStatusEnum.Proposed
    budget: Optional[Decimal] = Field(None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class MissionRoleBase(BaseModel):
    role_description: str
    skill_id_required: uuid.UUID
    proficiency_required: SkillProficiencyEnum


# --- READ Schemas (for API responses, with nested objects) ---


class Skill(SkillBase):
    id: uuid.UUID

    class Config(Config):
        pass


class User(UserBase):
    id: uuid.UUID
    role: UserRoleEnum

    class Config(Config):
        pass


class UserSkill(BaseModel):
    skill: Skill
    proficiency: SkillProficiencyEnum

    class Config(Config):
        pass


# This is the full User Profile, including skills.
class UserProfile(User):
    skills: List[UserSkill] = []

    class Config(Config):
        pass


# --- NANO: THE FORTRESS WALL ---
# 1. Create a simplified Mission schema for nesting. It has NO relations.
class MissionSimple(MissionBase):
    id: uuid.UUID
    lead_user_id: uuid.UUID

    class Config(Config):
        pass


# 2. The MissionRole schema for READ operations now uses the simplified Mission.
class MissionRole(MissionRoleBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    assignee: Optional[User] = None
    required_skill: Skill
    mission: MissionSimple  # This is the wall. It stops the loop.

    class Config(Config):
        pass


# 3. The full Mission schema for READ operations can safely include the full MissionRole list.
class Mission(MissionBase):
    id: uuid.UUID
    created_at: datetime
    lead: User
    lead_user_id: uuid.UUID
    roles: List[MissionRole] = []
    pitches: List["MissionPitch"] = []  # Forward ref is okay here

    class Config(Config):
        pass


# This schema is used when a user pitches for a mission.
class MissionPitch(MissionPitchBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    user_id: uuid.UUID
    status: PitchStatusEnum
    user: User

    class Config(Config):
        pass


# This is the schema for the "My Invitations" page.
class MissionInvite(BaseModel):
    id: uuid.UUID
    mission_role: MissionRole  # This now uses the safe, non-recursive version
    invited_user: User
    inviting_user: User
    status: InviteStatusEnum
    created_at: datetime

    class Config(Config):
        pass


# --------------------------------


class MissionActionItem(Mission):
    pending_pitches: int = 0


class Notification(BaseModel):
    id: uuid.UUID
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config(Config):
        pass


# --- Schemas for Creating/Updating resources ---


class UserCreate(UserBase):
    password: str


class SkillCreate(SkillBase):
    pass


class UserSkillCreate(BaseModel):
    skill_id: uuid.UUID
    proficiency: SkillProficiencyEnum


class MissionCreate(MissionBase):
    roles: List[MissionRoleBase] = []


class MissionUpdateStatus(BaseModel):
    status: MissionStatusEnum


class MissionPitchCreate(MissionPitchBase):
    pass


class MissionPitchUpdateStatus(BaseModel):
    status: PitchStatusEnum


class MissionRoleUpdate(BaseModel):
    assignee_user_id: uuid.UUID


class MissionInviteCreate(BaseModel):
    mission_role_id: uuid.UUID
    invited_user_id: uuid.UUID


class MissionInviteUpdate(BaseModel):
    status: InviteStatusEnum


# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRoleEnum] = None


# --- Update Forward References ---
Mission.model_rebuild()
