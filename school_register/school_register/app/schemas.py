from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum


class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"


class CommunicatedStatus(str, Enum):
    yes = "yes"
    no = "no"
    unknown = "unknown"


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: str = "teacher"


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Class ----------
class ClassOut(BaseModel):
    id: int
    name: str
    form: int
    stream: str

    class Config:
        from_attributes = True


# ---------- Student ----------
class StudentCreate(BaseModel):
    admission_number: str
    first_name: str
    last_name: str
    class_id: int
    gender: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_name: Optional[str] = None


class StudentOut(BaseModel):
    id: int
    admission_number: str
    first_name: str
    last_name: str
    full_name: str
    class_id: int
    gender: Optional[str]
    parent_phone: Optional[str]
    parent_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Attendance ----------
class AttendanceMark(BaseModel):
    student_id: int
    status: AttendanceStatus
    reason: Optional[str] = None
    communicated: CommunicatedStatus = CommunicatedStatus.unknown
    notes: Optional[str] = None


class AttendanceBulk(BaseModel):
    class_id: int
    date: date
    records: List[AttendanceMark]


class AttendanceOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    admission_number: str
    status: str
    reason: Optional[str]
    communicated: str
    notes: Optional[str]
    recorded_by_name: str

    class Config:
        from_attributes = True


class DailyReportSummary(BaseModel):
    class_name: str
    date: date
    total_students: int
    total_present: int
    total_absent: int
    present_percentage: float
    absentees: List[AttendanceOut]

# ---------- Subjects & Activities ----------

class SubjectOut(BaseModel):
    id: int
    name: str
    stream: Optional[str] = None

    class Config:
        from_attributes = True


class ClassActivityCreate(BaseModel):
    class_id: int
    subject_id: int
    date: date
    description: str
    participation_notes: Optional[str] = None


class ClassActivityOut(BaseModel):
    id: int
    class_id: int
    subject_id: int
    subject_name: str
    date: date
    description: str
    participation_notes: Optional[str]
    recorded_by_name: str
    created_at: datetime

    class Config:
        from_attributes = True

# ---------- Fees ----------

class FeeTermCreate(BaseModel):
    name: str
    year: int
    term_number: int
    amount_expected: int


class FeeTermOut(BaseModel):
    id: int
    name: str
    year: int
    term_number: int
    amount_expected: int
    is_active: bool

    class Config:
        from_attributes = True


class FeePaymentCreate(BaseModel):
    student_id: int
    term_id: int
    amount_paid: int
    payment_date: Optional[date] = None
    receipt_number: Optional[str] = None
    notes: Optional[str] = None


class StudentFeeStatus(BaseModel):
    student_id: int
    admission_number: str
    full_name: str
    class_name: str
    amount_expected: int
    amount_paid: int
    balance: int
    status: str  # Paid / Partial / Not Paid

# ---------- Assessments / Grades ----------

class AssessmentCreate(BaseModel):
    class_id: int
    subject_id: int
    title: str
    total_marks: int
    date: date
    description: Optional[str] = None


class ScoreEntry(BaseModel):
    student_id: int
    marks_obtained: Optional[int] = None
    comment: Optional[str] = None


class AssessmentScoresBulk(BaseModel):
    assessment_id: int
    scores: List[ScoreEntry]



# ---------- Subject Attendance ----------

class SubjectAttendanceMark(BaseModel):
    student_id: int
    status: AttendanceStatus
    reason: Optional[str] = None
    communicated: CommunicatedStatus = CommunicatedStatus.unknown
    notes: Optional[str] = None


class SubjectAttendanceBulk(BaseModel):
    class_id: int
    subject_id: int
    date: date
    records: List[SubjectAttendanceMark]