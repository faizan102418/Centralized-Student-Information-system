"""MySQL access layer: fetch student records keyed by stable student IDs."""

import mysql.connector

from chatbot.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER


def get_db_connection() -> mysql.connector.MySQLConnection:
    """Open and return a new MySQL connection."""
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
    except mysql.connector.Error as exc:
        raise RuntimeError(f"Could not connect to MySQL database '{DB_NAME}': {exc}") from exc


def fetch_student_records_from_db() -> list[dict]:
    """Return one canonical record per student, keyed by stable student_id.

    Each record contains student_id, name, and a text representation used by
    retrieval. Related tables are joined in Python by ID, never by student name.
    """
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT student_id, roll_number, name, discipline FROM student_general_data")
        general_data = {row["student_id"]: row for row in cursor.fetchall() if row["student_id"]}

        cursor.execute(
            "SELECT student_id, scholarship_name, enrollment_status FROM student_scholarship"
        )
        scholarship_data = {
            row["student_id"]: row for row in cursor.fetchall() if row["student_id"]
        }

        cursor.execute(
            "SELECT student_id, registration_number, fee_status FROM student_fee_submission"
        )
        fee_data = {row["student_id"]: row for row in cursor.fetchall() if row["student_id"]}

        records = []
        for student_id, general in general_data.items():
            parts = [f"Student Name: {general.get('name')}"]
            if general.get("roll_number"):
                parts.append(f"Roll Number: {general.get('roll_number')}")
            if general.get("discipline"):
                parts.append(f"Discipline: {general.get('discipline')}")

            scholarship = scholarship_data.get(student_id)
            if scholarship:
                if scholarship.get("scholarship_name"):
                    parts.append(f"Scholarship Name: {scholarship['scholarship_name']}")
                if scholarship.get("enrollment_status"):
                    parts.append(f"Scholarship Enrollment Status: {scholarship['enrollment_status']}")

            fee = fee_data.get(student_id)
            if fee:
                if fee.get("registration_number"):
                    parts.append(f"Registration Number: {fee['registration_number']}")
                if fee.get("fee_status"):
                    parts.append(f"Fee Status: {fee['fee_status']}")

            records.append({
                "student_id": str(student_id),
                "name": str(general.get("name") or "").strip(),
                "text": " -- ".join(parts),
            })
        return records
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch student data: {exc}") from exc
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def fetch_student_names_from_db() -> list[dict]:
    """Return the minimal canonical directory used for deterministic matching."""
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT student_id, name FROM student_general_data "
            "WHERE student_id IS NOT NULL AND name IS NOT NULL"
        )
        return [
            {"student_id": str(row["student_id"]), "name": str(row["name"]).strip()}
            for row in cursor.fetchall()
            if row.get("student_id") and row.get("name")
        ]
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch student directory: {exc}") from exc
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def fetch_student_data_from_db() -> str:
    """Backward-compatible text dump used by diagnostics and existing callers."""
    return "\n\n".join(record["text"] for record in fetch_student_records_from_db())
