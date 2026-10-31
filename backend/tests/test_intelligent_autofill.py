import pytest
from app.schemas.autofill import FormFieldDescriptor, FormFieldMapping
from app.services.field_mapping_service import FieldMappingService, match_select_option
from app.services.ai_answer_service import generate_application_answer, _generate_fallback_answer


@pytest.fixture
def test_applicant_profile():
    return {
        "personalInformation": {
            "firstName": "Sai",
            "lastName": "Konda Reddy",
            "fullName": "Sai Konda Reddy",
            "email": "saikondareddypala@gmail.com",
            "phone": "+1-555-234-5678",
            "city": "San Francisco",
            "state": "CA",
            "country": "USA",
            "address": "500 Howard Street",
            "dateOfBirth": "2000-08-20",
            "gender": "Male",
            "linkedin": "https://linkedin.com/in/saikondareddy",
            "github": "https://github.com/saikondareddy",
            "portfolio": "https://saikonda.dev"
        },
        "education": [
            {
                "institution": "Stanford University",
                "degree": "B.S.",
                "specialization": "Computer Science",
                "graduationYear": "2025",
                "cgpa": "3.92"
            }
        ],
        "skills": {
            "programmingLanguages": ["Python", "TypeScript", "Go"],
            "frameworks": ["FastAPI", "React", "Node.js"],
            "databases": ["MongoDB", "PostgreSQL"],
            "technicalSkills": ["FastAPI", "React", "Docker", "Python"]
        },
        "experiences": [
            {
                "company": "Tech Innovations Inc.",
                "role": "Software Engineer Intern",
                "currentlyWorking": False,
                "startDate": "2024-05",
                "endDate": "2024-08",
                "description": "Architected asynchronous REST endpoints improving throughput by 40%."
            }
        ],
        "projects": [
            {
                "projectName": "ApplyForMe",
                "description": "AI-powered job application assistant with local LLM integration and deterministic autofill.",
                "technologies": ["FastAPI", "React", "TypeScript", "Ollama"]
            }
        ],
        "careerPreferences": {
            "willingToRelocate": True,
            "workAuthorization": "Authorized to work in US",
            "sponsorshipRequired": False,
            "availability": "Immediate",
            "expectedSalary": "$120,000",
            "professionalSummary": "Results-driven computer science graduate with proven experience building full-stack web applications and microservices."
        }
    }


