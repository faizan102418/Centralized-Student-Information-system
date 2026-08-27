"""MySQL access layer: connects to the database and assembles per-student records."""

import mysql.connector

from chatbot.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_USER


def get_db_connection() -> mysql.connector.MySQLConnection:
    """Open and return a new MySQL connection."""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        return connection
    except mysql.connector.Error as exc:
        raise RuntimeError(f"Could not connect to MySQL database '{DB_NAME}': {exc}") from exc


def fetch_student_data_from_db() -> str:
    """
    Fetch and merge student data from the general, scholarship, and fee
    tables, keyed by student_id, and return it as newline-separated text
    ready to be chunked and embedded.

    Uses student_id (a stable UUID, see data/migrations/002_add_student_uuid.sql)
    rather than name for merging, so two students who happen to share a
    name are never incorrectly conflated into one record.
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

        for student_id, gd in general_data.items():
            parts = [f"Student Name: {gd.get('name')}"]
            if gd.get("roll_number"):
                parts.append(f"Roll Number: {gd.get('roll_number')}")
            if gd.get("discipline"):
                parts.append(f"Discipline: {gd.get('discipline')}")

            if sd := scholarship_data.get(student_id):
                if sd.get("scholarship_name"):
                    parts.append(f"Scholarship Name: {sd.get('scholarship_name')}")
                if sd.get("enrollment_status"):
                    parts.append(f"Scholarship Enrollment Status: {sd.get('enrollment_status')}")

            if fd := fee_data.get(student_id):
                if fd.get("registration_number"):
                    parts.append(f"Registration Number: {fd.get('registration_number')}")
                if fd.get("fee_status"):
                    parts.append(f"Fee Status: {fd.get('fee_status')}")

            records.append(" -- ".join(parts))

        return "\n\n".join(records)

    except Exception as exc:
        raise RuntimeError(f"Failed to fetch student data: {exc}") from exc
    finally:
        if connection is not None and connection.is_connected():
            connection.close()
