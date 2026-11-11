from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas, auth, database

router = APIRouter(prefix="/api", tags=["Activities"])


@router.get("/subjects", response_model=List[schemas.SubjectOut])
async def get_subjects(
    stream: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get list of subjects. Optionally filter by stream (Humanities / Sciences)."""
    query = db.query(models.Subject).filter(models.Subject.is_active == True)
    if stream:
        query = query.filter(models.Subject.stream == stream)
    return query.order_by(models.Subject.name).all()


@router.post("/activities")
async def create_activity(
    payload: schemas.ClassActivityCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Record a class activity (assignment, exercise, notes, etc.)."""
    # Validate class
    class_obj = db.query(models.Class).filter(models.Class.id == payload.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    # Validate subject
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    activity = models.ClassActivity(
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        date=payload.date,
        description=payload.description,
        participation_notes=payload.participation_notes,
        recorded_by=current_user.id
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return {
        "message": "Activity recorded successfully",
        "id": activity.id
    }


@router.get("/activities/{class_id}")
async def get_activities_for_class(
    class_id: int,
    activity_date: date = Query(..., alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all activities recorded for a class on a specific date."""
    activities = (
        db.query(models.ClassActivity)
        .filter(
            models.ClassActivity.class_id == class_id,
            models.ClassActivity.date == activity_date
        )
        .order_by(models.ClassActivity.created_at)
        .all()
    )

    result = []
    for a in activities:
        result.append({
            "id": a.id,
            "class_id": a.class_id,
            "subject_id": a.subject_id,
            "subject_name": a.subject.name if a.subject else "Unknown",
            "date": a.date,
            "description": a.description,
            "participation_notes": a.participation_notes,
            "recorded_by_name": a.recorded_by_user.full_name if a.recorded_by_user else "Unknown",
            "created_at": a.created_at
        })
    return result