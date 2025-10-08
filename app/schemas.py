# schemas.py

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

# Import the enums from our models file to be used in the schemas
from .models import SkillProficiencyEnum, MissionStatusEnum, PitchStatusEnum


# This Config class is used by Pydantic to configure its behavior.
# `from_attributes = True` tells Pydantic to read the data even if it is not a dict,
# but an ORM model (or any other arbitrary object with attributes).
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


# ------------------- User Schemas -------------------


class UserBase(BaseModel):
    name: str
    email: str
    title: str
    photo_url: Optional[str] = None


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: uuid.UUID

    class Config(Config):
        pass


# ------------------- MissionRole Schemas -------------------
# We define MissionRole schemas before Mission so they can be nested.


class MissionRoleBase(BaseModel):
    role_description: str
    skill_id_required: uuid.UUID
    proficiency_required: SkillProficiencyEnum


class MissionRoleCreate(MissionRoleBase):
    mission_id: uuid.UUID


class MissionRoleUpdate(BaseModel):
    # This schema is specifically for the "drafting" feature
    assignee_user_id: uuid.UUID


class MissionRole(MissionRoleBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    assignee: Optional[User] = None
    required_skill: Skill  # <-- ADD THIS LINE

    class Config(Config):
        pass


# ------------------- Mission Schemas -------------------


class MissionBase(BaseModel):
    title: str
    description: Optional[str] = None
    lead_user_id: uuid.UUID
    status: MissionStatusEnum = MissionStatusEnum.Proposed


class MissionCreate(MissionBase):
    # We can add a list of roles to be created at the same time as the mission
    roles: List[MissionRoleBase] = []


class Mission(MissionBase):
    id: uuid.UUID
    created_at: datetime
    lead: User  # Nested User schema for the lead
    roles: List[MissionRole] = []  # Nested list of MissionRole schemas

    class Config(Config):
        pass


# ------------------- MissionPitch Schemas -------------------


class MissionPitchBase(BaseModel):
    pitch_text: str


class MissionPitchCreate(MissionPitchBase):
    user_id: uuid.UUID  # The user ID will be provided from the request context


class MissionPitch(MissionPitchBase):
    id: uuid.UUID
    mission_id: uuid.UUID
    user_id: uuid.UUID
    status: PitchStatusEnum
    user: User  # Nested User schema for the pitcher

    class Config(Config):
        pass
