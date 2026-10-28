import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatbot.auth import can_access_student, hash_password, verify_password


def test_password_roundtrip():
    hashed = hash_password("correct-horse")
    assert verify_password("correct-horse", hashed)


def test_wrong_password_rejected():
    hashed = hash_password("correct-horse")
    assert not verify_password("wrong-password", hashed)


def test_admin_can_access_any_student():
    admin = {"role": "admin", "student_name": None}
    assert can_access_student(admin, "Alice Smith")
    assert can_access_student(admin, "Bob Johnson")


def test_faculty_can_access_any_student():
    faculty = {"role": "faculty", "student_name": None}
    assert can_access_student(faculty, "Charlie Brown")


def test_student_can_access_own_record():
    student = {"role": "student", "student_name": "Alice Smith"}
    assert can_access_student(student, "Alice Smith")
    # Case-insensitive match
    assert can_access_student(student, "alice smith")


def test_student_cannot_access_other_records():
    student = {"role": "student", "student_name": "Alice Smith"}
    assert not can_access_student(student, "Bob Johnson")


def test_student_with_no_linked_name_denied():
    student = {"role": "student", "student_name": None}
    assert not can_access_student(student, "Alice Smith")



def test_student_access_uses_stable_id_when_available():
    student = {"role": "student", "student_id": "uuid-1", "student_name": "Alice Smith"}
    assert can_access_student(student, "Someone Else", "uuid-1")
    assert not can_access_student(student, "Alice Smith", "uuid-2")


def test_student_with_missing_id_cannot_access_id_scoped_record():
    student = {"role": "student", "student_name": "Alice Smith"}
    assert not can_access_student(student, "Alice Smith", "uuid-1")
