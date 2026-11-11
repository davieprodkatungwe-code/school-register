from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, auth, database

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    status: Optional[str] = Query(None),  # pending / contacted
    notif_date: Optional[date] = Query(None, alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """List parent notifications."""
    query = db.query(models.Notification)

    if status:
        query = query.filter(models.Notification.status == status)
    if notif_date:
        query = query.filter(models.Notification.date == notif_date)

    notifications = query.order_by(models.Notification.date.desc(), models.Notification.created_at.desc()).all()

    result = []
    for n in notifications:
        result.append({
            "id": n.id,
            "student_name": n.student.full_name if n.student else "Unknown",
            "admission_number": n.student.admission_number if n.student else "",
            "class_name": n.student.class_.name if n.student and n.student.class_ else "",
            "date": n.date,
            "parent_phone": n.parent_phone,
            "parent_name": n.parent_name,
            "message": n.message,
            "status": n.status,
            "contacted_by": n.contacted_by_user.full_name if n.contacted_by_user else None,
            "contacted_at": n.contacted_at,
            "notes": n.notes
        })
    return result


@router.put("/{notification_id}/contacted")
async def mark_as_contacted(
    notification_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Mark a notification as contacted."""
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.status = "contacted"
    notif.contacted_by = current_user.id
    notif.contacted_at = datetime.utcnow()
    if notes:
        notif.notes = notes

    db.commit()
    return {"message": "Marked as contacted"}