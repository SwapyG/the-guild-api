# app/main.py (Definitive Final Version with Two-Tiered Auth)

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List
import uuid

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from . import models, schemas, auth
from .database import get_db, engine

models.Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="The Guild API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://localhost:3000",
    "https://the-guild-frontend.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https:\/\/the-guild-frontend-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="The Guild API",
        version="0.1.0",
        description="Operating System for a Post-Job Economy",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    security_requirement = {"BearerAuth": []}
    paths = openapi_schema["paths"]
    for path in paths:
        for method in paths[path]:
            if "security" in paths[path][method].get("tags", []):
                paths[path][method]["security"] = [security_requirement]
    return openapi_schema


app.openapi = custom_openapi


# --- Auth Endpoints ---
@app.post(
    "/auth/register",
    response_model=schemas.User,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
@limiter.limit("10/minute")
def register_user(
    user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        **user.model_dump(exclude={"password"}), hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/auth/login", response_model=schemas.Token, tags=["Authentication"])
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = auth.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_data = {"sub": user.email, "role": user.role.value}
    access_token = auth.create_access_token(data=access_token_data)
    return {"access_token": access_token, "token_type": "bearer"}


# --- Root Endpoint ---
@app.get("/", tags=["Public"])
def read_root():
    return {"message": "Welcome to The Guild API"}


# --- Notification Endpoints ---
@app.get(
    "/users/me/notifications",
    response_model=List[schemas.Notification],
    tags=["Notifications", "security"],
)
def get_my_notifications(current_user: models.User = Depends(auth.get_current_user)):
    return current_user.notifications


@app.patch(
    "/notifications/{notification_id}/read",
    response_model=schemas.Notification,
    tags=["Notifications", "security"],
)
def mark_notification_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_notification = (
        db.query(models.Notification)
        .filter(
            models.Notification.id == notification_id,
            models.Notification.user_id == current_user.id,
        )
        .first()
    )
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db_notification.is_read = True
    db.commit()
    db.refresh(db_notification)
    return db_notification


# --- User & Talent Endpoints ---
@app.get("/users/", response_model=List[schemas.User], tags=["Public"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.User).offset(skip).limit(limit).all()


@app.get(
    "/users/search",
    response_model=List[schemas.UserProfile],
    tags=["Users", "security"],
)
def search_users_by_skill(
    skill_name: str,
    proficiency: models.SkillProficiencyEnum,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    proficiency_hierarchy = ["Beginner", "Intermediate", "Advanced", "Expert"]
    try:
        required_index = proficiency_hierarchy.index(proficiency.value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid proficiency level")
    valid_proficiencies = proficiency_hierarchy[required_index:]
    return (
        db.query(models.User)
        .join(models.User.skills)
        .join(models.UserSkill.skill)
        .filter(
            models.Skill.name.ilike(f"%{skill_name}%"),
            models.UserSkill.proficiency.in_(valid_proficiencies),
        )
        .options(joinedload(models.User.skills).joinedload(models.UserSkill.skill))
        .all()
    )


@app.get("/users/me", response_model=schemas.UserProfile, tags=["Users", "security"])
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.post(
    "/users/me/skills", response_model=schemas.UserProfile, tags=["Users", "security"]
)
def add_skill_to_current_user(
    user_skill: schemas.UserSkillCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_user_skill = (
        db.query(models.UserSkill)
        .filter(
            models.UserSkill.user_id == current_user.id,
            models.UserSkill.skill_id == user_skill.skill_id,
        )
        .first()
    )
    if db_user_skill:
        db_user_skill.proficiency = user_skill.proficiency
    else:
        db_user_skill = models.UserSkill(
            **user_skill.model_dump(), user_id=current_user.id
        )
        db.add(db_user_skill)
    db.commit()
    db.refresh(current_user)
    return current_user


@app.delete(
    "/users/me/skills/{skill_id}",
    response_model=schemas.UserProfile,
    tags=["Users", "security"],
)
def remove_skill_from_current_user(
    skill_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_user_skill = (
        db.query(models.UserSkill)
        .filter(
            models.UserSkill.user_id == current_user.id,
            models.UserSkill.skill_id == skill_id,
        )
        .first()
    )
    if db_user_skill:
        db.delete(db_user_skill)
        db.commit()
    db.refresh(current_user)
    return current_user


# --- Skill Endpoints ---
@app.get("/skills/", response_model=List[schemas.Skill], tags=["Public"])
def read_skills(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Skill).offset(skip).limit(limit).all()


@app.post(
    "/skills/",
    response_model=schemas.Skill,
    status_code=status.HTTP_201_CREATED,
    tags=["Skills", "security"],
)
def create_skill(
    skill: schemas.SkillCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_manager_user),
):
    db_skill = models.Skill(**skill.model_dump())
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


# --- Mission Endpoints ---
@app.get("/missions/", response_model=List[schemas.Mission], tags=["Public"])
def read_missions(db: Session = Depends(get_db)):
    return (
        db.query(models.Mission)
        .options(
            joinedload(models.Mission.lead),
            joinedload(models.Mission.roles).joinedload(models.MissionRole.assignee),
            joinedload(models.Mission.roles).joinedload(
                models.MissionRole.required_skill
            ),
            joinedload(models.Mission.pitches).joinedload(models.MissionPitch.user),
        )
        .order_by(models.Mission.created_at.desc())
        .all()
    )


@app.get(
    "/missions/action-items",
    response_model=List[schemas.MissionActionItem],
    tags=["Missions", "security"],
)
def get_missions_with_pending_pitches(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_manager_user),
):
    missions = (
        db.query(models.Mission)
        .join(models.Mission.pitches)
        .filter(
            models.Mission.lead_user_id == current_user.id,
            models.MissionPitch.status == models.PitchStatusEnum.Submitted,
        )
        .options(joinedload(models.Mission.lead), joinedload(models.Mission.pitches))
        .distinct()
        .all()
    )
    result = []
    for mission in missions:
        pending_count = sum(
            1
            for pitch in mission.pitches
            if pitch.status == models.PitchStatusEnum.Submitted
        )
        mission_action_item = schemas.MissionActionItem.model_validate(
            mission, from_attributes=True
        )
        mission_action_item.pending_pitches = pending_count
        result.append(mission_action_item)
    return result


@app.get("/missions/{mission_id}", response_model=schemas.Mission, tags=["Public"])
def read_mission(mission_id: uuid.UUID, db: Session = Depends(get_db)):
    mission = (
        db.query(models.Mission)
        .options(
            joinedload(models.Mission.lead),
            joinedload(models.Mission.roles).joinedload(models.MissionRole.assignee),
            joinedload(models.Mission.roles).joinedload(
                models.MissionRole.required_skill
            ),
            joinedload(models.Mission.pitches).joinedload(models.MissionPitch.user),
        )
        .filter(models.Mission.id == mission_id)
        .first()
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@app.post(
    "/missions/",
    response_model=schemas.Mission,
    status_code=status.HTTP_201_CREATED,
    tags=["Missions", "security"],
)
def create_mission(
    mission: schemas.MissionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_manager_user),
):
    mission_data = mission.model_dump(exclude={"roles"})
    db_mission = models.Mission(**mission_data, lead_user_id=current_user.id)
    db.add(db_mission)
    db.commit()
    db.refresh(db_mission)
    for role_data in mission.roles:
        db_role = models.MissionRole(**role_data.model_dump(), mission_id=db_mission.id)
        db.add(db_role)
    db.commit()
    db.refresh(db_mission)
    return db_mission


@app.patch(
    "/missions/{mission_id}/status",
    response_model=schemas.Mission,
    tags=["Missions", "security"],
)
def update_mission_status(
    mission_id: uuid.UUID,
    status_update: schemas.MissionUpdateStatus,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_mission = (
        db.query(models.Mission)
        .options(
            joinedload(models.Mission.lead),
            joinedload(models.Mission.roles).joinedload(models.MissionRole.assignee),
            joinedload(models.Mission.roles).joinedload(
                models.MissionRole.required_skill
            ),
            joinedload(models.Mission.pitches).joinedload(models.MissionPitch.user),
        )
        .filter(models.Mission.id == mission_id)
        .first()
    )
    if not db_mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    if db_mission.lead_user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the mission lead can change the status"
        )
    db_mission.status = status_update.status
    db.commit()
    db.refresh(db_mission)
    return db_mission


# --- Workflow Endpoints ---
@app.get(
    "/missions/{mission_id}/pitches",
    response_model=List[schemas.MissionPitch],
    tags=["Workflow", "security"],
)
def read_pitches_for_mission(mission_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(models.MissionPitch)
        .options(joinedload(models.MissionPitch.user))
        .filter(models.MissionPitch.mission_id == mission_id)
        .all()
    )


@app.post(
    "/missions/{mission_id}/pitch",
    response_model=schemas.MissionPitch,
    status_code=status.HTTP_201_CREATED,
    tags=["Workflow", "security"],
)
def pitch_for_mission(
    mission_id: uuid.UUID,
    pitch: schemas.MissionPitchBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_mission = (
        db.query(models.Mission)
        .options(joinedload(models.Mission.lead))
        .filter(models.Mission.id == mission_id)
        .first()
    )
    if not db_mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    db_pitch = models.MissionPitch(
        **pitch.model_dump(), mission_id=mission_id, user_id=current_user.id
    )
    notification = models.Notification(
        user_id=db_mission.lead_user_id,
        message=f"'{current_user.name}' has pitched for your mission: '{db_mission.title}'.",
        link=f"/missions/{mission_id}",
    )
    db.add(db_pitch)
    db.add(notification)
    try:
        db.commit()
        db.refresh(db_pitch)
        return db_pitch
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="You have already pitched for this mission."
        )


@app.patch(
    "/pitches/{pitch_id}/status",
    response_model=schemas.MissionPitch,
    tags=["Workflow", "security"],
)
def update_pitch_status(
    pitch_id: uuid.UUID,
    status_update: schemas.MissionPitchUpdateStatus,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_pitch = (
        db.query(models.MissionPitch)
        .options(
            joinedload(models.MissionPitch.mission),
            joinedload(models.MissionPitch.user),
        )
        .filter(models.MissionPitch.id == pitch_id)
        .first()
    )
    if not db_pitch or db_pitch.mission.lead_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Pitch not found or not authorized")
    db_pitch.status = status_update.status
    status_text = (
        "accepted"
        if status_update.status == models.PitchStatusEnum.Accepted
        else "rejected"
    )
    notification = models.Notification(
        user_id=db_pitch.user_id,
        message=f"Your pitch for the mission '{db_pitch.mission.title}' has been {status_text}.",
        link=f"/missions/{db_pitch.mission_id}",
    )
    db.add(notification)
    db.commit()
    db.refresh(db_pitch)
    return db_pitch


@app.post(
    "/mission-roles/{role_id}/draft",
    response_model=schemas.MissionRole,
    tags=["Workflow", "security"],
)
def draft_user_for_role(
    role_id: uuid.UUID,
    draft_info: schemas.MissionRoleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_role = (
        db.query(models.MissionRole).filter(models.MissionRole.id == role_id).first()
    )
    if not db_role:
        raise HTTPException(status_code=404, detail="Mission role not found")
    mission = (
        db.query(models.Mission).filter(models.Mission.id == db_role.mission_id).first()
    )
    if not mission or mission.lead_user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Only the mission lead can draft members."
        )
    db_user = (
        db.query(models.User)
        .filter(models.User.id == draft_info.assignee_user_id)
        .first()
    )
    if not db_user:
        raise HTTPException(status_code=404, detail="User to be drafted not found")
    db_role.assignee_user_id = draft_info.assignee_user_id
    notification = models.Notification(
        user_id=draft_info.assignee_user_id,
        message=f"You have been drafted for the role '{db_role.role_description}' in the mission: '{mission.title}'.",
        link=f"/missions/{mission.id}",
    )
    db.add(notification)
    db.commit()
    db.refresh(db_role)
    return db_role


@app.get(
    "/invites/me",
    response_model=List[schemas.MissionInvite],
    tags=["Invitations", "security"],
)
def get_my_invitations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_invites = (
        db.query(models.MissionInvite)
        .options(
            joinedload(models.MissionInvite.mission_role).joinedload(
                models.MissionRole.mission
            ),
            joinedload(models.MissionInvite.inviting_user),
            joinedload(models.MissionInvite.mission_role).joinedload(
                models.MissionRole.required_skill
            ),
        )
        .filter(
            models.MissionInvite.invited_user_id == current_user.id,
            models.MissionInvite.status == models.InviteStatusEnum.Pending,
        )
        .order_by(models.MissionInvite.created_at.desc())
        .all()
    )
    return [
        schemas.MissionInvite.model_validate(invite, from_attributes=True)
        for invite in db_invites
    ]


@app.post(
    "/invites",
    response_model=schemas.MissionInvite,
    status_code=status.HTTP_201_CREATED,
    tags=["Invitations", "security"],
)
def create_invite(
    invite_data: schemas.MissionInviteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_manager_user),
):
    db_role = (
        db.query(models.MissionRole)
        .options(joinedload(models.MissionRole.mission))
        .filter(models.MissionRole.id == invite_data.mission_role_id)
        .first()
    )
    if not db_role:
        raise HTTPException(status_code=404, detail="Mission role not found")
    if db_role.mission.lead_user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You are not the lead of this mission"
        )
    if db_role.assignee_user_id:
        raise HTTPException(status_code=400, detail="This role is already filled")
    db_invited_user = (
        db.query(models.User)
        .filter(models.User.id == invite_data.invited_user_id)
        .first()
    )
    if not db_invited_user:
        raise HTTPException(status_code=404, detail="User to be invited not found")
    existing_invite = (
        db.query(models.MissionInvite)
        .filter(
            models.MissionInvite.mission_role_id == invite_data.mission_role_id,
            models.MissionInvite.invited_user_id == invite_data.invited_user_id,
            models.MissionInvite.status == models.InviteStatusEnum.Pending,
        )
        .first()
    )
    if existing_invite:
        raise HTTPException(
            status_code=409,
            detail="A pending invite for this user to this role already exists",
        )
    db_invite = models.MissionInvite(
        mission_role_id=invite_data.mission_role_id,
        invited_user_id=invite_data.invited_user_id,
        inviting_user_id=current_user.id,
    )
    notification = models.Notification(
        user_id=invite_data.invited_user_id,
        message=f"'{current_user.name}' has invited you to join the mission '{db_role.mission.title}' as '{db_role.role_description}'.",
        link=f"/invites",
    )
    db.add(db_invite)
    db.add(notification)
    db.commit()
    db.refresh(db_invite)
    return db_invite


@app.patch(
    "/invites/{invite_id}",
    response_model=schemas.MissionInvite,
    tags=["Invitations", "security"],
)
def respond_to_invite(
    invite_id: uuid.UUID,
    response_data: schemas.MissionInviteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_invite = (
        db.query(models.MissionInvite)
        .options(
            joinedload(models.MissionInvite.mission_role).joinedload(
                models.MissionRole.mission
            ),
            joinedload(models.MissionInvite.inviting_user),
        )
        .filter(models.MissionInvite.id == invite_id)
        .first()
    )
    if not db_invite or db_invite.invited_user_id != current_user.id:
        raise HTTPException(
            status_code=404, detail="Invite not found or you are not authorized"
        )
    if db_invite.status != models.InviteStatusEnum.Pending:
        raise HTTPException(
            status_code=400, detail="This invitation has already been responded to"
        )
    if response_data.status == models.InviteStatusEnum.Accepted:
        if db_invite.mission_role.assignee_user_id:
            db_invite.status = models.InviteStatusEnum.Declined
            notification_msg = f"Your acceptance for '{db_invite.mission_role.mission.title}' could not be processed as the role was filled."
            db.add(
                models.Notification(user_id=current_user.id, message=notification_msg)
            )
            db.commit()
            raise HTTPException(
                status_code=409, detail="This role has already been filled."
            )
        db_invite.mission_role.assignee_user_id = current_user.id
        db_invite.status = models.InviteStatusEnum.Accepted
        notification_msg = f"'{current_user.name}' has accepted your invitation to join '{db_invite.mission_role.mission.title}'."
        db.add(
            models.Notification(
                user_id=db_invite.inviting_user_id,
                message=notification_msg,
                link=f"/missions/{db_invite.mission_role.mission_id}",
            )
        )
    elif response_data.status == models.InviteStatusEnum.Declined:
        db_invite.status = models.InviteStatusEnum.Declined
        notification_msg = f"'{current_user.name}' has declined your invitation to join '{db_invite.mission_role.mission.title}'."
        db.add(
            models.Notification(
                user_id=db_invite.inviting_user_id, message=notification_msg
            )
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid status update")
    db.commit()
    db.refresh(db_invite)
    return db_invite
