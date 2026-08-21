"""Authentication and role-based access control (RBAC).

Three roles:
- admin / faculty: full access to any student's record
- student: can only query their own record (matched via users.student_name)
"""

import os
import time

import bcrypt
from jose import JWTError, jwt

from chatbot.database import get_db_connection

FULL_ACCESS_ROLES = {"admin", "faculty"}

# JWT config for the FastAPI backend. In production, JWT_SECRET_KEY MUST be
# set to a long random value via environment variable - the default here
# is only for local development and is intentionally obvious about that.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_SECONDS = 8 * 60 * 60  # 8 hours


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB - treat as a failed login, not a crash.
        return False


def get_user(username: str) -> dict | None:
    """Fetch a user record by username, or None if it doesn't exist."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, password_hash, role, student_name "
            "FROM users WHERE username = %s",
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


def can_access_student(user: dict, student_name: str) -> bool:
    """Check whether a logged-in user is allowed to view a given student's record."""
    if user["role"] in FULL_ACCESS_ROLES:
        return True
    if user["role"] == "student":
        own_name = (user.get("student_name") or "").strip().lower()
        return own_name != "" and own_name == student_name.strip().lower()
    return False


def create_access_token(user: dict) -> str:
    """Issue a signed JWT encoding the user's identity and role."""
    payload = {
        "sub": user["username"],
        "role": user["role"],
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
        "student_name": payload.get("student_name"),
    }
