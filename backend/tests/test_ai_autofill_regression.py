"""Comprehensive Regression and AI Validation Test Suite for ApplyForMe with Groq."""

import pytest
from app.core.config import settings
from app.services.llm_factory import get_llm, reset_llm
from app.services.ai_answer_service import (
    generate_answer,
    validate_generated_answer,
    AI_GENERATED,
    NEEDS_USER_INPUT,
    DETERMINISTIC_PROFILE_MAPPING
)
from app.schemas.autofill import FormFieldDescriptor
from app.services.field_mapping_service import FieldMappingService
from app.services.seeder_service import SAMPLE_USER_EMAIL, SAMPLE_USER_NAME


@pytest.fixture(autouse=True)
def setup_groq_env(monkeypatch):
    """Enforce Groq provider for all tests in this suite."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    reset_llm()
    yield
    reset_llm()


@pytest.fixture
def verified_profile():
    return {
        "personalInformation": {
            "fullName": "Sai Konda Reddy",
            "firstName": "Sai",
            "lastName": "Konda Reddy",
            "email": "saikondareddypala@gmail.com",
            "phone": "+1-555-234-5678",
            "city": "San Francisco",
            "state": "CA",
            "country": "USA"
        },
        "education": [
            {
                "institution": "Stanford University",
                "degree": "Bachelor of Science",
                "specialization": "Computer Science",
                "graduationYear": "2025",
                "cgpa": "3.92"
            }
        ],
        "skills": {
            "technicalSkills": ["Python", "TypeScript", "FastAPI", "React", "Docker", "MongoDB", "Go"]
        },
        "experiences": [
            {
                "company": "Tech Innovations Inc.",
                "role": "Software Engineer Intern",
                "technologies": ["Python", "FastAPI", "Docker"],
                "description": "Architected asynchronous microservices improving throughput by 40%."
            }
        ],
        "projects": [
            {
                "projectName": "ApplyForMe",
                "technologies": ["React", "TypeScript", "FastAPI", "MongoDB", "Groq"],
                "description": "AI-powered job application assistant extension with intelligent grounded field synthesis."
            }
        ],
        "careerPreferences": {
            "availability": "Immediate",
            "employmentTypes": ["Full-time", "Internship"],
            "workAuthorization": "Authorized to work in US",
            "sponsorshipRequired": False,
            "willingToRelocate": True
        }
    }


# ==============================================================================
# 1. Recruitment Internship vs Software Engineering Internship Distinction
# ==============================================================================
@pytest.mark.asyncio
async def test_recruitment_vs_software_internship_distinction(verified_profile):
    """Verify that a candidate with software engineering experience is NOT claimed to have recruitment experience."""
    res = await generate_answer(
        question_id="rec_exp_check",
        question_text="Do you have any prior recruitment internship experience?",
        field_type="text",
        applicant_profile=verified_profile,
        company_name="Paytm"
    )
    assert res.status == "generated"
    ans_lower = res.answer.lower()
    assert "no" in ans_lower
    assert "software" in ans_lower
    assert "recruitment internship experience" not in ans_lower or "do not have" in ans_lower or "no prior" in ans_lower


# ==============================================================================
# 2. Unknown Availability Handling
# ==============================================================================
@pytest.mark.asyncio
async def test_unknown_availability_requires_confirmation(verified_profile):
    """Verify when availability is missing, system marks NEEDS_USER_INPUT and does not fabricate a date."""
    profile_no_avail = dict(verified_profile)
    profile_no_avail["careerPreferences"] = {}  # Empty preferences

    res = await generate_answer(
        question_id="avail_unknown",
        question_text="Will you be available for a 6-month internship starting next week?",
        field_type="text",
        applicant_profile=profile_no_avail,
        company_name="Paytm"
    )
    assert res.status == "needs_user_input"
    assert res.execution_status == NEEDS_USER_INPUT
    assert res.answer is None


# ==============================================================================
# 3. Unknown Salary Expectations Handling
# ==============================================================================
def test_unknown_salary_expectations(verified_profile):
    """Verify salary fields propose standard negotiable terms with confirmation required."""
    field = FormFieldDescriptor(
        elementId="salary-exp",
        name="expectedSalary",
        type="text",
        label="What are your expected salary / compensation requirements?"
    )
    res = FieldMappingService.map_entire_form([field], verified_profile)
    m = res.mappings[0]
    assert m.category in ("USER_INPUT_REQUIRED", "USER_CONFIRMATION_REQUIRED")
    assert m.requires_confirmation is True
    assert "negotiable" in str(m.proposed_answer).lower()


# ==============================================================================
# 4. Work Authorization Safeguards
# ==============================================================================
@pytest.mark.asyncio
async def test_work_authorization_unverified_requires_confirmation(verified_profile):
    """Verify that if work authorization is absent, it is not assumed."""
    profile_no_auth = dict(verified_profile)
    profile_no_auth["careerPreferences"] = {}

    res = await generate_answer(
        question_id="auth_check",
        question_text="Are you legally authorized to work in the country?",
        field_type="select",
        applicant_profile=profile_no_auth
    )
    assert res.status == "needs_user_input"


# ==============================================================================
# 5. Motivation Questions Grounded in Profile & Company
# ==============================================================================
@pytest.mark.asyncio
async def test_motivation_question_grounded(verified_profile):
    """Verify company motivation questions reference company and applicant engineering competencies."""
    res = await generate_answer(
        question_id="why_paytm",
        question_text="Why do you want to work at Paytm and join the payment gateways engineering team?",
        field_type="textarea",
        applicant_profile=verified_profile,
        company_name="Paytm",
        job_title="Backend Engineer"
    )
    assert res.status == "generated"
    assert res.execution_status == AI_GENERATED
    ans = res.answer
    assert "Paytm" in ans or "payment" in ans.lower()
    assert len(ans) > 40


# ==============================================================================
# 6. Project Descriptions Grounded in Verified Profile
# ==============================================================================
@pytest.mark.asyncio
async def test_project_description_grounded(verified_profile):
    """Verify technical project questions reference applicant's real projects (ApplyForMe)."""
    res = await generate_answer(
        question_id="proj_desc",
        question_text="Describe a challenging technical project you built and the technologies used.",
        field_type="textarea",
        applicant_profile=verified_profile,
        company_name="Paytm",
        job_title="Backend Engineer"
    )
    assert res.status == "generated"
    assert res.execution_status == AI_GENERATED
    ans = res.answer
    assert "ApplyForMe" in ans or "FastAPI" in ans or "Python" in ans


