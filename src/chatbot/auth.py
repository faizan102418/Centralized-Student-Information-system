"""Authentication and role-based access control (RBAC).

Admin/faculty can access any student record. Student accounts are restricted
to their own stable student_id; names are only a compatibility fallback when
the target record has no ID.
"""
import os
import time

import bcrypt
from jose import JWTError, jwt

from chatbot.database import get_db_connection

FULL_ACCESS_ROLES = {"admin", "faculty"}
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 8 * 60 * 60


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def get_user(username: str) -> dict | None:
    """Fetch a user and derive its canonical student name from student_id."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT u.id, u.username, u.password_hash, u.role, u.student_id, "
            "COALESCE(g.name, u.student_name) AS student_name "
            "FROM users u "
            "LEFT JOIN student_general_data g ON g.student_id = u.student_id "
            "WHERE u.username = %s",
            (username,),
        )
        return cursor.fetchone()
    finally:
        connection.close()


def authenticate(username: str, password: str) -> dict | None:
    """Return the user record if credentials are valid, otherwise None."""
    if not username or not password:
        return None
    user = get_user(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user


def can_access_student(
    user: dict,
    student_name: str,
    student_id: str | None = None,
) -> bool:
    """Check authorization; use stable IDs for student-to-record comparisons."""
    if user.get("role") in FULL_ACCESS_ROLES:
        return True
    if user.get("role") != "student":
        return False

    own_id = user.get("student_id")
    if student_id is not None:
        return bool(own_id) and str(own_id) == str(student_id)

    # Compatibility for older callers/tests that do not yet provide a record ID.
    own_name = (user.get("student_name") or "").strip().casefold()
    return bool(own_name) and own_name == student_name.strip().casefold()


def create_access_token(user: dict) -> str:
    """Issue a signed JWT encoding the user's identity and role."""
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "student_id": user.get("student_id"),
        "student_name": user.get("student_name"),
        "exp": int(time.time()) + JWT_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Verify and decode a JWT, returning the embedded user info or None if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    return {
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "student_id": payload.get("student_id"),
        "student_name": payload.get("student_name"),
    }
