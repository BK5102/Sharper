"""Tests for the FastAPI wrapper. Mocks critique_question so we don't hit Anthropic."""

from __future__ import annotations

import json
from unittest.mock import patch

import anthropic
import pytest
from fastapi.testclient import TestClient

from sharper.api import MAX_BODY_BYTES, app
from sharper.schema import Critique, Finding, RubricItem, Severity

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear auth and rate-limit env vars before every test in this file.

    backend/.env (loaded by api.py via load_dotenv(override=True)) may contain
    real credentials. Wipe them so tests don't depend on local env state.
    Tests that need a specific mode re-set the vars explicitly.

    Upstash vars are cleared so the rate limiter goes fail-open (no real
    Upstash calls). Without this, the anonymous 10 req/hr cap is hit during
    the full test suite run and later tests get 429.
    """
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)


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


# ----- /api/health ---------------------------------------------------------


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


# ----- Security headers are set on every response --------------------------


def test_security_headers_set_on_health() -> None:
    resp = client.get("/api/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert resp.headers["permissions-policy"] == "interest-cohort=()"


# ----- /api/lint happy path + input validation ------------------------------


def test_lint_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # No SHARPER_API_TOKEN configured -> dependency falls through.
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    with patch("sharper.api.critique_question", return_value=_fake_critique()):
        resp = client.post("/api/lint", json={"question": "Will AI be a big deal by 2030?"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["findings"]) == 1
    assert body["findings"][0]["rubric_item"] == "operationalization"
    assert body["findings"][0]["severity"] == "high"
    assert body["findings"][0]["quoted_span"] == "big deal"
    assert body["findings"][0]["suggested_rewrite"] is not None


def test_lint_rejects_empty_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    resp = client.post("/api/lint", json={"question": ""})
    assert resp.status_code == 422


def test_lint_rejects_whitespace_only_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    resp = client.post("/api/lint", json={"question": "   \n  "})
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_lint_rejects_oversized_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    resp = client.post("/api/lint", json={"question": "x" * 4001})
    assert resp.status_code == 422


def test_lint_missing_question_field_is_422(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    resp = client.post("/api/lint", json={})
    assert resp.status_code == 422


# ----- Body size limit -----------------------------------------------------


def test_lint_rejects_oversized_body_via_content_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bodies whose Content-Length exceeds the cap return 413 before Pydantic runs."""
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    # Build a body larger than MAX_BODY_BYTES. Use raw content so we can ensure
    # the declared Content-Length triggers the middleware.
    big_payload = json.dumps({"question": "x" * (MAX_BODY_BYTES * 2)})
    resp = client.post(
        "/api/lint",
        content=big_payload,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413
    assert "body exceeds" in resp.json()["detail"]


# ----- Sanitized upstream errors -------------------------------------------


def test_lint_sanitizes_anthropic_apistatuserror(monkeypatch: pytest.MonkeyPatch) -> None:
    """Anthropic error details (model name, prompt context) must not leak to the client."""
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    # Fake an APIStatusError with a 400-class status (client-side rejection).
    fake_response = type("R", (), {"status_code": 400, "headers": {}, "request": None})()
    err = anthropic.APIStatusError(
        "internal-only message that should NOT leak to the client",
        response=fake_response,  # type: ignore[arg-type]
        body=None,
    )
    err.status_code = 400  # in case the SDK doesn't set this from response
    with patch("sharper.api.critique_question", side_effect=err):
        resp = client.post("/api/lint", json={"question": "test"})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    # The client-side message must NOT contain the raw upstream error string.
    assert "internal-only" not in detail
    assert "rejected" in detail.lower()


def test_lint_sanitizes_anthropic_generic_apierror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    err = anthropic.APIConnectionError(message="dns failure leaking infra detail", request=None)  # type: ignore[arg-type]
    with patch("sharper.api.critique_question", side_effect=err):
        resp = client.post("/api/lint", json={"question": "test"})
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert "dns failure" not in detail
    assert detail == "upstream API error"


# ----- Auth gate -----------------------------------------------------------


def test_lint_requires_bearer_when_token_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "test-secret-token")
    with patch("sharper.api.critique_question", return_value=_fake_critique()):
        # No Authorization header -> 401
        resp = client.post("/api/lint", json={"question": "test"})
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_lint_rejects_wrong_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "test-secret-token")
    with patch("sharper.api.critique_question", return_value=_fake_critique()):
        resp = client.post(
            "/api/lint",
            json={"question": "test"},
            headers={"authorization": "Bearer not-the-real-token"},
        )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_lint_accepts_correct_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "test-secret-token")
    with patch("sharper.api.critique_question", return_value=_fake_critique()):
        resp = client.post(
            "/api/lint",
            json={"question": "test"},
            headers={"authorization": "Bearer test-secret-token"},
        )
    assert resp.status_code == 200


