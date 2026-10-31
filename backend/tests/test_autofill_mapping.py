import pytest
from app.schemas.autofill import FormFieldDescriptor
from app.services.field_mapping_service import FieldMappingService


@pytest.fixture
def sample_profile():
    return {
        "personalInformation": {
            "firstName": "Alex",
            "lastName": "Rivera",
            "fullName": "Alex Rivera",
            "email": "alex.rivera@example.com",
            "phone": "+1-555-123-4567",
            "city": "Seattle",
            "state": "WA",
            "country": "USA",
            "address": "400 Broad St",
            "dateOfBirth": "2000-05-15",
            "gender": "Male",
            "linkedin": "https://linkedin.com/in/alexrivera",
            "github": "https://github.com/alexrivera",
            "portfolio": "https://alexrivera.dev"
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
            "programmingLanguages": ["Python", "TypeScript"],
            "frameworks": ["React", "FastAPI"],
            "databases": ["PostgreSQL", "MongoDB"],
            "cloud": ["AWS"],
            "tools": ["Git", "Docker"]
        },
        "careerPreferences": {
            "careerObjective": "Building scalable software.",
            "professionalSummary": "Full stack engineer passionate about AI.",
            "availability": "Immediate",
            "workAuthorization": "Authorized to work in US",
            "willingToRelocate": True
        }
    }


def test_deterministic_field_mappings(sample_profile):
    fields = [
        FormFieldDescriptor(elementId="fname", name="first_name", label="First Name", placeholder="First name"),
        FormFieldDescriptor(elementId="lname", name="last_name", label="Last Name", placeholder="Last name"),
        FormFieldDescriptor(elementId="applicant_name", name="full_name", label="Full Name"),
        FormFieldDescriptor(elementId="user_email", name="email", type="email", label="Email Address"),
        FormFieldDescriptor(elementId="user_phone", name="phone_num", type="tel", label="Phone Number"),
        FormFieldDescriptor(elementId="school", name="university", label="College / University"),
        FormFieldDescriptor(elementId="deg", name="degree_select", type="select", label="Degree Obtained"),
        FormFieldDescriptor(elementId="major", name="branch", label="Major / Specialization"),
        FormFieldDescriptor(elementId="grad_yr", name="graduation_year", label="Year of Graduation"),
        FormFieldDescriptor(elementId="gpa_input", name="cgpa", label="Cumulative GPA / Marks"),
        FormFieldDescriptor(elementId="skills_area", name="technical_skills", type="textarea", label="Key Technical Skills"),
        FormFieldDescriptor(elementId="li_url", name="linkedin_profile", label="LinkedIn URL"),
        FormFieldDescriptor(elementId="gh_url", name="github_profile", label="GitHub URL"),
        FormFieldDescriptor(elementId="city_input", name="city", label="City of Residence"),
        FormFieldDescriptor(elementId="resume_file", name="resume", type="file", label="Upload Resume (PDF)")
    ]

    res = FieldMappingService.map_entire_form(fields, sample_profile)
    assert res.totalFields == 15
    assert res.matchedFields >= 13

    mapping_by_id = {m.elementIdentifier: m for m in res.mappings}

    # Verify First Name
    assert mapping_by_id["fname"].fillValue == "Alex"
    assert mapping_by_id["fname"].confidence >= 0.95

    # Verify Last Name
    assert mapping_by_id["lname"].fillValue == "Rivera"

    # Verify Full Name
    assert mapping_by_id["applicant_name"].fillValue == "Alex Rivera"

    # Verify Email
    assert mapping_by_id["user_email"].fillValue == "alex.rivera@example.com"

    # Verify Phone
    assert mapping_by_id["user_phone"].fillValue == "+1-555-123-4567"

    # Verify University
    assert mapping_by_id["school"].fillValue == "University of Washington"

    # Verify Degree
    assert mapping_by_id["deg"].fillValue == "B.S."

    # Verify Skills (joined)
    skills_val = mapping_by_id["skills_area"].fillValue
    assert "Python" in skills_val
    assert "React" in skills_val

    # Verify LinkedIn & GitHub
    assert mapping_by_id["li_url"].fillValue == "https://linkedin.com/in/alexrivera"
    assert mapping_by_id["gh_url"].fillValue == "https://github.com/alexrivera"

    # Verify File Input was safely skipped from direct fillValue
    assert mapping_by_id["resume_file"].fillValue is None
    assert mapping_by_id["resume_file"].requiresReview is True

