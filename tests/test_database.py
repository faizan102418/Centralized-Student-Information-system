from unittest.mock import MagicMock

import pytest

from chatbot import database


def make_mock_connection(fetchone_result=None, execute_error=None):
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value = cursor
    connection.is_connected.return_value = True
    cursor.fetchone.return_value = fetchone_result

    if execute_error:
        cursor.execute.side_effect = execute_error

    return connection, cursor


def test_unsupported_field_does_not_open_database_connection(monkeypatch):
    connection_factory = MagicMock()
    monkeypatch.setattr(database, "get_db_connection", connection_factory)

    result = database.fetch_student_field_availability_from_db(
        "SYN-001", "unknown_field"
    )

    assert result == {
        "available": False,
        "reason": "unsupported_field",
    }
    connection_factory.assert_not_called()


def test_missing_related_record(monkeypatch):
    connection, cursor = make_mock_connection(fetchone_result=None)
    monkeypatch.setattr(database, "get_db_connection", lambda: connection)

    result = database.fetch_student_field_availability_from_db(
        "SYN-001", "fee_status"
    )

    assert result == {
        "available": False,
        "reason": "missing_related_record",
    }
    cursor.execute.assert_called_once()
    assert cursor.execute.call_args.args[1] == ("SYN-001",)
    connection.close.assert_called_once()


@pytest.mark.parametrize("available_value", [0, False, None])
def test_null_or_empty_source_value(monkeypatch, available_value):
    connection, cursor = make_mock_connection(
        fetchone_result={"available": available_value}
    )
    monkeypatch.setattr(database, "get_db_connection", lambda: connection)

    result = database.fetch_student_field_availability_from_db(
        "SYN-001", "fee_status"
    )

    assert result == {
        "available": False,
        "reason": "null_or_empty_value",
    }
    connection.close.assert_called_once()


def test_source_value_present(monkeypatch):
    connection, cursor = make_mock_connection(
        fetchone_result={"available": 1}
    )
    monkeypatch.setattr(database, "get_db_connection", lambda: connection)

    result = database.fetch_student_field_availability_from_db(
        "SYN-001", "fee_status"
    )

    assert result == {
        "available": True,
        "reason": "source_value_present",
    }
    connection.close.assert_called_once()


def test_database_error_is_wrapped_and_connection_closed(monkeypatch):
    connection, cursor = make_mock_connection(
        execute_error=Exception("simulated database failure")
    )
    monkeypatch.setattr(database, "get_db_connection", lambda: connection)

    with pytest.raises(
        RuntimeError, match="Failed to inspect source field availability"
    ):
        database.fetch_student_field_availability_from_db(
            "SYN-001", "fee_status"
        )

    connection.close.assert_called_once()
