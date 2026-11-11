from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from .. import models, schemas, auth, database

router = APIRouter(prefix="/api/subject-attendance", tags=["Subject Attendance"])


@router.post("/mark")
async def mark_subject_attendance(
    payload: schemas.SubjectAttendanceBulk,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Mark attendance for a specific subject in a class on a given date."""
    class_obj = db.query(models.Class).filter(models.Class.id == payload.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    saved = 0
    for record in payload.records:
        student = db.query(models.Student).filter(
            models.Student.id == record.student_id,
            models.Student.class_id == payload.class_id
        ).first()
        if not student:
            continue

        existing = db.query(models.SubjectAttendance).filter(
            and_(
                models.SubjectAttendance.student_id == record.student_id,
                models.SubjectAttendance.subject_id == payload.subject_id,
                models.SubjectAttendance.date == payload.date
            )
        ).first()

        if existing:
            existing.status = record.status.value
            existing.reason = record.reason if record.status == schemas.AttendanceStatus.absent else None
            existing.communicated = record.communicated.value if record.status == schemas.AttendanceStatus.absent else "unknown"
            existing.notes = record.notes
            existing.recorded_by = current_user.id
            existing.updated_at = datetime.utcnow()
        else:
            new_record = models.SubjectAttendance(
                student_id=record.student_id,
                class_id=payload.class_id,
                subject_id=payload.subject_id,
                date=payload.date,
                status=record.status.value,
                reason=record.reason if record.status == schemas.AttendanceStatus.absent else None,
                communicated=record.communicated.value if record.status == schemas.AttendanceStatus.absent else "unknown",
                notes=record.notes,
                recorded_by=current_user.id
            )
            db.add(new_record)
        saved += 1

    db.commit()
    return {
        "message": f"Subject attendance saved for {saved} students ({subject.name})",
        "saved": saved
    }


@router.get("/{class_id}")
async def get_subject_attendance(
    class_id: int,
    subject_id: int = Query(...),
    attendance_date: date = Query(..., alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get existing subject attendance records for a class + subject + date."""
    records = (
        db.query(models.SubjectAttendance)
        .filter(
            models.SubjectAttendance.class_id == class_id,
            models.SubjectAttendance.subject_id == subject_id,
            models.SubjectAttendance.date == attendance_date
        )
        .all()
    )

    result = []
    for r in records:
        result.append({
            "id": r.id,
            "student_id": r.student_id,
            "status": r.status,
            "reason": r.reason,
            "communicated": r.communicated,
            "notes": r.notes,
            "recorded_by": r.recorded_by_user.full_name if r.recorded_by_user else ""
        })
    return result


@router.get("/report/{class_id}")
async def get_subject_attendance_report(
    class_id: int,
    report_date: date = Query(..., alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Form Teacher report:
    For each student, show which subjects they attended or missed on that day.
    """
    class_obj = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    students = (
        db.query(models.Student)
        .filter(models.Student.class_id == class_id, models.Student.is_active == True)
        .order_by(models.Student.last_name, models.Student.first_name)
        .all()
    )

    # All subject attendance records for this class on this date
    records = (
        db.query(models.SubjectAttendance)
        .filter(
            models.SubjectAttendance.class_id == class_id,
            models.SubjectAttendance.date == report_date
        )
        .all()
    )

    # Group by student
    student_map = {}
    for r in records:
        if r.student_id not in student_map:
            student_map[r.student_id] = []
        student_map[r.student_id].append({
            "subject_id": r.subject_id,
            "subject_name": r.subject.name if r.subject else "Unknown",
            "status": r.status,
            "reason": r.reason,
            "communicated": r.communicated,
            "recorded_by": r.recorded_by_user.full_name if r.recorded_by_user else ""
        })

    result = []
    for s in students:
        subjects = student_map.get(s.id, [])
        present_subjects = [x for x in subjects if x["status"] == "present"]
        absent_subjects = [x for x in subjects if x["status"] == "absent"]

        result.append({
            "student_id": s.id,
            "admission_number": s.admission_number,
            "full_name": s.full_name,
            "subjects_attended": present_subjects,
            "subjects_missed": absent_subjects,
            "total_marked": len(subjects)
        })

    return {
        "class_name": class_obj.name,
        "date": report_date,
        "students": result
    }