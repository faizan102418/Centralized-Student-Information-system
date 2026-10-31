"""Deterministic evidence checks for structured student-record answers.

This narrow verifier checks whether an answer contains the requested field value
in retrieved evidence. It is not a general-purpose fact checker and cannot prove
that every claim in a longer response is grounded. Unknown/missing fields fail closed.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class EvidenceVerification:
    supported: bool
    field: str | None
    evidence_value: str | None
    reason: str


FIELD_ALIASES = (
    ("scholarship_name", (r"\bscholarship name\b", r"\bname of (?:the )?scholarship\b")),
    ("enrollment_status", (r"\bscholarship status\b", r"\benrollment status\b", r"\benrolment status\b")),
    ("fee_status", (r"\bfee status\b", r"\bfee paid\b", r"\bfees paid\b")),
    ("discipline", (r"\bdiscipline\b", r"\bdepartment\b", r"\bmajor\b", r"\bsubject area\b")),
    ("roll_number", (r"\broll number\b", r"\broll no\.?\b")),
    ("registration_number", (r"\bregistration number\b", r"\bregistration no\.?\b")),
)
EVIDENCE_LABELS = {
    "scholarship_name": ("scholarship name",),
    "enrollment_status": ("scholarship enrollment status", "enrollment status", "enrolment status"),
    "fee_status": ("fee status",),
    "discipline": ("discipline",),
    "roll_number": ("roll number",),
    "registration_number": ("registration number",),
}


def requested_field(question: str) -> str | None:
    """Return a recognized structured field mentioned in the question."""
    normalized = " ".join(question.casefold().split())
    for field, patterns in FIELD_ALIASES:
        if any(re.search(pattern, normalized) for pattern in patterns):
            return field
    return None


def _extract_field_value(evidence_text: str, field: str) -> str | None:
    """Extract a value from the app's ' -- ' record representation."""
    accepted = {label.casefold() for label in EVIDENCE_LABELS[field]}
    for segment in re.split(r"\s+--\s+|\n+", evidence_text):
        label, separator, value = segment.partition(":")
        if separator and label.strip().casefold() in accepted:
            return value.strip() or None
    return None


def verify_answer_against_evidence(question: str, answer: str, evidence_text: str) -> EvidenceVerification:
    """Fail closed unless the answer contains the retrieved value for the asked field."""
    field = requested_field(question)
    if field is None:
        return EvidenceVerification(False, None, None, "unrecognized_requested_field")
    value = _extract_field_value(evidence_text, field)
    if value is None:
        return EvidenceVerification(False, field, None, "requested_field_missing_from_evidence")
    normalized_answer = " ".join(answer.casefold().split())
    normalized_value = " ".join(value.casefold().split())
    if normalized_value not in normalized_answer:
        return EvidenceVerification(False, field, value, "answer_does_not_contain_evidence_value")
    return EvidenceVerification(True, field, value, "requested_value_found_in_evidence")
