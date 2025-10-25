# app/cli.py (Definitive, Corrected Version)

import typer
from . import auth

# --- NANO: CRITICAL CORRECTION ---
# This import provides the necessary `models` object.
from . import models

# --------------------------------

app = typer.Typer()


@app.command()
def hash_password(
    password: str = typer.Option(
        ...,
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="The plain-text password to hash.",
    )
):
    """
    Generates a secure bcrypt hash for a given password.
    """
    hashed_password = auth.get_password_hash(password)
    print("\n--- SOVEREIGN KEY FORGED ---")
    print("This key is guaranteed to be compatible with your environment.")
    print("Copy the entire hash string below and use it in your SQL seeding script:")
    print(f"\n{hashed_password}\n")
    print("----------------------------")


@app.command()
def create_user_with_role(
    name: str = typer.Option(..., help="Full name of the user."),
    email: str = typer.Option(..., help="User's email address."),
    password: str = typer.Option(..., help="User's password."),
    title: str = typer.Option(..., help="User's professional title."),
    role: models.UserRoleEnum = typer.Option(
        models.UserRoleEnum.Member, help="User's role."
    ),
):
    """
    Creates a new user in the database with a specified role.
    """
    # This function is not used in this protocol but is now syntactically correct.
    from .database import SessionLocal

    db = SessionLocal()
    try:
        db_user = db.query(models.User).filter(models.User.email == email).first()
        if db_user:
            print(f"Error: Email '{email}' already registered.")
            return

        hashed_password = auth.get_password_hash(password)
        new_user = models.User(
            name=name,
            email=email,
            title=title,
            hashed_password=hashed_password,
            role=role,
        )
        db.add(new_user)
        db.commit()
        print(f"Successfully created user '{name}' with role '{role.value}'.")
    finally:
        db.close()


if __name__ == "__main__":
    app()
