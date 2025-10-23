# app/models.py (DEFINITIVE - Corrected with server_default for UUIDs)

import enum
import uuid
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    ForeignKey,
    Enum,
    TIMESTAMP,
    Date,
    Numeric,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from .database import Base


class UserRoleEnum(str, enum.Enum):
    Member = "Member"
    Manager = "Manager"
    Admin = "Admin"


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


# --- NANO: CORRECTIVE ACTION - Using server_default for all UUID primary keys ---
# This ensures PostgreSQL generates the UUID, making direct SQL INSERTs work.


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message = Column(Text, nullable=False)
    link = Column(String(2048), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    recipient: Mapped["User"] = relationship("User", back_populates="notifications")


class User(Base):
    __tablename__ = "users"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    photo_url = Column(String(2048))
    title = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    role = Column(
        Enum(UserRoleEnum, name="user_role"),
        nullable=False,
        server_default=UserRoleEnum.Member.value,
    )
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    skills: Mapped[List["UserSkill"]] = relationship(
        "UserSkill", back_populates="user", cascade="all, delete-orphan"
    )
    led_missions: Mapped[List["Mission"]] = relationship(
        "Mission", back_populates="lead"
    )
    assigned_roles: Mapped[List["MissionRole"]] = relationship(
        "MissionRole", back_populates="assignee"
    )
    pitches: Mapped[List["MissionPitch"]] = relationship(
        "MissionPitch", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="recipient",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )

    @property
    def mission_history(self):
        history = []
        for mission in self.led_missions:
            history.append(
                {
                    "mission_id": mission.id,
                    "mission_title": mission.title,
                    "role": "Mission Lead",
                    "status": mission.status,
                }
            )
        for role in self.assigned_roles:
            history.append(
                {
                    "mission_id": role.mission.id,
                    "mission_title": role.mission.title,
                    "role": role.role_description,
                    "status": role.mission.status,
                }
            )
        return sorted(history, key=lambda x: x["mission_title"])


class Skill(Base):
    __tablename__ = "skills"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    users: Mapped[List["UserSkill"]] = relationship("UserSkill", back_populates="skill")


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
    user: Mapped["User"] = relationship("User", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="users")


class Mission(Base):
    __tablename__ = "missions"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
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
    budget = Column(Numeric(10, 2), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    lead: Mapped["User"] = relationship("User", back_populates="led_missions")
    roles: Mapped[List["MissionRole"]] = relationship(
        "MissionRole", back_populates="mission", cascade="all, delete-orphan"
    )
    pitches: Mapped[List["MissionPitch"]] = relationship(
        "MissionPitch", back_populates="mission", cascade="all, delete-orphan"
    )


class MissionRole(Base):
    __tablename__ = "mission_roles"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
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
    mission: Mapped["Mission"] = relationship("Mission", back_populates="roles")
    required_skill: Mapped["Skill"] = relationship("Skill")
    assignee: Mapped[Optional["User"]] = relationship(
        "User", back_populates="assigned_roles"
    )


class MissionPitch(Base):
    __tablename__ = "mission_pitches"
    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
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
    mission: Mapped["Mission"] = relationship("Mission", back_populates="pitches")
    user: Mapped["User"] = relationship("User", back_populates="pitches")