# ==============================================================================
# 7. Company Attribution
# ==============================================================================
@pytest.mark.asyncio
async def test_company_attribution(verified_profile):
    """Verify company name is appropriately addressed without cross-contamination."""
    res_stripe = await generate_answer(
        question_id="why_stripe",
        question_text="Why do you want to join Stripe?",
        field_type="textarea",
        applicant_profile=verified_profile,
        company_name="Stripe"
    )
    assert "Stripe" in res_stripe.answer
    assert "Paytm" not in res_stripe.answer


# ==============================================================================
# 8. Different Questions Receive Different Answers
# ==============================================================================
@pytest.mark.asyncio
async def test_different_questions_receive_different_answers(verified_profile):
    """Verify that multiple open-ended questions receive distinct tailored answers."""
    questions = [
        ("q_why", "Why do you want to join our engineering organization?", "textarea"),
        ("q_proj", "Describe a complex backend system you designed.", "textarea"),
        ("q_strength", "What are your greatest technical strengths?", "textarea"),
        ("q_python", "Explain your practical experience with Python and FastAPI.", "textarea")
    ]

    answers = []
    for qid, qtext, qtype in questions:
        out = await generate_answer(
            question_id=qid,
            question_text=qtext,
            field_type=qtype,
            applicant_profile=verified_profile,
            company_name="Paytm",
            job_title="Software Development Engineer"
        )
        assert out.status == "generated"
        answers.append(out.answer.strip())

    # Ensure all 4 answers are mutually distinct
    assert len(set(answers)) == 4


