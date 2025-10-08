# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL environment variable not set")

# The create_engine function from SQLAlchemy is used to establish a connection to the database.
# It takes the database URL as an argument.
engine = create_engine(DATABASE_URL)

# SessionLocal is a factory for creating new Session objects. A session is the primary interface
# for all database operations in SQLAlchemy. It's essentially a temporary workspace for your objects
# that are linked to the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is a factory for creating declarative base classes. All of our ORM models will inherit from this class.
# It connects the class definitions to the database tables.
Base = declarative_base()


# Dependency for FastAPI
# This function will be used in our API endpoints to get a database session.
# It ensures that the database session is always closed after the request is finished.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
