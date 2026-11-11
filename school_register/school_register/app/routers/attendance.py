from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from .. import models, schemas, auth, database

router = APIRouter(prefix="/api", tags=["Attendance"])


@router.get("/classes", response_model=List[schemas.ClassOut])
async def get_classes(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Class).order_by(models.Class.form, models.Class.stream).all()


@router.get("/classes/{class_id}/students", response_model=List[schemas.StudentOut])
async def get_class_students(
    class_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    students = (
        db.query(models.Student)
        .filter(models.Student.class_id == class_id, models.Student.is_active == True)
        .order_by(models.Student.last_name, models.Student.first_name)
        .all()
    )
    return students


@router.get("/attendance/{class_id}")
async def get_attendance_for_date(
    class_id: int,
    attendance_date: date = Query(..., alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get existing attendance records for a class on a specific date."""
    records = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.class_id == class_id,
            models.Attendance.date == attendance_date
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
        })
    return result


@router.post("/attendance/mark")
async def mark_attendance(
    payload: schemas.AttendanceBulk,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Mark or update attendance for a whole class on a given date."""
    class_obj = db.query(models.Class).filter(models.Class.id == payload.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    saved = 0
    for record in payload.records:
        student = db.query(models.Student).filter(
            models.Student.id == record.student_id,
            models.Student.class_id == payload.class_id
        ).first()
        if not student:
            continue

        existing = db.query(models.Attendance).filter(
            and_(
                models.Attendance.student_id == record.student_id,
                models.Attendance.date == payload.date
            )
        ).first()

        if existing:
            existing.status = record.status.value
            existing.reason = record.reason if record.status == schemas.AttendanceStatus.absent else None
            existing.communicated = record.communicated.value if record.status == schemas.AttendanceStatus.absent else "unknown"
            existing.notes = record.notes
            existing.recorded_by = current_user.id
            existing.updated_at = datetime.utcnow()
            attendance_record = existing
        else:
            new_record = models.Attendance(
                student_id=record.student_id,
                class_id=payload.class_id,
                date=payload.date,
                status=record.status.value,
                reason=record.reason if record.status == schemas.AttendanceStatus.absent else None,
                communicated=record.communicated.value if record.status == schemas.AttendanceStatus.absent else "unknown",
                notes=record.notes,
                recorded_by=current_user.id
            )
            db.add(new_record)
            db.flush()  # so we get the id
            attendance_record = new_record

        # Create notification if student is absent
        if record.status == schemas.AttendanceStatus.absent:
            # Avoid duplicate notification for same student + date
            existing_notif = db.query(models.Notification).filter(
                models.Notification.student_id == student.id,
                models.Notification.date == payload.date
            ).first()

            if not existing_notif:
                message = f"Dear Parent, your child {student.full_name} was marked absent on {payload.date}."
                if record.reason:
                    message += f" Reason: {record.reason}."

                notif = models.Notification(
                    student_id=student.id,
                    attendance_id=attendance_record.id,
                    date=payload.date,
                    parent_phone=student.parent_phone,
                    parent_name=student.parent_name,
                    message=message,
                    status="pending"
                )
                db.add(notif)

        saved += 1

    db.commit()
    return {"message": f"Attendance saved successfully for {saved} students", "saved": saved}
@router.get("/report/{class_id}")
async def get_daily_report(
    class_id: int,
    report_date: date = Query(..., alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Generate daily attendance report for a class."""
    class_obj = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    # All active students in class
    students = (
        db.query(models.Student)
        .filter(models.Student.class_id == class_id, models.Student.is_active == True)
        .all()
    )
    total_students = len(students)

    # Attendance records for the day
    records = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.class_id == class_id,
            models.Attendance.date == report_date
        )
        .all()
    )

    # Map student_id -> record
    record_map = {r.student_id: r for r in records}

    present_count = 0
    absent_count = 0
    absentees = []

    for student in students:
        rec = record_map.get(student.id)
        if rec:
            if rec.status == "present":
                present_count += 1
            else:
                absent_count += 1
                absentees.append({
                    "id": rec.id,
                    "student_id": student.id,
                    "student_name": student.full_name,
                    "admission_number": student.admission_number,
                    "status": rec.status,
                    "reason": rec.reason or "Not specified",
                    "communicated": rec.communicated,
                    "notes": rec.notes,
                    "recorded_by_name": rec.recorded_by_user.full_name if rec.recorded_by_user else "Unknown"
                })
        else:
            # Not marked yet – treat as unknown for report, but don't count as absent
            pass

    # Only count marked students for percentage if some are unmarked
    marked = present_count + absent_count
    percentage = round((present_count / total_students * 100), 1) if total_students > 0 else 0

    return {
        "class_name": class_obj.name,
        "date": report_date,
        "total_students": total_students,
        "total_present": present_count,
        "total_absent": absent_count,
        "unmarked": total_students - marked,
        "present_percentage": percentage,
        "absentees": absentees
    }

from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from io import BytesIO


from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from io import BytesIO


@router.get("/report/{class_id}/excel")
async def download_excel_report(
    class_id: int,
    report_date: date = Query(..., alias="date"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Download Daily Report as Excel (Attendance + Activities + Grades out of 100)."""
    class_obj = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    # Students
    students = (
        db.query(models.Student)
        .filter(models.Student.class_id == class_id, models.Student.is_active == True)
        .order_by(models.Student.last_name, models.Student.first_name)
        .all()
    )
    total_students = len(students)

    # Attendance
    records = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.class_id == class_id,
            models.Attendance.date == report_date
        )
        .all()
    )
    record_map = {r.student_id: r for r in records}

    present_count = 0
    absent_count = 0
    student_rows = []
    absentees = []

    for student in students:
        rec = record_map.get(student.id)
        if rec:
            status = rec.status.capitalize()
            reason = rec.reason or ""
            communicated = rec.communicated
            if rec.status == "present":
                present_count += 1
            else:
                absent_count += 1
                absentees.append({
                    "name": student.full_name,
                    "admission": student.admission_number,
                    "reason": reason or "Not specified",
                    "communicated": communicated
                })
        else:
            status = "Not marked"
            reason = ""
            communicated = ""

        student_rows.append({
            "admission": student.admission_number,
            "name": student.full_name,
            "status": status,
            "reason": reason,
            "communicated": communicated
        })

    # Activities for the day
    activities = (
        db.query(models.ClassActivity)
        .filter(
            models.ClassActivity.class_id == class_id,
            models.ClassActivity.date == report_date
        )
        .order_by(models.ClassActivity.created_at)
        .all()
    )

    # Assessments for this class in the same year (current term performance)
    year = report_date.year
    assessments = (
        db.query(models.Assessment)
        .filter(
            models.Assessment.class_id == class_id,
            models.Assessment.date >= date(year, 1, 1),
            models.Assessment.date <= date(year, 12, 31)
        )
        .order_by(models.Assessment.date)
        .all()
    )

    # Build performance data per student (out of 100)
    performance = []
    for student in students:
        total_possible = 0
        total_obtained = 0
        details = []

        for a in assessments:
            score = db.query(models.AssessmentScore).filter(
                models.AssessmentScore.assessment_id == a.id,
                models.AssessmentScore.student_id == student.id
            ).first()

            if score and score.marks_obtained is not None:
                total_possible += a.total_marks
                total_obtained += score.marks_obtained
                details.append(f"{a.title}: {score.marks_obtained}/{a.total_marks}")

        percentage = round((total_obtained / total_possible * 100), 1) if total_possible > 0 else None

        performance.append({
            "admission": student.admission_number,
            "name": student.full_name,
            "total_obtained": total_obtained,
            "total_possible": total_possible,
            "percentage": percentage,
            "details": "; ".join(details) if details else "No scores yet"
        })

    form_teacher_name = class_obj.form_teacher.full_name if class_obj.form_teacher else "Not assigned"

    # ========== CREATE EXCEL ==========
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Report"

    title_font = Font(name='Calibri', size=16, bold=True, color='0A2540')
    subtitle_font = Font(name='Calibri', size=12, bold=True)
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    section_font = Font(name='Calibri', size=12, bold=True, color='0A2540')
    normal_font = Font(name='Calibri', size=11)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    header_fill = PatternFill(start_color='0A2540', end_color='0A2540', fill_type='solid')
    present_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    absent_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')

    # Title
    ws.merge_cells('A1:F1')
    ws['A1'] = "HIGH PROFILE PRIVATE SECONDARY SCHOOL"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:F2')
    ws['A2'] = "DAILY ATTENDANCE, ACTIVITIES & PERFORMANCE REPORT"
    ws['A2'].font = subtitle_font
    ws['A2'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A3:F3')
    ws['A3'] = f"Class: {class_obj.name}  |  Date: {report_date.strftime('%d %B %Y')}  |  Form Teacher: {form_teacher_name}"
    ws['A3'].font = Font(name='Calibri', size=11)
    ws['A3'].alignment = Alignment(horizontal='center')

    # Summary
    ws['A5'] = "ATTENDANCE SUMMARY"
    ws['A5'].font = section_font
    ws['A6'] = "Total Students"
    ws['B6'] = total_students
    ws['A7'] = "Present"
    ws['B7'] = present_count
    ws['A8'] = "Absent"
    ws['B8'] = absent_count
    ws['A9'] = "Present %"
    ws['B9'] = f"{round((present_count / total_students * 100), 1) if total_students else 0}%"

    # Full attendance list
    row = 11
    ws[f'A{row}'] = "FULL STUDENT ATTENDANCE LIST"
    ws[f'A{row}'].font = section_font
    row += 1

    headers = ["No.", "Admission No.", "Student Name", "Status", "Reason", "Parent Informed"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    row += 1

    for i, s in enumerate(student_rows, 1):
        ws.cell(row=row, column=1, value=i).border = thin_border
        ws.cell(row=row, column=2, value=s["admission"]).border = thin_border
        ws.cell(row=row, column=3, value=s["name"]).border = thin_border
        status_cell = ws.cell(row=row, column=4, value=s["status"])
        status_cell.border = thin_border
        if s["status"] == "Present":
            status_cell.fill = present_fill
        elif s["status"] == "Absent":
            status_cell.fill = absent_fill
        ws.cell(row=row, column=5, value=s["reason"]).border = thin_border
        informed = "Yes" if s["communicated"] == "yes" else ("No" if s["communicated"] == "no" else ("Unknown" if s["communicated"] else ""))
        ws.cell(row=row, column=6, value=informed).border = thin_border
        row += 1

    # Absentees
    row += 1
    ws[f'A{row}'] = "ABSENTEES SUMMARY"
    ws[f'A{row}'].font = section_font
    row += 1

    if not absentees:
        ws.cell(row=row, column=1, value="No absentees today").font = normal_font
        row += 1
    else:
        for col, header in enumerate(["No.", "Admission No.", "Student Name", "Reason", "Parent Informed"], 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        row += 1
        for i, a in enumerate(absentees, 1):
            ws.cell(row=row, column=1, value=i).border = thin_border
            ws.cell(row=row, column=2, value=a["admission"]).border = thin_border
            ws.cell(row=row, column=3, value=a["name"]).border = thin_border
            ws.cell(row=row, column=4, value=a["reason"]).border = thin_border
            informed = "Yes" if a["communicated"] == "yes" else ("No" if a["communicated"] == "no" else "Unknown")
            ws.cell(row=row, column=5, value=informed).border = thin_border
            row += 1

    # Activities
    row += 1
    ws[f'A{row}'] = "CLASS ACTIVITIES (TODAY)"
    ws[f'A{row}'].font = section_font
    row += 1

    for col, header in enumerate(["No.", "Subject", "Activity Description", "Participation Notes", "Recorded By"], 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    row += 1

    if not activities:
        ws.cell(row=row, column=1, value="No activities recorded for this day").font = normal_font
        row += 1
    else:
        for i, a in enumerate(activities, 1):
            ws.cell(row=row, column=1, value=i).border = thin_border
            ws.cell(row=row, column=2, value=a.subject.name if a.subject else "").border = thin_border
            ws.cell(row=row, column=3, value=a.description).border = thin_border
            ws.cell(row=row, column=4, value=a.participation_notes or "").border = thin_border
            ws.cell(row=row, column=5, value=a.recorded_by_user.full_name if a.recorded_by_user else "").border = thin_border
            row += 1

    # ========== PERFORMANCE / GRADES (OUT OF 100) ==========
    row += 1
    ws[f'A{row}'] = f"STUDENT PERFORMANCE – {year} (OUT OF 100)"
    ws[f'A{row}'].font = section_font
    row += 1

    if not assessments:
        ws.cell(row=row, column=1, value="No assessments recorded for this class yet this year").font = normal_font
    else:
        perf_headers = ["No.", "Admission No.", "Student Name", "Marks Obtained", "Total Possible", "Percentage (%)", "Details"]
        for col, header in enumerate(perf_headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        row += 1

        for i, p in enumerate(performance, 1):
            ws.cell(row=row, column=1, value=i).border = thin_border
            ws.cell(row=row, column=2, value=p["admission"]).border = thin_border
            ws.cell(row=row, column=3, value=p["name"]).border = thin_border
            ws.cell(row=row, column=4, value=p["total_obtained"]).border = thin_border
            ws.cell(row=row, column=5, value=p["total_possible"]).border = thin_border
            perc_cell = ws.cell(row=row, column=6, value=p["percentage"] if p["percentage"] is not None else "N/A")
            perc_cell.border = thin_border
            ws.cell(row=row, column=7, value=p["details"]).border = thin_border
            row += 1
        # ========== SUBJECT ATTENDANCE OVERVIEW ==========
    subject_records = (
        db.query(models.SubjectAttendance)
        .filter(
            models.SubjectAttendance.class_id == class_id,
            models.SubjectAttendance.date == report_date
        )
        .all()
    )

    # Group by student
    subject_map = {}
    for r in subject_records:
        if r.student_id not in subject_map:
            subject_map[r.student_id] = []
        subject_map[r.student_id].append({
            "subject_name": r.subject.name if r.subject else "Unknown",
            "status": r.status,
            "reason": r.reason or "",
            "recorded_by": r.recorded_by_user.full_name if r.recorded_by_user else ""
        })

    row += 1
    ws[f'A{row}'] = "SUBJECT ATTENDANCE OVERVIEW (PER STUDENT)"
    ws[f'A{row}'].font = section_font
    row += 1

    sub_headers = ["No.", "Admission No.", "Student Name", "Subjects Attended", "Subjects Missed (with reason)"]
    for col, header in enumerate(sub_headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    row += 1

    if not subject_records:
        ws.cell(row=row, column=1, value="No subject attendance recorded for this day").font = normal_font
        row += 1
    else:
        for i, student in enumerate(students, 1):
            subjects = subject_map.get(student.id, [])
            attended = [x["subject_name"] for x in subjects if x["status"] == "present"]
            missed = [
                f"{x['subject_name']} ({x['reason'] or 'No reason'})"
                for x in subjects if x["status"] == "absent"
            ]

            ws.cell(row=row, column=1, value=i).border = thin_border
            ws.cell(row=row, column=2, value=student.admission_number).border = thin_border
            ws.cell(row=row, column=3, value=student.full_name).border = thin_border
            ws.cell(row=row, column=4, value=", ".join(attended) if attended else "None").border = thin_border
            ws.cell(row=row, column=5, value=", ".join(missed) if missed else "None").border = thin_border
            row += 1

    # Column widths
    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 26
    ws.column_dimensions['D'].width = 35
    ws.column_dimensions['E'].width = 40
    ws.column_dimensions['F'].width = 16
    ws.column_dimensions['G'].width = 45

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Daily_Report_{class_obj.name.replace(' ', '_')}_{report_date}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
@router.post("/students")
async def create_student(
    payload: schemas.StudentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Add a new student."""
    # Check if admission number already exists
    existing = db.query(models.Student).filter(
        models.Student.admission_number == payload.admission_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admission number already exists")

    # Check class exists
    class_obj = db.query(models.Class).filter(models.Class.id == payload.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    student = models.Student(
        admission_number=payload.admission_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        class_id=payload.class_id,
        gender=payload.gender,
        parent_phone=payload.parent_phone,
        parent_name=payload.parent_name
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    return {
        "message": "Student added successfully",
        "id": student.id,
        "full_name": student.full_name
    }


@router.delete("/students/{student_id}")
async def delete_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Delete a student (or deactivate)."""
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Soft delete (safer)
    student.is_active = False
    db.commit()

    return {"message": f"Student {student.full_name} removed successfully"}

    
@router.put("/classes/{class_id}/form-teacher")
async def assign_form_teacher(
    class_id: int,
    teacher_id: int = Query(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Assign a Form Teacher to a class (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can assign form teachers")

    class_obj = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    teacher = db.query(models.User).filter(models.User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    class_obj.form_teacher_id = teacher_id
    # Also update the teacher's role if it is still plain "teacher"
    if teacher.role == "teacher":
        teacher.role = "form_teacher"

    db.commit()

    return {
        "message": f"{teacher.full_name} is now Form Teacher for {class_obj.name}",
        "class": class_obj.name,
        "form_teacher": teacher.full_name
    }


@router.get("/classes-with-teachers")
async def get_classes_with_teachers(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get all classes with their assigned Form Teacher."""
    classes = db.query(models.Class).order_by(models.Class.form, models.Class.stream).all()
    result = []
    for c in classes:
        result.append({
            "id": c.id,
            "name": c.name,
            "form": c.form,
            "stream": c.stream,
            "form_teacher_id": c.form_teacher_id,
            "form_teacher_name": c.form_teacher.full_name if c.form_teacher else None
        })
    return result