# app/models.py

import enum
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Enum, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


# --- NEW: UserRoleEnum for RBAC ---
class UserRoleEnum(str, enum.Enum):
    Member = "Member"
    Manager = "Manager"
    Admin = "Admin"


# ------------------------------------


class SkillProficiencyEnum(str, enum.Enum):
    Beginner = "Beginner"
    Intermediate = "Intermediate"
    Advanced = "Advanced"
    Expert = "Expert"


class MissionStatusEnum(str, enum.Enum):
    Proposed = "Proposed"
    Active = "Active"
    Completed = "Completed"


class PitchStatusEnum(str, enum.Enum):
    Submitted = "Submitted"
    Accepted = "Accepted"
    Rejected = "Rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    photo_url = Column(String(2048))
    title = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)

    # --- THIS IS THE NEWLY ADDED ROLE COLUMN ---
    role = Column(
        Enum(UserRoleEnum, name="user_role"),
        nullable=False,
        server_default=UserRoleEnum.Member.value,
    )
    # -------------------------------------------

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    skills = relationship(
        "UserSkill", back_populates="user", cascade="all, delete-orphan"
    )
    led_missions = relationship("Mission", back_populates="lead")
    assigned_roles = relationship("MissionRole", back_populates="assignee")
    pitches = relationship(
        "MissionPitch", back_populates="user", cascade="all, delete-orphan"
    )


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users = relationship("UserSkill", back_populates="skill")


class UserSkill(Base):
    __tablename__ = "user_skills"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    proficiency = Column(
        Enum(SkillProficiencyEnum, name="skill_proficiency"), nullable=False
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="skills")
    skill = relationship("Skill", back_populates="users")


class Mission(Base):
    __tablename__ = "missions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    lead_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(
        Enum(MissionStatusEnum, name="mission_status"),
        nullable=False,
        default=MissionStatusEnum.Proposed,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead = relationship("User", back_populates="led_missions")
    roles = relationship(
        "MissionRole", back_populates="mission", cascade="all, delete-orphan"
    )
    pitches = relationship(
        "MissionPitch", back_populates="mission", cascade="all, delete-orphan"
    )


class MissionRole(Base):
    __tablename__ = "mission_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_description = Column(Text, nullable=False)
    skill_id_required = Column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    proficiency_required = Column(
        Enum(SkillProficiencyEnum, name="skill_proficiency"), nullable=False
    )
    assignee_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    mission = relationship("Mission", back_populates="roles")
    required_skill = relationship("Skill")
    assignee = relationship("User", back_populates="assigned_roles")


class MissionPitch(Base):
    __tablename__ = "mission_pitches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pitch_text = Column(Text, nullable=False)
    status = Column(
        Enum(PitchStatusEnum, name="pitch_status"),
        nullable=False,
        default=PitchStatusEnum.Submitted,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    mission = relationship("Mission", back_populates="pitches")
    user = relationship("User", back_populates="pitches")
