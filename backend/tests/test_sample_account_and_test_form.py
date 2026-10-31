import pytest
from app.core.config import settings
from app.services.seeder_service import seed_sample_development_account, SAMPLE_USER_EMAIL, SAMPLE_USER_NAME
from app.core.database import get_database


def test_seed_sample_account_and_login(client):
    """Verify sample dev account seeding and authenticated login."""
    # 1. Dev login with sample account
    payload = {
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    }
    response = client.post("/api/auth/dev-login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == SAMPLE_USER_EMAIL
    assert data["user"]["name"] == SAMPLE_USER_NAME
    token = data["access_token"]

    # 2. Verify profile retrieval for sample user
    headers = {"Authorization": f"Bearer {token}"}
    prof_resp = client.get("/api/profiles/me", headers=headers)
    assert prof_resp.status_code == 200
    prof = prof_resp.json()
    assert prof["personalInformation"]["email"] == SAMPLE_USER_EMAIL
    assert prof["personalInformation"]["fullName"] == SAMPLE_USER_NAME
    assert prof["completionPercentage"] >= 90
    assert len(prof["skills"]["programmingLanguages"]) > 0


def test_dev_login_production_forbidden(client, monkeypatch):
    """Dev login must return 403 Forbidden in production mode."""
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DEBUG", False)

    response = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    assert response.status_code == 403
    assert "disabled in production" in response.json()["detail"].lower()


def test_dev_login_rejects_arbitrary_email_in_dev_mode(client, monkeypatch):
    """Dev login should reject unknown emails in non-test mode."""
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEBUG", True)

    response = client.post("/api/auth/dev-login", json={
        "email": "intruder@malicious.com",
        "name": "Intruder"
    })
    assert response.status_code == 400


def test_serve_test_form_endpoint(client):
    """Verify test-form is served correctly."""
    res1 = client.get("/test-form")
    assert res1.status_code == 200
    assert "ApplyForMe" in res1.text
    assert "<form" in res1.text or "id=\"first-name\"" in res1.text

    res2 = client.get("/test_application_form.html")
    assert res2.status_code == 200
    assert "ApplyForMe" in res2.text


def test_autofill_mapping_pipeline_on_sample_account(client):
    """Verify mapping fields on test form against seeded sample user profile."""
    # 1. Sign in as sample account
    login_res = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit form fields from test_application_form.html
    fields_payload = [
        {"elementId": "first-name", "name": "firstName", "type": "text", "label": "First Name"},
        {"elementId": "last-name", "name": "lastName", "type": "text", "label": "Last Name"},
        {"elementId": "email-address", "name": "email", "type": "email", "label": "Email Address"},
        {"elementId": "phone-number", "name": "phone", "type": "tel", "label": "Phone Number"},
        {"elementId": "linkedin-url", "name": "linkedin", "type": "url", "label": "LinkedIn Profile URL"},
        {"elementId": "github-url", "name": "github", "type": "url", "label": "GitHub Profile URL"},
        {"elementId": "portfolio-url", "name": "portfolio", "type": "url", "label": "Portfolio / Personal Website"},
        {"elementId": "current-city", "name": "city", "type": "text", "label": "Current City"},
        {"elementId": "graduation-year", "name": "graduationYear", "type": "select", "label": "Graduation Year"},
        {"elementId": "cover-letter", "name": "coverLetter", "type": "textarea", "label": "Cover Letter / Why do you want to work here?"},
        {"elementId": "work-auth-yes", "name": "workAuth", "type": "radio", "label": "Are you legally authorized to work in the United States?"},
    ]

    map_resp = client.post("/api/autofill/map-fields", json={"fields": fields_payload}, headers=headers)
    assert map_resp.status_code == 200
    mapped_data = map_resp.json()
    assert mapped_data["matchedFields"] > 0
    
    # Check key mappings
    mappings_by_field = {m["fieldName"]: m for m in mapped_data["mappings"] if m.get("fieldName")}
    assert "firstName" in mappings_by_field or any(m.get("elementIdentifier") == "first-name" for m in mapped_data["mappings"])
    assert any(m.get("fillValue") == SAMPLE_USER_EMAIL for m in mapped_data["mappings"])
    assert any("Sai" in str(m.get("fillValue")) for m in mapped_data["mappings"])
