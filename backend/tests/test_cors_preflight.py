def test_cors_preflight_chrome_extension(client):
    """Verify OPTIONS preflight succeeds for the ApplyForMe Chrome extension."""
    origin = "chrome-extension://dccdppkggcalleledhmbclldddnokhok"
    response = client.options(
        "/api/autofill/map-fields",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in response.headers.get("access-control-allow-methods", "")


def test_cors_preflight_vite_dev_servers(client):
    """Verify OPTIONS preflight succeeds for Vite dev servers (5173 and 5174)."""
    for origin in ["http://localhost:5173", "http://localhost:5174"]:
        response = client.options(
            "/api/autofill/map-fields",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_profile_endpoint(client):
    """Verify OPTIONS preflight succeeds for profile endpoints."""
    origin = "chrome-extension://dccdppkggcalleledhmbclldddnokhok"
    response = client.options(
        "/api/profiles/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_post_actual_request_headers(client, auth_headers):
    """Verify actual POST request from chrome extension origin returns proper CORS headers."""
    origin = "chrome-extension://dccdppkggcalleledhmbclldddnokhok"
    headers = dict(auth_headers)
    headers["Origin"] = origin

    response = client.post(
        "/api/autofill/map-fields",
        json={
            "fields": [
                {
                    "elementId": "first-name",
                    "name": "first_name",
                    "type": "text",
                    "label": "First Name"
                }
            ]
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin_rejected(client):
    """Verify unauthorized external origin is rejected during preflight."""
    response = client.options(
        "/api/autofill/map-fields",
        headers={
            "Origin": "https://malicious-unauthorized-site.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 400
    assert "Disallowed CORS" in response.text

