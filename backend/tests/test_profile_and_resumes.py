import io
import pytest
from app.core.security import create_access_token


def test_unauthenticated_profile_and_resumes(client):
    # Unauthenticated access must be strictly forbidden (401)
    res = client.get("/api/profiles/me")
    assert res.status_code == 401

    res = client.get("/api/profile")
    assert res.status_code == 401

    res = client.get("/api/profiles/me/completion")
    assert res.status_code == 401

    res = client.post("/api/profiles", json={})
    assert res.status_code == 401

    res = client.put("/api/profiles/me", json={})
    assert res.status_code == 401

    res = client.patch("/api/profiles/me", json={})
    assert res.status_code == 401

    res = client.get("/api/resumes")
    assert res.status_code == 401

    res = client.post("/api/resumes/upload")
    assert res.status_code == 401


def test_profile_lifecycle_and_completion(client):
    fresh_token = create_access_token({"sub": "fresh_user_id_99", "email": "fresh@test.com"})
    fresh_headers = {"Authorization": f"Bearer {fresh_token}"}

    # 1. GET initial profile
    res = client.get("/api/profiles/me", headers=fresh_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["completionPercentage"] == 0
    assert "personalInformation" in data

    # 2. GET completion details
    res = client.get("/api/profiles/me/completion", headers=fresh_headers)
    assert res.status_code == 200
    comp = res.json()
    assert comp["completionPercentage"] == 0
    assert len(comp["missingRequired"]) > 0

    # 3. Create / update full profile
    full_profile = {
        "personalInformation": {
            "firstName": "Alex",
            "lastName": "Rivera",
            "fullName": "Alex Rivera",
            "email": "alex.rivera@example.com",
            "phone": "+1-555-123-4567",
            "city": "Seattle",
            "state": "WA",
            "country": "USA",
            "linkedin": "https://linkedin.com/in/alexrivera",
            "github": "https://github.com/alexrivera"
        },
        "education": [
            {
                "institution": "University of Washington",
                "college": "University of Washington",
                "degree": "B.S.",
                "specialization": "Computer Science",
                "branch": "Computer Science",
                "graduationYear": "2025",
                "cgpa": "3.85"
            }
        ],
        "skills": {
            "programmingLanguages": ["Python", "TypeScript", "SQL"],
            "frameworks": ["FastAPI", "React", "Next.js"],
            "databases": ["PostgreSQL", "MongoDB"],
            "cloud": ["AWS"],
            "devops": ["Docker"],
            "aiMl": ["LangChain", "PyTorch"],
            "tools": ["Git", "Postman", "VS Code"],
            "softSkills": ["Problem Solving", "Collaboration"]
        },
        "experiences": [
            {
                "company": "CloudScale Inc.",
                "role": "Software Engineering Intern",
                "startDate": "2024-06",
                "endDate": "2024-09",
                "technologies": ["Python", "FastAPI", "Docker"],
                "description": "Architected high-throughput async APIs."
            }
        ],
        "projects": [
            {
                "projectName": "ApplyForMe",
                "description": "AI-powered job application assistant extension",
                "technologies": ["React", "TypeScript", "FastAPI", "Ollama"],
                "githubUrl": "https://github.com/alexrivera/applyforme"
            }
        ],
        "careerPreferences": {
            "preferredRoles": ["Software Engineer", "Backend Engineer"],
            "preferredLocations": ["Seattle, WA", "Remote"],
            "employmentTypes": ["Full-time"],
            "workModes": ["Hybrid", "Remote"],
            "careerObjective": "Building resilient distributed systems."
        },
        "onboardingCompleted": True
    }

    res = client.post("/api/profiles", json=full_profile, headers=fresh_headers)
    assert res.status_code == 200
    saved = res.json()
    assert saved["personalInformation"]["fullName"] == "Alex Rivera"
    assert saved["completionPercentage"] >= 80

    # 4. PATCH partial update (e.g. adding a new skill)
    patch_data = {
        "skills": {
            "programmingLanguages": ["Python", "TypeScript", "SQL", "Rust"]
        }
    }
    res = client.patch("/api/profiles/me", json=patch_data, headers=fresh_headers)
    assert res.status_code == 200
    patched = res.json()
    assert "Rust" in patched["skills"]["programmingLanguages"]
    # Ensure personalInformation was preserved
    assert patched["personalInformation"]["email"] == "alex.rivera@example.com"

    # 5. Check completion endpoint reflects the update
    res = client.get("/api/profiles/me/completion", headers=fresh_headers)
    assert res.status_code == 200
    assert res.json()["completionPercentage"] >= 80


def test_resume_upload_and_management(client, auth_headers):
    # 1. Reject non-PDF file
    fake_txt = io.BytesIO(b"Hello world, not a pdf")
    res = client.post(
        "/api/resumes/upload",
        files={"file": ("test.txt", fake_txt, "text/plain")},
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "PDF" in res.json()["detail"]

    # 2. Reject oversized file (>5MB)
    oversized = io.BytesIO(b"A" * (6 * 1024 * 1024))
    res = client.post(
        "/api/resumes/upload",
        files={"file": ("large.pdf", oversized, "application/pdf")},
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "5MB limit" in res.json()["detail"]

    # 3. Successful PDF upload
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
    pdf_stream = io.BytesIO(valid_pdf_bytes)
    res = client.post(
        "/api/resumes/upload",
        files={"file": ("alex_rivera_resume.pdf", pdf_stream, "application/pdf")},
        data={"title": "Software Engineer Resume", "category": "Software Engineer", "isDefault": "true"},
        headers=auth_headers
    )
    assert res.status_code == 201
    resume_data = res.json()
    assert resume_data["title"] == "Software Engineer Resume"
    assert resume_data["isDefault"] is True
    assert resume_data["contentType"] == "application/pdf"
    resume_id = resume_data["_id"]

    # 4. List resumes
    res = client.get("/api/resumes", headers=auth_headers)
    assert res.status_code == 200
    resumes_list = res.json()
    assert len(resumes_list) >= 1
    assert any(r["_id"] == resume_id for r in resumes_list)

    # 5. Set default toggle
    res = client.patch(f"/api/resumes/{resume_id}/default", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["isDefault"] is True

    # 6. Delete resume
    res = client.delete(f"/api/resumes/{resume_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
