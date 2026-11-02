"""Safe exception diagnostics for experiment raw logs.

Only code-owned GroqAPIError messages are persisted. Arbitrary exception
messages and chained request messages may contain prompts, credentials, or
student data, so they are deliberately excluded.
"""


def safe_exception_details(exc: Exception) -> dict[str, object]:
    """Return structured, non-sensitive details for an operational failure."""
    error_type = type(exc).__name__
    details: dict[str, object] = {"error_type": error_type}
    safe_message = str(exc) if error_type == "GroqAPIError" else ""

    cause = exc.__cause__ or exc.__context__
    seen: set[int] = set()
    cause_type = None
    http_status = None
    category = None

    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        cause_type = type(cause).__name__
        if cause_type == "HTTPError":
            category = "http_error"
            response = getattr(cause, "response", None)
            status = getattr(response, "status_code", None)
            if isinstance(status, int):
                http_status = status
            break
        if cause_type in {"Timeout", "ConnectTimeout", "ReadTimeout"}:
            category = "timeout"
            break
        if cause_type == "ConnectionError":
            category = "connection_error"
            break
        if cause_type == "JSONDecodeError":
            category = "invalid_response"
        cause = cause.__cause__ or cause.__context__

    if safe_message:
        details["error_message"] = safe_message
        if category is None:
            lowered = safe_message.casefold()
            if "http " in lowered:
                category = "http_error"
            elif "timeout" in lowered:
                category = "timeout"
            elif "connectionerror" in lowered:
                category = "connection_error"
            elif "invalid json" in lowered or "model answer" in lowered:
                category = "invalid_response"

    if cause_type is not None:
        details["error_cause_type"] = cause_type
    if http_status is not None:
        details["http_status"] = http_status
    details["error_category"] = category or "application_error"
    return details
