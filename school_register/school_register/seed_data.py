"""
Seed the database with:
- Admin + sample teachers
- 8 classes (Form 1-4 × Humanities/Sciences)
- Sample students
- Subjects (8 per stream)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app import models
from app.auth import get_password_hash

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ---------- Users ----------
        if not db.query(models.User).filter(models.User.username == "admin").first():
            admin = models.User(
                username="admin",
                full_name="School Administrator",
                hashed_password=get_password_hash("admin123"),
                role="admin"
            )
            db.add(admin)
            print("✓ Created admin user (username: admin / password: admin123)")

        teachers = [
            ("teacher1", "Mr. John Mwangi", "teacher123"),
            ("teacher2", "Ms. Grace Wanjiku", "teacher123"),
            ("teacher3", "Mr. Peter Otieno", "teacher123"),
        ]
        for username, full_name, pwd in teachers:
            if not db.query(models.User).filter(models.User.username == username).first():
                t = models.User(
                    username=username,
                    full_name=full_name,
                    hashed_password=get_password_hash(pwd),
                    role="teacher"
                )
                db.add(t)
                print(f"✓ Created teacher: {username} / {pwd}")

        db.commit()

        # ---------- Classes ----------
        streams = ["Humanities", "Sciences"]
        classes_created = []
        for form in range(1, 5):
            for stream in streams:
                name = f"Form {form} {stream}"
                existing = db.query(models.Class).filter(models.Class.name == name).first()
                if not existing:
                    c = models.Class(name=name, form=form, stream=stream)
                    db.add(c)
                    classes_created.append(name)
        db.commit()
        if classes_created:
            print(f"✓ Created classes: {', '.join(classes_created)}")
        else:
            print("✓ Classes already exist")

        all_classes = db.query(models.Class).order_by(models.Class.form, models.Class.stream).all()

        # ---------- Subjects ----------
        # 8 subjects for Humanities and 8 for Sciences
        humanities_subjects = [
            "English", "Chichewa", "History", "Geography",
            "Christian Religious Education", "Business Studies", "French", "Literature"
        ]
        sciences_subjects = [
            "English", "Chichewa", "Mathematics", "Biology",
            "Chemistry", "Physics", "Agriculture", "Computer Studies"
        ]

        subjects_created = 0
        for name in humanities_subjects:
            if not db.query(models.Subject).filter(models.Subject.name == name, models.Subject.stream == "Humanities").first():
                db.add(models.Subject(name=name, stream="Humanities"))
                subjects_created += 1

        for name in sciences_subjects:
            if not db.query(models.Subject).filter(models.Subject.name == name, models.Subject.stream == "Sciences").first():
                db.add(models.Subject(name=name, stream="Sciences"))
                subjects_created += 1

        db.commit()
        print(f"✓ Created {subjects_created} subjects")

        # ---------- Sample Students ----------
        first_names_m = ["James", "David", "Brian", "Kevin", "Samuel", "Daniel", "Michael", "Joseph"]
        first_names_f = ["Mary", "Faith", "Grace", "Ann", "Jane", "Mercy", "Esther", "Ruth"]
        last_names = ["Kamau", "Otieno", "Wanjiku", "Ochieng", "Njoroge", "Achieng", "Mwangi", "Omondi", "Kariuki", "Akinyi"]

        student_count = 0
        for cls in all_classes:
            existing_count = db.query(models.Student).filter(models.Student.class_id == cls.id).count()
            if existing_count > 0:
                continue

            for i in range(1, 13):
                gender = "Male" if i % 2 == 1 else "Female"
                first = first_names_m[(i-1) % len(first_names_m)] if gender == "Male" else first_names_f[(i-1) % len(first_names_f)]
                last = last_names[(i + cls.form) % len(last_names)]
                adm = f"{cls.form}{cls.stream[0]}{1000 + i + cls.id*10}"

                s = models.Student(
                    admission_number=adm,
                    first_name=first,
                    last_name=last,
                    class_id=cls.id,
                    gender=gender,
                    parent_phone=f"07{20 + i}{100000 + i*7}"[:10],
                    parent_name=f"Parent of {first}"
                )
                db.add(s)
                student_count += 1

        db.commit()
        if student_count:
            print(f"✓ Created {student_count} sample students")
        else:
            print("✓ Students already exist")

        print("\n✅ Database seeded successfully!")
        print("\nLogin credentials:")
        print("  Admin   → username: admin    password: admin123")
        print("  Teacher → username: teacher1 password: teacher123")
        print("  Teacher → username: teacher2 password: teacher123")

    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()