# ==============================================================================
# 9. Proposed Answer for Every Field (Section 5 Requirement)
# ==============================================================================
def test_proposed_answer_for_every_field(verified_profile):
    """Verify that every field receives either a direct value or a proposed answer with confirmation reason."""
    fields = [
        FormFieldDescriptor(elementId="fname", name="firstName", label="First Name"),
        FormFieldDescriptor(elementId="sec-clear", name="securityClearance", label="Do you hold an active Top Secret Security Clearance?"),
        FormFieldDescriptor(elementId="sal", name="salary", label="Expected Salary Range"),
        FormFieldDescriptor(elementId="dlicense", name="driverLicense", label="Do you have a valid driver's license?"),
        FormFieldDescriptor(elementId="unrec", name="customQuestion", label="Any other certifications?")
    ]

    res = FieldMappingService.map_entire_form(fields, verified_profile)
    assert res.totalFields == 5
    for m in res.mappings:
        assert m.field_id is not None
        assert m.question is not None
        # Every field must have a fillValue or proposed_answer
        has_proposal = m.fillValue is not None or m.proposed_answer is not None
        assert has_proposal, f"Field '{m.fieldName}' lacks a proposed answer."


# ==============================================================================
# 10. AI Validation Rejects Hallucinations
# ==============================================================================
def test_validate_generated_answer_rejects_hallucinations(verified_profile):
    """Verify that validator rejects robotic disclaimers and fabricated credentials."""
    # Robotic disclaimer
    valid, reason = validate_generated_answer("As an AI model, I cannot answer this.", "Why join?", "COMPANY_MOTIVATION", verified_profile)
    assert not valid
    assert "disclaimer" in reason.lower()

    # Fabricated recruitment claim
    valid_rec, reason_rec = validate_generated_answer(
        "I have recruitment internship experience hiring 50 candidates.",
        "Do you have recruitment internship experience?",
        "PRIOR_EXPERIENCE",
        verified_profile
    )
    assert not valid_rec
    assert "recruitment" in reason_rec.lower()


# ==============================================================================
# 11. End-to-End API /api/autofill/map-fields with Groq
# ==============================================================================
def test_autofill_map_fields_e2e_with_groq(client):
    """Verify the FastAPI endpoint POST /api/autofill/map-fields runs with Groq in production shape."""
    login_resp = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "companyName": "Paytm",
        "jobTitle": "Backend Engineer",
        "jobDescription": "Scale payment gateways and microservices.",
        "url": "https://jobs.lever.co/paytm/backend-engineer",
        "fields": [
            {"elementId": "f-name", "name": "firstName", "type": "text", "label": "First Name *"},
            {"elementId": "why-join", "name": "whyJoin", "type": "textarea", "label": "Why do you want to work at Paytm? *"},
            {"elementId": "proj", "name": "project", "type": "textarea", "label": "Describe a challenging technical project you built *"},
            {"elementId": "clearance", "name": "securityClearance", "type": "text", "label": "Do you hold a security clearance?"}
        ]
    }

    resp = client.post("/api/autofill/map-fields", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["totalFields"] == 4
    by_id = {m["elementIdentifier"]: m for m in data["mappings"]}

    assert by_id["f-name"]["fillValue"] == "Sai"
    assert by_id["why-join"]["category"] == "AI_GENERATED_ANSWER"
    assert by_id["why-join"]["fillValue"] is not None
    assert by_id["proj"]["category"] == "AI_GENERATED_ANSWER"
    assert by_id["proj"]["fillValue"] is not None
    assert by_id["why-join"]["fillValue"] != by_id["proj"]["fillValue"]
    assert by_id["clearance"]["requires_confirmation"] is True
    assert by_id["clearance"]["proposed_answer"] is not None

