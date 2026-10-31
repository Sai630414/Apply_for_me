import pytest
from app.services.seeder_service import SAMPLE_USER_EMAIL, SAMPLE_USER_NAME


def test_full_paytm_application_form_autofill(client):
    """
    End-to-end simulation of Paytm Lever job application form autofill
    testing all 33 fields across all 6 classification categories.
    """
    # 1. Sign in as sample account
    login_resp = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Simulate the 33 fields detected from test_application_form.html
    fields_payload = [
        # Personal Information (DIRECT_PROFILE_FIELD)
        {"elementId": "first-name", "name": "firstName", "type": "text", "label": "First Name *"},
        {"elementId": "last-name", "name": "lastName", "type": "text", "label": "Last Name *"},
        {"elementId": "full-name", "name": "fullName", "type": "text", "label": "Full Name *"},
        {"elementId": "email-address", "name": "email", "type": "email", "label": "Email Address *"},
        {"elementId": "phone-number", "name": "phone", "type": "tel", "label": "Phone Number *"},
        {"elementId": "date-of-birth", "name": "dateOfBirth", "type": "date", "label": "Date of Birth"},
        {"elementId": "gender-select", "name": "gender", "type": "select", "label": "Gender", "options": ["Select Gender", "Male", "Female", "Non-binary", "Prefer not to say"]},
        {"elementId": "current-city", "name": "city", "type": "text", "label": "Current City *"},
        {"elementId": "current-state", "name": "state", "type": "text", "label": "State / Province"},
        {"elementId": "current-country", "name": "country", "type": "select", "label": "Country *", "options": ["Select Country", "United States", "India", "Canada", "United Kingdom"]},
        {"elementId": "street-address", "name": "address", "type": "text", "label": "Street Address"},

        # Professional Presence (DIRECT_PROFILE_FIELD)
        {"elementId": "linkedin-url", "name": "linkedin", "type": "url", "label": "LinkedIn Profile URL *"},
        {"elementId": "github-url", "name": "github", "type": "url", "label": "GitHub Profile URL *"},
        {"elementId": "portfolio-url", "name": "portfolio", "type": "url", "label": "Personal Portfolio / Website"},

        # Education (DIRECT_PROFILE_FIELD + SELECT)
        {"elementId": "institution-name", "name": "university", "type": "text", "label": "College / University Name *"},
        {"elementId": "degree-select", "name": "degree", "type": "select", "label": "Degree Level *", "options": ["Select Degree", "Bachelor of Science (B.S.)", "Bachelor of Technology (B.Tech)", "Master of Science (M.S.)", "Doctor of Philosophy (Ph.D.)"]},
        {"elementId": "specialization-name", "name": "specialization", "type": "text", "label": "Major / Specialization *"},
        {"elementId": "graduation-year", "name": "graduationYear", "type": "select", "label": "Graduation Year (Select) *", "options": ["Select Year", "2023", "2024", "2025", "2026"]},
        {"elementId": "cgpa-score", "name": "cgpa", "type": "text", "label": "Cumulative GPA / CGPA"},

        # Experience & Skills (DIRECT_PROFILE_FIELD)
        {"elementId": "current-company", "name": "currentCompany", "type": "text", "label": "Current Company / Employer"},
        {"elementId": "current-role", "name": "currentRole", "type": "text", "label": "Current Title / Role"},
        {"elementId": "employment-type", "name": "employmentType", "type": "select", "label": "Employment Type", "options": ["Select Type", "Full-time", "Internship", "Part-time"]},
        {"elementId": "notice-period-select", "name": "noticePeriod", "type": "select", "label": "Notice Period", "options": ["Select Notice Period", "Immediate", "15 Days", "30 Days", "60 Days"]},
        {"elementId": "technical-skills", "name": "skills", "type": "textarea", "label": "Key Technical Skills & Technologies *"},

        # AI Questions (AI_GENERATED_ANSWER)
        {"elementId": "why-paytm", "name": "whyJoin", "type": "textarea", "label": "Why do you want to work at Paytm and join this team? *"},
        {"elementId": "challenging-project", "name": "challengingProject", "type": "textarea", "label": "Describe a challenging technical project you built and the technologies used *"},
        {"elementId": "candidate-strengths", "name": "strengths", "type": "textarea", "label": "What are your core strengths and what makes you a suitable candidate for this role? *"},
        {"elementId": "tech-experience", "name": "techExperience", "type": "textarea", "label": "Explain your practical experience with Python, FastAPI, or distributed systems"},

        # Preferences & Authorization (DIRECT_PROFILE_FIELD / RADIOS / SELECTS)
        {"elementId": "work-authorization-select", "name": "workAuthorization", "type": "select", "label": "Are you legally authorized to work in the United States? *", "options": ["Select an option", "Yes", "No"]},
        {"elementId": "sponsorship-select", "name": "sponsorshipRequired", "type": "select", "label": "Will you now or in the future require visa sponsorship? *", "options": ["Select an option", "Yes", "No"]},
        {"elementId": "relocate-yes", "name": "willingToRelocate", "type": "radio", "label": "Are you willing to relocate for this position?"},

        # Missing Factual Question (USER_INPUT_REQUIRED)
        {"elementId": "security-clearance", "name": "securityClearance", "type": "text", "label": "Do you hold an active Top Secret Security Clearance?"},

        # Resume Upload (FILE_UPLOAD)
        {"elementId": "resume-upload", "name": "resumeFile", "type": "file", "label": "Upload Resume / CV (PDF, DOCX) *"},

        # Legal Declarations (CONSENT_OR_LEGAL)
        {"elementId": "consent-privacy", "name": "privacyPolicyAgree", "type": "checkbox", "label": "I agree to the Paytm Privacy Policy and consent to the processing of my candidate data."},
        {"elementId": "certify-accuracy", "name": "accuracyCertified", "type": "checkbox", "label": "I certify that all statements made in this job application are true, complete, and accurate."}
    ]

    req_body = {
        "companyName": "Paytm",
        "jobTitle": "Software Development Engineer (Backend)",
        "jobDescription": "Build and scale high-performance payment gateways and distributed backend microservices.",
        "url": "https://jobs.lever.co/paytm/backend-engineer",
        "fields": fields_payload
    }

    resp = client.post("/api/autofill/map-fields", json=req_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["totalFields"] == len(fields_payload)
    assert data["matchedFields"] >= 20
    assert data["directMappedCount"] >= 15
    assert data["aiGeneratedCount"] >= 4
    assert data["fileUploadCount"] == 1
    assert data["consentLegalCount"] == 2
    assert data["userInputRequiredCount"] >= 1

    by_id = {m["elementIdentifier"]: m for m in data["mappings"]}

    # 1. DIRECT_PROFILE_FIELD checks
    assert by_id["first-name"]["fillValue"] == "Sai"
    assert by_id["last-name"]["fillValue"] == "Konda Reddy"
    assert by_id["email-address"]["fillValue"] == "saikondareddypala@gmail.com"
    assert by_id["institution-name"]["fillValue"] == "Stanford University"
    assert by_id["degree-select"]["fillValue"] == "Bachelor of Science (B.S.)"
    assert by_id["graduation-year"]["fillValue"] == "2025"
    assert by_id["current-country"]["fillValue"] == "United States"
    assert by_id["work-authorization-select"]["fillValue"] == "Yes"
    assert by_id["sponsorship-select"]["fillValue"] == "No"
    assert by_id["relocate-yes"]["fillValue"] == "Yes"

    # 2. AI_GENERATED_ANSWER checks
    assert by_id["why-paytm"]["category"] == "AI_GENERATED_ANSWER"
    assert by_id["why-paytm"]["fillValue"] is not None
    assert len(by_id["why-paytm"]["fillValue"]) > 30

    assert by_id["challenging-project"]["category"] == "AI_GENERATED_ANSWER"
    assert by_id["challenging-project"]["fillValue"] is not None
    assert ("ApplyForMe" in by_id["challenging-project"]["fillValue"] or "FastAPI" in by_id["challenging-project"]["fillValue"])

    assert by_id["candidate-strengths"]["category"] == "AI_GENERATED_ANSWER"
    assert by_id["candidate-strengths"]["fillValue"] is not None

    # 3. USER_INPUT_REQUIRED check
    assert by_id["security-clearance"]["category"] == "USER_INPUT_REQUIRED"
    assert by_id["security-clearance"]["fillValue"] is None
    assert by_id["security-clearance"]["requiresReview"] is True

    # 4. FILE_UPLOAD check
    assert by_id["resume-upload"]["category"] == "FILE_UPLOAD"
    assert by_id["resume-upload"]["fillValue"] is None
    assert by_id["resume-upload"]["requiresReview"] is True

    # 5. CONSENT_OR_LEGAL checks (NEVER automatically checked)
    assert by_id["consent-privacy"]["category"] == "CONSENT_OR_LEGAL"
    assert by_id["consent-privacy"]["fillValue"] is None
    assert by_id["consent-privacy"]["requiresReview"] is True

    assert by_id["certify-accuracy"]["category"] == "CONSENT_OR_LEGAL"
    assert by_id["certify-accuracy"]["fillValue"] is None
    assert by_id["certify-accuracy"]["requiresReview"] is True

