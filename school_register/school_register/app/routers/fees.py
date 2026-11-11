from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas, auth, database

router = APIRouter(prefix="/api/fees", tags=["Fees"])


def require_bursar_or_admin(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role not in ["bursar", "admin", "head_teacher"]:
        raise HTTPException(status_code=403, detail="Only Bursar, Admin or Head Teacher can access fees")
    return current_user


@router.post("/terms")
async def create_fee_term(
    payload: schemas.FeeTermCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_bursar_or_admin)
):
    """Create a new fee term (e.g. Term 1 2026)."""
    term = models.FeeTerm(
        name=payload.name,
        year=payload.year,
        term_number=payload.term_number,
        amount_expected=payload.amount_expected
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return {"message": f"Fee term '{term.name}' created", "id": term.id}


@router.get("/terms", response_model=List[schemas.FeeTermOut])
async def list_fee_terms(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.FeeTerm).order_by(models.FeeTerm.year.desc(), models.FeeTerm.term_number).all()


@router.post("/payments")
async def record_payment(
    payload: schemas.FeePaymentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_bursar_or_admin)
):
    """Record a fee payment for a student."""
    student = db.query(models.Student).filter(models.Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    term = db.query(models.FeeTerm).filter(models.FeeTerm.id == payload.term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Fee term not found")

    # Check if a payment record already exists for this student + term
    existing = db.query(models.FeePayment).filter(
        models.FeePayment.student_id == payload.student_id,
        models.FeePayment.term_id == payload.term_id
    ).first()

    if existing:
        existing.amount_paid += payload.amount_paid
        existing.payment_date = payload.payment_date or date.today()
        existing.receipt_number = payload.receipt_number or existing.receipt_number
        existing.notes = payload.notes or existing.notes
        existing.recorded_by = current_user.id
        db.commit()
        return {"message": f"Payment updated. Total paid: {existing.amount_paid}"}
    else:
        payment = models.FeePayment(
            student_id=payload.student_id,
            term_id=payload.term_id,
            amount_paid=payload.amount_paid,
            payment_date=payload.payment_date or date.today(),
            receipt_number=payload.receipt_number,
            notes=payload.notes,
            recorded_by=current_user.id
        )
        db.add(payment)
        db.commit()
        return {"message": "Payment recorded successfully"}


@router.get("/status")
async def get_fee_status(
    term_id: int = Query(...),
    class_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get fee status for all students (or one class) for a given term."""
    term = db.query(models.FeeTerm).filter(models.FeeTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Fee term not found")

    query = db.query(models.Student).filter(models.Student.is_active == True)
    if class_id:
        query = query.filter(models.Student.class_id == class_id)
    students = query.order_by(models.Student.last_name, models.Student.first_name).all()

    # Get all payments for this term
    payments = db.query(models.FeePayment).filter(models.FeePayment.term_id == term_id).all()
    payment_map = {p.student_id: p for p in payments}

    result = []
    for s in students:
        paid = payment_map.get(s.id)
        amount_paid = paid.amount_paid if paid else 0
        balance = term.amount_expected - amount_paid
        if amount_paid <= 0:
            status = "Not Paid"
        elif balance <= 0:
            status = "Paid"
        else:
            status = "Partial"

        result.append({
            "student_id": s.id,
            "admission_number": s.admission_number,
            "full_name": s.full_name,
            "class_name": s.class_.name if s.class_ else "",
            "amount_expected": term.amount_expected,
            "amount_paid": amount_paid,
            "balance": max(balance, 0),
            "status": status
        })

    return {
        "term": term.name,
        "amount_expected": term.amount_expected,
        "students": result
    }