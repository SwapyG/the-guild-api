# app/schemas.py (Updated for Authentication)

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from .models import SkillProficiencyEnum, MissionStatusEnum, PitchStatusEnum


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
    # This schema is used when creating a new user (e.g., registration).
    # It includes the password field.
    password: str


class User(UserBase):
    # This is the public-facing user schema.
    # Notice it inherits from UserBase and does NOT include the password.
    # This ensures we never accidentally send a password hash to the client.
    id: uuid.UUID

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
    # lead_user_id is NOT here because it's determined by the token
    roles: List[MissionRoleBase] = []


class Mission(MissionBase):
    id: uuid.UUID
    created_at: datetime
    lead: User
    lead_user_id: uuid.UUID  # It IS here for reading data
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


# ------------------- NEW: Token Schemas -------------------
# These schemas define the shape of the JWT and its payload.


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# --------------------------------------------------------
