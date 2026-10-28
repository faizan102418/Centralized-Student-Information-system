import sys
from pathlib import Path
from unittest.mock import Mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatbot import jev_verifier
from chatbot.jev_verifier import JevVerifier


def mock_response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def test_high_score_is_only_provisional_accept(monkeypatch):
    post = Mock(return_value=mock_response({"questions": {"candidate_match": {"noul": 0.91}}}))
    monkeypatch.setattr(jev_verifier.requests, "post", post)

    result = JevVerifier(api_key="test-key").verify(
        "What is John Smith's discipline?", "John Smith", ["John Smith"]
    )

    assert result.decision == "ACCEPT"
    assert result.probability_yes == 0.91
    assert "not identity proof" in result.reason
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert post.call_args.kwargs["json"]["state"]["candidate_names"] == ["John Smith"]


def test_low_score_abstains(monkeypatch):
    monkeypatch.setattr(
        jev_verifier.requests,
        "post",
        Mock(return_value=mock_response({"noul": 0.42})),
    )
    result = JevVerifier(api_key="test-key").verify("query", "Alice Smith", ["Alice Smith"])
    assert result.decision == "ABSTAIN"


def test_missing_key_abstains_without_network(monkeypatch):
    post = Mock()
    monkeypatch.setattr(jev_verifier.requests, "post", post)
    result = JevVerifier(api_key="").verify("query", "Alice Smith", ["Alice Smith"])
    assert result.decision == "ABSTAIN"
    post.assert_not_called()


def test_api_failure_abstains(monkeypatch):
    monkeypatch.setattr(
        jev_verifier.requests,
        "post",
        Mock(side_effect=requests.Timeout()),
    )
    result = JevVerifier(api_key="test-key").verify("query", "Alice Smith", ["Alice Smith"])
    assert result.decision == "ABSTAIN"
    assert "Timeout" in result.reason


def test_invalid_score_abstains(monkeypatch):
    monkeypatch.setattr(
        jev_verifier.requests,
        "post",
        Mock(return_value=mock_response({"noul": 1.5})),
    )
    result = JevVerifier(api_key="test-key").verify("query", "Alice Smith", ["Alice Smith"])
    assert result.decision == "ABSTAIN"
