import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.core.config import settings
settings.APP_ENV = "test"

from app.core.database import InMemoryAsyncDatabase
from app.services.auth_service import AuthService
from app.services.profile_service import ProfileService
from app.services.field_mapping_service import FieldMappingService
from app.services.ai_service import AIService
from app.schemas.autofill import FormFieldDescriptor
from app.schemas.ai import AnswerGenerationRequest


async def run_direct_tests():
    print("--- 1. Testing In-Memory DB & Auth Service ---", flush=True)
    db = InMemoryAsyncDatabase("applyforme_test")
    print(">>> Created test DB", flush=True)
    login_result = await AuthService.dev_login("alex.test@stanford.edu", "Alex Test", db)
    print(">>> Finished dev_login", flush=True)
    assert "access_token" in login_result
    user = login_result["user"]
    user_id = user["_id"]
    print(f"Dev Login Successful: {user['name']} ({user['email']}), ID: {user_id}", flush=True)

    print("\n--- 2. Testing Profile Service CRUD & Completion ---", flush=True)
    # Initial empty profile
    initial_prof = await ProfileService.get_user_profile(user_id, db)
    print(f"Initial Profile Completion: {initial_prof['completionPercentage']}%", flush=True)

    # Update profile with comprehensive data
    profile_update = {
        "personalInformation": {
            "fullName": "Alex Test",
            "firstName": "Alex",
            "lastName": "Test",
            "email": "alex.test@stanford.edu",
            "phone": "+1-555-0142",
            "city": "Palo Alto",
            "country": "USA"
        },
        "education": [
            {
                "college": "Stanford University",
                "degree": "B.S.",
                "branch": "Computer Science",
                "graduationYear": "2025",
                "cgpa": "3.92"
            }
        ],
        "skills": {
            "technicalSkills": ["Data Structures", "Algorithms", "Distributed Systems"],
            "programmingLanguages": ["Python", "TypeScript", "C++"],
            "frameworks": ["FastAPI", "React", "Node.js"],
            "cloudPlatforms": ["AWS", "Azure"],
            "tools": ["Git", "Docker"]
        },
        "experiences": [
            {
                "company": "Tech Corp",
                "role": "Software Engineering Intern",
                "duration": "Jun 2024 - Aug 2024",
                "description": "Developed backend APIs with FastAPI and deployed to cloud."
            }
        ],
        "projects": [
            {
                "projectName": "ApplyForMe",
                "description": "Smart Chrome Extension for autofilling job applications",
                "technologies": ["React", "FastAPI", "MongoDB"]
            }
        ],
        "professionalLinks": {
            "linkedin": "https://linkedin.com/in/alextest",
            "github": "https://github.com/alextest",
            "portfolio": "https://alextest.dev"
        },
        "careerPreferences": {
            "preferredRoles": ["Software Engineer", "Full Stack Developer"],
            "preferredIndustries": ["Technology", "Fintech"],
            "careerObjectives": "Build reliable scalable software",
            "professionalSummary": "CS senior specializing in full-stack development and distributed systems."
        }
    }
    saved_prof = await ProfileService.update_user_profile(user_id, profile_update, db)
    print(f"Updated Profile Completion: {saved_prof['completionPercentage']}% (Expected >= 80%)", flush=True)
    assert saved_prof["completionPercentage"] >= 80

    # Retrieve profile
    fetched = await ProfileService.get_user_profile(user_id, db)
    assert fetched["personalInformation"]["email"] == "alex.test@stanford.edu"
    assert len(fetched["skills"]["programmingLanguages"]) == 3
    print("Profile CRUD verified successfully.", flush=True)

    print("\n--- 3. Testing Field Mapping Engine ---", flush=True)
    sample_fields = [
        FormFieldDescriptor(name="first_name", label="First Name", placeholder="Enter given name"),
        FormFieldDescriptor(name="email_address", label="Email", type="email"),
        FormFieldDescriptor(name="phone_number", label="Phone Number", type="tel"),
        FormFieldDescriptor(name="university", label="College / University"),
        FormFieldDescriptor(name="graduation_year", label="Graduation Year"),
        FormFieldDescriptor(name="linkedin_url", label="LinkedIn Profile"),
        FormFieldDescriptor(name="github_url", label="GitHub Profile"),
    ]
    mapping_res = FieldMappingService.map_entire_form(sample_fields, fetched)
    print(f"Total Fields: {mapping_res.totalFields}, Matched: {mapping_res.matchedFields}", flush=True)
    for m in mapping_res.mappings:
        print(f"  Field [{m.elementIdentifier}] -> Path [{m.profileKey}] = '{m.fillValue}' (Confidence: {m.confidence})", flush=True)
    assert mapping_res.matchedFields >= 6
    print("Field Mapping verified successfully.", flush=True)

    print("\n--- 4. Testing AI Answer Generation Service ---", flush=True)
    ai_req = AnswerGenerationRequest(
        question="Why do you want to join our company?",
        companyName="Stripe",
        jobTitle="Backend Software Engineer",
        jobDescription="We are looking for an engineer proficient in Python and distributed systems."
    )
    ai_ans = await AIService.generate_answer(ai_req, fetched, user_id, db)
    print(f"Generated Answer for: '{ai_ans.question}':", flush=True)
    print(f"Answer: {ai_ans.answer}", flush=True)
    print(f"Confidence: {ai_ans.confidence}", flush=True)
    print(f"Key Points Used: {ai_ans.keyPointsUsed}", flush=True)
    assert len(ai_ans.answer) > 20
    assert "Stripe" in ai_ans.answer
    print("AI Answer Generation verified successfully.", flush=True)

    print("\n=======================================================", flush=True)
    print("ALL PHASE 1 BACKEND SERVICES & LOGIC PASSED WITH 100% SUCCESS!", flush=True)
    print("=======================================================", flush=True)


if __name__ == "__main__":
    asyncio.run(run_direct_tests())
