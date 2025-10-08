# main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List
import uuid

# Import all the necessary components from our other files
from . import models, schemas
from .database import SessionLocal, engine, get_db

# This command ensures that all of the tables defined in models.py
# are created in the database when the application starts.
# For a real production app, you might use a migration tool like Alembic.
models.Base.metadata.create_all(bind=engine)

# Initialize the FastAPI app
app = FastAPI(title="The Guild API", version="0.1.0")

# --- CORS (Cross-Origin Resource Sharing) Middleware ---
# This allows our frontend (running on http://localhost:3000)
# to communicate with our backend API.
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# ------------------- API Endpoints -------------------


# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "Welcome to The Guild API"}


# --- User Endpoints ---
@app.post(
    "/users/",
    response_model=schemas.User,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/", response_model=List[schemas.User], tags=["Users"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


# --- Skill Endpoints ---
@app.post(
    "/skills/",
    response_model=schemas.Skill,
    status_code=status.HTTP_201_CREATED,
    tags=["Skills"],
)
def create_skill(skill: schemas.SkillCreate, db: Session = Depends(get_db)):
    db_skill = models.Skill(**skill.model_dump())
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill


@app.get("/skills/", response_model=List[schemas.Skill], tags=["Skills"])
def read_skills(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    skills = db.query(models.Skill).offset(skip).limit(limit).all()
    return skills


# --- Mission Endpoints ---
@app.post(
    "/missions/",
    response_model=schemas.Mission,
    status_code=status.HTTP_201_CREATED,
    tags=["Missions"],
)
def create_mission(mission: schemas.MissionCreate, db: Session = Depends(get_db)):
    # Create the main mission object
    mission_data = mission.model_dump(exclude={"roles"})
    db_mission = models.Mission(**mission_data)

    # Create the associated role objects
    for role_data in mission.roles:
        db_role = models.MissionRole(**role_data.model_dump(), mission=db_mission)
        db.add(db_role)

    db.add(db_mission)
    db.commit()
    db.refresh(db_mission)
    return db_mission


@app.get("/missions/", response_model=List[schemas.Mission], tags=["Missions"])
def read_missions(db: Session = Depends(get_db)):
    # Use joinedload to efficiently fetch related objects (lead, roles, assignee)
    # This prevents the "N+1 query problem" and is much more performant.
    missions = (
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
    return missions


@app.get("/missions/{mission_id}", response_model=schemas.Mission, tags=["Missions"])
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


# --- Core Workflow Endpoints ---


@app.post(
    "/mission-roles/{role_id}/draft",
    response_model=schemas.MissionRole,
    tags=["Workflow"],
)
def draft_user_for_role(
    role_id: uuid.UUID,
    draft_info: schemas.MissionRoleUpdate,
    db: Session = Depends(get_db),
):
    """
    Assigns a user to a specific mission role. This is the "Draft" feature.
    """
    db_role = (
        db.query(models.MissionRole).filter(models.MissionRole.id == role_id).first()
    )
    if not db_role:
        raise HTTPException(status_code=404, detail="Mission role not found")

    # Check if user exists
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
    tags=["Workflow"],
)
def pitch_for_mission(
    mission_id: uuid.UUID,
    pitch: schemas.MissionPitchCreate,
    db: Session = Depends(get_db),
):
    """
    Allows a user to submit a pitch for a mission. This is the "Aspiration Ledger".
    """
    db_mission = (
        db.query(models.Mission).filter(models.Mission.id == mission_id).first()
    )
    if not db_mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    db_user = db.query(models.User).filter(models.User.id == pitch.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User pitching not found")

    db_pitch = models.MissionPitch(**pitch.model_dump(), mission_id=mission_id)
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
