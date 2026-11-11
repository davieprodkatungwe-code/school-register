from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import models, schemas, auth, database

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.get("/users", response_model=List[schemas.UserOut])
async def list_users(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can view users")
    return db.query(models.User).order_by(models.User.full_name).all()


@router.post("/users")
async def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create users")

    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    allowed_roles = ["teacher", "form_teacher", "head_teacher", "bursar", "admin"]
    if payload.role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(allowed_roles)}")

    user = models.User(
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=auth.get_password_hash(payload.password),
        role=payload.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": f"User {user.full_name} created successfully",
        "id": user.id,
        "username": user.username,
        "role": user.role
    }


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can deactivate users")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot deactivate the main admin account")

    user.is_active = False
    db.commit()

    return {"message": f"User {user.full_name} has been deactivated"}
from pydantic import BaseModel

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Allow any logged-in user to change their own password."""
    if not auth.verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    current_user.hashed_password = auth.get_password_hash(payload.new_password)
    db.commit()

    return {"message": "Password changed successfully. Please login again with your new password."}