def test_field_classification_all_categories(test_applicant_profile):
    """Verify that fields are classified into the 6 required categories."""
    fields = [
        # 1. DIRECT_PROFILE_FIELD
        FormFieldDescriptor(elementId="email", name="email", type="email", label="Email"),
        FormFieldDescriptor(elementId="fname", name="first_name", type="text", label="First Name"),
        FormFieldDescriptor(elementId="city", name="city", type="text", label="Current City"),
        FormFieldDescriptor(elementId="skills", name="skills", type="textarea", label="Technical Skills"),
        # 2. AI_GENERATED_ANSWER
        FormFieldDescriptor(elementId="why_us", name="why_join", type="textarea", label="Why do you want to work at Paytm?"),
        FormFieldDescriptor(elementId="proj_desc", name="project_experience", type="textarea", label="Describe a challenging project you built"),
        # 3. USER_INPUT_REQUIRED
        FormFieldDescriptor(elementId="sec_clearance", name="security_clearance", type="text", label="Do you hold active Top Secret Security Clearance?"),
        # 4. FILE_UPLOAD
        FormFieldDescriptor(elementId="resume", name="resume", type="file", label="Upload Resume"),
        # 5. CONSENT_OR_LEGAL
        FormFieldDescriptor(elementId="terms", name="agree_terms", type="checkbox", label="I agree to the Terms of Service and Privacy Policy"),
        FormFieldDescriptor(elementId="certify", name="certify_accuracy", type="checkbox", label="I certify that all information submitted is true and accurate")
    ]

    res = FieldMappingService.map_entire_form(fields, test_applicant_profile)
    by_id = {m.elementIdentifier: m for m in res.mappings}

    # Verify DIRECT_PROFILE_FIELD
    assert by_id["email"].category == "DIRECT_PROFILE_FIELD"
    assert by_id["email"].fillValue == "saikondareddypala@gmail.com"
    assert by_id["fname"].category == "DIRECT_PROFILE_FIELD"
    assert by_id["fname"].fillValue == "Sai"
    assert by_id["skills"].category == "DIRECT_PROFILE_FIELD"
    assert "Python" in str(by_id["skills"].fillValue)

    # Verify AI_GENERATED_ANSWER
    assert by_id["why_us"].category == "AI_GENERATED_ANSWER"
    assert by_id["why_us"].fillValue is not None
    assert len(str(by_id["why_us"].fillValue)) > 20
    assert by_id["proj_desc"].category == "AI_GENERATED_ANSWER"
    assert "ApplyForMe" in str(by_id["proj_desc"].fillValue) or "FastAPI" in str(by_id["proj_desc"].fillValue)

    # Verify USER_INPUT_REQUIRED
    assert by_id["sec_clearance"].category == "USER_INPUT_REQUIRED"
    assert by_id["sec_clearance"].fillValue is None
    assert by_id["sec_clearance"].requiresReview is True

    # Verify FILE_UPLOAD
    assert by_id["resume"].category == "FILE_UPLOAD"
    assert by_id["resume"].fillValue is None
    assert by_id["resume"].requiresReview is True

    # Verify CONSENT_OR_LEGAL (must NEVER be automatically accepted)
    assert by_id["terms"].category == "CONSENT_OR_LEGAL"
    assert by_id["terms"].fillValue is None
    assert by_id["terms"].requiresReview is True

    assert by_id["certify"].category == "CONSENT_OR_LEGAL"
    assert by_id["certify"].fillValue is None
    assert by_id["certify"].requiresReview is True


def test_select_dropdown_matching():
    """Verify intelligent matching against select options."""
    # Graduation year
    options_years = ["2022", "2023", "2024", "2025", "2026"]
    assert match_select_option("2025", options_years) == "2025"

    # Degree option matching
    options_degree = ["Bachelor of Science (B.S.)", "Master of Science (M.S.)", "Ph.D."]
    assert match_select_option("B.S.", options_degree) == "Bachelor of Science (B.S.)"

    # Boolean work authorization
    options_auth = ["Yes", "No"]
    assert match_select_option("Authorized to work in US", options_auth) == "Yes"
    assert match_select_option(True, options_auth) == "Yes"
    assert match_select_option(False, options_auth) == "No"

    # Country matching
    options_country = ["United States", "Canada", "United Kingdom", "India"]
    assert match_select_option("USA", options_country) == "United States"

    # No match
    assert match_select_option("Astronautical Engineering", options_degree) is None


@pytest.mark.asyncio
async def test_ai_answer_generation_grounded(test_applicant_profile):
    """Verify generated answers use real projects/skills and do not hallucinate."""
    res = await generate_application_answer(
        applicant_profile=test_applicant_profile,
        company_name="Paytm",
        job_title="Software Development Engineer",
        job_description="Building scalable backend microservices",
        question="Why are you interested in this position at Paytm?",
        answer_length="concise"
    )

    assert res.status == "generated"
    assert res.answer is not None
    assert len(res.answer) > 20
    assert res.confidence >= 0.80
    assert "Paytm" in res.answer or "Software" in res.answer


@pytest.mark.asyncio
async def test_ai_answer_missing_factual_info_needs_user_input(test_applicant_profile):
    """Verify factual questions missing from profile return needs_user_input."""
    res = await generate_application_answer(
        applicant_profile=test_applicant_profile,
        company_name="Paytm",
        job_title="Software Engineer",
        job_description="",
        question="What is your active security clearance level?",
        answer_length="standard"
    )

    assert res.status == "needs_user_input"
    assert res.answer is None
    assert len(res.missing_information) > 0