def test_health_does_not_require_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Liveness probes must work without auth, even when token is configured."""
    monkeypatch.setenv("SHARPER_API_TOKEN", "test-secret-token")
    resp = client.get("/api/health")
    assert resp.status_code == 200


# ----- run() refuses non-loopback bind without token -----------------------


def test_run_refuses_public_bind_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from sharper.api import run

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SHARPER_API_HOST", "0.0.0.0")
    with pytest.raises(SystemExit) as exc_info:
        run()
    assert "SHARPER_API_TOKEN" in str(exc_info.value)


def test_run_allows_public_bind_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """When token is configured, run() proceeds to uvicorn (which we mock)."""
    monkeypatch.setenv("SHARPER_API_TOKEN", "real-token")
    monkeypatch.setenv("SHARPER_API_HOST", "0.0.0.0")
    with patch("uvicorn.run") as mock_run:
        from sharper.api import run

        run()
    assert mock_run.called
    _, kwargs = mock_run.call_args
    assert kwargs["host"] == "0.0.0.0"


def test_run_allows_loopback_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loopback bind doesn't require the token (local dev convenience)."""
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    monkeypatch.setenv("SHARPER_API_HOST", "127.0.0.1")
    with patch("uvicorn.run") as mock_run:
        from sharper.api import run

        run()
    assert mock_run.called


# ----- mode param -----------------------------------------------------------


def test_lint_accepts_civic_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    with patch("sharper.api.critique_question", return_value=_fake_critique()) as mock_cq:
        resp = client.post(
            "/api/lint",
            json={"question": "Will the program reduce homelessness by 2027?", "mode": "civic"},
        )
    assert resp.status_code == 200
    # Confirm mode was passed through to critique_question.
    _, kwargs = mock_cq.call_args
    assert kwargs.get("mode") == "civic"


def test_lint_rejects_unknown_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    resp = client.post("/api/lint", json={"question": "test", "mode": "unknown"})
    assert resp.status_code == 422


def test_lint_default_mode_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Omitting mode should default to 'default', not raise."""
    monkeypatch.delenv("SHARPER_API_TOKEN", raising=False)
    with patch("sharper.api.critique_question", return_value=_fake_critique()) as mock_cq:
        resp = client.post("/api/lint", json={"question": "Will AI be a big deal by 2030?"})
    assert resp.status_code == 200
    _, kwargs = mock_cq.call_args
    assert kwargs.get("mode") == "default"


# ----- kill-switch ----------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_kill_switch():
    """Reset the kill-switch flag before every test so tests don't bleed into each other."""
    import sharper.api as api_mod
    api_mod._DISABLED = False
    yield
    api_mod._DISABLED = False


def test_disable_endpoint_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "test-secret-token")
    resp = client.post("/api/admin/disable")
    assert resp.status_code == 401


def test_disable_endpoint_disables_linting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARPER_API_TOKEN", "test-secret-token")
    # Disable the linter.
    resp = client.post(
        "/api/admin/disable",
        headers={"authorization": "Bearer test-secret-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "disabled"

    # Subsequent lint requests must return 503.
    with patch("sharper.api.critique_question", return_value=_fake_critique()):
        resp2 = client.post(
            "/api/lint",
            json={"question": "test"},
            headers={"authorization": "Bearer test-secret-token"},
        )
    assert resp2.status_code == 503
    assert "disabled" in resp2.json()["detail"]


def test_health_unaffected_by_disable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Health check must keep returning 200 even when the linter is disabled."""
    monkeypatch.setenv("SHARPER_API_TOKEN", "test-secret-token")
    client.post(
        "/api/admin/disable",
        headers={"authorization": "Bearer test-secret-token"},
    )
    resp = client.get("/api/health")
    assert resp.status_code == 200
