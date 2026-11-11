from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="teacher")  # teacher, form_teacher, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    attendance_records = relationship("Attendance", back_populates="recorded_by_user")
    activities = relationship("ClassActivity", back_populates="recorded_by_user")


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    form = Column(Integer, nullable=False)
    stream = Column(String(20), nullable=False)
    form_teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NEW
    created_at = Column(DateTime, default=datetime.utcnow)

    students = relationship("Student", back_populates="class_")
    attendance_records = relationship("Attendance", back_populates="class_")
    activities = relationship("ClassActivity", back_populates="class_")
    form_teacher = relationship("User", foreign_keys=[form_teacher_id])


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    admission_number = Column(String(30), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    gender = Column(String(10), nullable=True)
    parent_phone = Column(String(20), nullable=True)
    parent_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    class_ = relationship("Class", back_populates="students")
    attendance_records = relationship("Attendance", back_populates="student")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(10), nullable=False)  # present / absent
    reason = Column(Text, nullable=True)
    communicated = Column(String(10), default="unknown")
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="attendance_records")
    class_ = relationship("Class", back_populates="attendance_records")
    recorded_by_user = relationship("User", back_populates="attendance_records")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False)
    stream = Column(String(20), nullable=True)  # Humanities, Sciences, or None (common)
    form = Column(Integer, nullable=True)       # Optional: specific form
    is_active = Column(Boolean, default=True)

    activities = relationship("ClassActivity", back_populates="subject")


class ClassActivity(Base):
    __tablename__ = "class_activities"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=False)          # Free text: assignment, exercise, notes etc.
    participation_notes = Column(Text, nullable=True)   # Optional notes about who participated
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    class_ = relationship("Class", back_populates="activities")
    subject = relationship("Subject", back_populates="activities")
    recorded_by_user = relationship("User", back_populates="activities")
class FeeTerm(Base):
    __tablename__ = "fee_terms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)          # e.g. "Term 1 2026"
    year = Column(Integer, nullable=False)
    term_number = Column(Integer, nullable=False)      # 1, 2 or 3
    amount_expected = Column(Integer, nullable=False)  # in local currency (e.g. MWK)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payments = relationship("FeePayment", back_populates="term")


class FeePayment(Base):
    __tablename__ = "fee_payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    term_id = Column(Integer, ForeignKey("fee_terms.id"), nullable=False)
    amount_paid = Column(Integer, nullable=False, default=0)
    payment_date = Column(Date, nullable=True)
    receipt_number = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student")
    term = relationship("FeeTerm", back_populates="payments")
    recorded_by_user = relationship("User")
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=True)
    date = Column(Date, nullable=False, index=True)
    parent_phone = Column(String(20), nullable=True)
    parent_name = Column(String(100), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending / contacted / failed
    contacted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    contacted_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student")
    attendance = relationship("Attendance")
    contacted_by_user = relationship("User", foreign_keys=[contacted_by])
class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(150), nullable=False)          # e.g. Continuous Test 1
    total_marks = Column(Integer, nullable=False)        # e.g. 20 or 50
    date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    class_ = relationship("Class")
    subject = relationship("Subject")
    recorded_by_user = relationship("User")
    scores = relationship("AssessmentScore", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentScore(Base):
    __tablename__ = "assessment_scores"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    marks_obtained = Column(Integer, nullable=True)      # null = not submitted / absent
    comment = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("Assessment", back_populates="scores")
    student = relationship("Student")

class SubjectAttendance(Base):
    __tablename__ = "subject_attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(10), nullable=False)  # present / absent
    reason = Column(Text, nullable=True)
    communicated = Column(String(10), default="unknown")
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student")
    class_ = relationship("Class")
    subject = relationship("Subject")
    recorded_by_user = relationship("User")