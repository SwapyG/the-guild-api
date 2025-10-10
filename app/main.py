# app/main.py (Complete, with PATCH endpoint)

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List
import uuid
import re

from . import models, schemas, auth
from .database import get_db, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="The Guild API", version="0.1.0")


# --- CORS Configuration ---
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


# --- Custom OpenAPI Schema ---
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
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        name=user.name,
        title=user.title,
        photo_url=user.photo_url,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/auth/login", response_model=schemas.Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = auth.get_user(db, email=form_data.username)
    if (
        not user
        or not user.hashed_password
        or not auth.verify_password(form_data.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_data = {"sub": user.email, "role": user.role.value}
    access_token = auth.create_access_token(data=access_token_data)
    return {"access_token": access_token, "token_type": "bearer"}


# --- Root & Public Endpoints ---
@app.get("/", tags=["Public"])
def read_root():
    return {"message": "Welcome to The Guild API"}


@app.get("/users/me", response_model=schemas.User, tags=["Users", "security"])
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.get("/users/", response_model=List[schemas.User], tags=["Public"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.User).offset(skip).limit(limit).all()


@app.get("/skills/", response_model=List[schemas.Skill], tags=["Public"])
def read_skills(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Skill).offset(skip).limit(limit).all()


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
        )
        .all()
    )


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
        )
        .filter(models.Mission.id == mission_id)
        .first()
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@app.get(
    "/missions/{mission_id}/pitches",
    response_model=List[schemas.MissionPitch],
    tags=["Public"],
)
def read_pitches_for_mission(mission_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(models.MissionPitch)
        .options(joinedload(models.MissionPitch.user))
        .filter(models.MissionPitch.mission_id == mission_id)
        .all()
    )


# --- Secured Endpoints ---
@app.post(
    "/skills/",
    response_model=schemas.Skill,
    status_code=status.HTTP_201_CREATED,
    tags=["Skills", "security"],
)
def create_skill(
    skill: schemas.SkillCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    db_skill = models.Skill(**skill.model_dump())
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


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
    for role_data in mission.roles:
        db_role = models.MissionRole(**role_data.model_dump(), mission=db_mission)
        db.add(db_role)
    db.add(db_mission)
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
        db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    )
    if not db_mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found"
        )
    if db_mission.lead_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the mission lead can change the status",
        )
    db_mission.status = status_update.status
    db.commit()
    db.refresh(db_mission)
    return db_mission


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
    # Add security check: only mission lead can draft
    mission = (
        db.query(models.Mission).filter(models.Mission.id == db_role.mission_id).first()
    )
    if not mission or mission.lead_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the mission lead can draft members.",
        )

    db_user = (
        db.query(models.User)
        .filter(models.User.id == draft_info.assignee_user_id)
        .first()
    )
    if not db_user:
        raise HTTPException(status_code=404, detail="User to be drafted not found")
    db_role.assignee_user_id = draft_info.assignee_user_id
    db.commit()
    db.refresh(db_role)
    return db_role


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
        db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    )
    if not db_mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    db_pitch = models.MissionPitch(
        **pitch.model_dump(), mission_id=mission_id, user_id=current_user.id
    )
    db.add(db_pitch)
    try:
        db.commit()
        db.refresh(db_pitch)
        return db_pitch
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already pitched for this mission.",
        )


from fastapi.routing import APIRoute

# This will run once when the server starts up.
print("\n--- CURRENTLY REGISTERED ROUTES ---")
for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"Path: {route.path}, Name: {route.name}, Methods: {route.methods}")
print("-----------------------------------\n")
