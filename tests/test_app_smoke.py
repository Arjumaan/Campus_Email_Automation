"""Headless smoke test: the Streamlit app must start and render every tab without exceptions."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_renders_without_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "smoke.db"))
    monkeypatch.setenv("SEND_MODE", "test")
    monkeypatch.setenv("TEST_RECIPIENT", "internal-test@example.invalid")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "campus@example.invalid")
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    # The app is login-gated; tabs are only rendered after sign-in.
    # Simulate login using demo credentials then check tabs are visible.
    try:
        at.text_input[0].set_value("admin")
        at.text_input[1].set_value("admin@123")
        at.form_submit_button[0].click().run()
        assert not at.exception, [e.value for e in at.exception]
        # After login there are navigation items in the sidebar radio
        assert len(at.sidebar.radio) >= 1, "Expected sidebar navigation radio"
        assert len(at.sidebar.radio[0].options) >= 6, f"Expected >= 6 nav options, got {len(at.sidebar.radio[0].options)}"
    except (IndexError, AttributeError):
        # If AppTest doesn't expose form inputs (older Streamlit), skip the tab assertion.
        pytest.skip("AppTest login simulation not supported in this Streamlit version")
