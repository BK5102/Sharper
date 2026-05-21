"""Tests for the FastAPI wrapper. Mocks critique_question so we don't hit Anthropic."""

from __future__ import annotations

from unittest.mock import patch

import anthropic
import pytest
from fastapi.testclient import TestClient

from sharper.api import app
from sharper.schema import Critique, Finding, RubricItem, Severity

client = TestClient(app)


def _fake_critique() -> Critique:
    return Critique(
        findings=[
            Finding(
                rubric_item=RubricItem.operationalization,
                severity=Severity.high,
                quoted_span="big deal",
                issue="'big deal' is not operationalized.",
                explanation="No measurable threshold defined.",
                suggested_rewrite="achieves at least 50% adoption among Fortune 500 companies",
            )
        ],
        overall_assessment="One high-severity defect.",
    )


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_lint_happy_path() -> None:
    with patch("sharper.api.critique_question", return_value=_fake_critique()):
        resp = client.post("/api/lint", json={"question": "Will AI be a big deal by 2030?"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["findings"]) == 1
    assert body["findings"][0]["rubric_item"] == "operationalization"
    assert body["findings"][0]["severity"] == "high"
    assert body["findings"][0]["quoted_span"] == "big deal"
    assert body["findings"][0]["suggested_rewrite"] is not None


def test_lint_rejects_empty_question() -> None:
    resp = client.post("/api/lint", json={"question": ""})
    # Pydantic validation rejects min_length=1 -- returns 422
    assert resp.status_code == 422


def test_lint_rejects_whitespace_only_question() -> None:
    resp = client.post("/api/lint", json={"question": "   \n  "})
    # Passes Pydantic min_length but our explicit strip check returns 400
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_lint_rejects_oversized_question() -> None:
    resp = client.post("/api/lint", json={"question": "x" * 4001})
    # Pydantic max_length kicks in -- 422
    assert resp.status_code == 422


def test_lint_missing_question_field_is_422() -> None:
    resp = client.post("/api/lint", json={})
    assert resp.status_code == 422
