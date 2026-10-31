import pytest


def test_dev_login(client):
    payload = {
        "email": "test.applicant@university.edu",
        "name": "Jane Doe"
    }
    response = client.post("/api/auth/dev-login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["name"] == payload["name"]


def test_get_me_unauthorized(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_authorized(client, auth_headers, test_user):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["name"] == test_user["name"]


def test_google_auth_new_account(client):
    """Test first-time Google sign-in registers account and returns JWT session."""
    payload = {"id_token": "dev_token_sarah_new"}
    response = client.post("/api/auth/google", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "sarah_new@example.com" in data["user"]["email"]
    assert data["user"]["googleId"] == "google_dev_sarah_new"
    assert "createdAt" in data["user"]
    assert "lastLoginAt" in data["user"]


def test_google_auth_existing_account(client):
    """Test returning Google user signs in without creating duplicate account."""
    payload = {"id_token": "dev_token_repeat_user"}
    # First login (create)
    res1 = client.post("/api/auth/google", json=payload)
    assert res1.status_code == 200
    user1 = res1.json()["user"]

    # Second login (update lastLoginAt, same user ID)
    res2 = client.post("/api/auth/google", json=payload)
    assert res2.status_code == 200
    user2 = res2.json()["user"]
    assert user1["_id"] == user2["_id"]
    assert user1["email"] == user2["email"]


def test_google_auth_invalid_token(client):
    """Test rejected invalid / malformed token returns 401 Unauthorized."""
    payload = {"id_token": "invalid_raw_token_xyz_123"}
    response = client.post("/api/auth/google", json=payload)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_google_auth_expired_or_unverified_token(client):
    """Test rejected expired or unverified token returns 401 Unauthorized."""
    payload_expired = {"id_token": "dev_token_expired_alex"}
    res_expired = client.post("/api/auth/google", json=payload_expired)
    assert res_expired.status_code == 401

    payload_unverified = {"id_token": "dev_token_unverified_sam"}
    res_unverified = client.post("/api/auth/google", json=payload_unverified)
    assert res_unverified.status_code == 401


def test_logout(client, auth_headers):
    """Test authenticated logout endpoint."""
    response = client.post("/api/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
