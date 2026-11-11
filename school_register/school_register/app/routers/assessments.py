from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas, auth, database

router = APIRouter(prefix="/api/assessments", tags=["Assessments"])


@router.post("")
async def create_assessment(
    payload: schemas.AssessmentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Create a new assessment / continuous test."""
    class_obj = db.query(models.Class).filter(models.Class.id == payload.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    assessment = models.Assessment(
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        title=payload.title,
        total_marks=payload.total_marks,
        date=payload.date,
        description=payload.description,
        recorded_by=current_user.id
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return {
        "message": "Assessment created successfully",
        "id": assessment.id,
        "title": assessment.title
    }


@router.get("")
async def list_assessments(
    class_id: Optional[int] = None,
    assessment_date: Optional[date] = Query(None, alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """List assessments, optionally filtered by class or date."""
    query = db.query(models.Assessment)
    if class_id:
        query = query.filter(models.Assessment.class_id == class_id)
    if assessment_date:
        query = query.filter(models.Assessment.date == assessment_date)

    assessments = query.order_by(models.Assessment.date.desc()).all()

    result = []
    for a in assessments:
        result.append({
            "id": a.id,
            "title": a.title,
            "class_id": a.class_id,
            "class_name": a.class_.name if a.class_ else "",
            "subject_id": a.subject_id,
            "subject_name": a.subject.name if a.subject else "",
            "total_marks": a.total_marks,
            "date": a.date,
            "description": a.description,
            "recorded_by": a.recorded_by_user.full_name if a.recorded_by_user else ""
        })
    return result


@router.get("/{assessment_id}/scores")
async def get_assessment_scores(
    assessment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all students and their scores for an assessment."""
    assessment = db.query(models.Assessment).filter(models.Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    students = (
        db.query(models.Student)
        .filter(models.Student.class_id == assessment.class_id, models.Student.is_active == True)
        .order_by(models.Student.last_name, models.Student.first_name)
        .all()
    )

    existing_scores = {
        s.student_id: s for s in db.query(models.AssessmentScore).filter(
            models.AssessmentScore.assessment_id == assessment_id
        ).all()
    }

    result = []
    for student in students:
        score = existing_scores.get(student.id)
        result.append({
            "student_id": student.id,
            "admission_number": student.admission_number,
            "full_name": student.full_name,
            "marks_obtained": score.marks_obtained if score else None,
            "comment": score.comment if score else None
        })

    return {
        "assessment": {
            "id": assessment.id,
            "title": assessment.title,
            "total_marks": assessment.total_marks,
            "subject_name": assessment.subject.name if assessment.subject else "",
            "class_name": assessment.class_.name if assessment.class_ else "",
            "date": assessment.date
        },
        "scores": result
    }


@router.post("/scores")
async def save_scores(
    payload: schemas.AssessmentScoresBulk,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Save or update scores for an assessment."""
    assessment = db.query(models.Assessment).filter(models.Assessment.id == payload.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    for entry in payload.scores:
        existing = db.query(models.AssessmentScore).filter(
            models.AssessmentScore.assessment_id == payload.assessment_id,
            models.AssessmentScore.student_id == entry.student_id
        ).first()

        if existing:
            existing.marks_obtained = entry.marks_obtained
            existing.comment = entry.comment
        else:
            new_score = models.AssessmentScore(
                assessment_id=payload.assessment_id,
                student_id=entry.student_id,
                marks_obtained=entry.marks_obtained,
                comment=entry.comment
            )
            db.add(new_score)

    db.commit()
    return {"message": "Scores saved successfully"}