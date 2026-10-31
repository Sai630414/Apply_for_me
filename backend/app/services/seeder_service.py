import logging
from datetime import datetime, timezone
from typing import Optional, Any
from app.services.profile_service import ProfileService
from app.schemas.profile import calculate_profile_completion

logger = logging.getLogger("applyforme.seeder")

SAMPLE_USER_EMAIL = "saikondareddypala@gmail.com"
SAMPLE_USER_NAME = "Sai Konda Reddy"


async def seed_sample_development_account(db: Optional[Any]) -> None:
    """
    Seed fixed development sample account on local startup.
    Creates user and complete applicant profile if they do not already exist.
    Preserves existing user data without overwriting.
    """
    if db is None:
        logger.info("[Seeder] Database connection offline; skipping seeding.")
        return

    now = datetime.now(timezone.utc)

    # 1. Check if sample user exists in db.users
    user = await db.users.find_one({"email": SAMPLE_USER_EMAIL})
    if not user:
        new_user = {
            "googleId": "dev_google_saikondareddypala",
            "email": SAMPLE_USER_EMAIL,
            "name": SAMPLE_USER_NAME,
            "picture": "https://api.dicebear.com/7.x/initials/svg?seed=Sai%20Konda%20Reddy",
            "createdAt": now,
            "updatedAt": now,
            "lastLoginAt": now
        }
        res = await db.users.insert_one(new_user)
        user_id = str(res.inserted_id)
        logger.info(f"[Seeder] Created development sample user: {SAMPLE_USER_EMAIL} ({user_id})")
    else:
        user_id = str(user["_id"])
        logger.info(f"[Seeder] Sample user already exists: {SAMPLE_USER_EMAIL} ({user_id})")

    # 2. Check if profile exists in db.profiles (do not overwrite existing profile)
    existing_profile = await db.profiles.find_one({"userId": user_id})
    if not existing_profile:
        sample_profile_doc = {
            "userId": user_id,
            "personalInformation": {
                "firstName": "Sai",
                "lastName": "Konda Reddy",
                "fullName": "Sai Konda Reddy",
                "email": SAMPLE_USER_EMAIL,
                "phone": "+1-555-234-5678",
                "city": "San Francisco",
                "state": "CA",
                "country": "USA",
                "address": "500 Howard Street, Suite 400",
                "dateOfBirth": "2000-08-20",
                "gender": "Male",
                "linkedin": "https://linkedin.com/in/saikondareddy",
                "github": "https://github.com/saikondareddy",
                "portfolio": "https://saikonda.dev"
            },
            "education": [
                {
                    "institution": "Stanford University",
                    "college": "Stanford University",
                    "degree": "B.S.",
                    "specialization": "Computer Science",
                    "branch": "Computer Science",
                    "department": "School of Engineering",
                    "startYear": "2021",
                    "graduationYear": "2025",
                    "currentAcademicYear": "Senior",
                    "cgpa": "3.92",
                    "gradingSystem": "4.0 scale",
                    "tenthPercentage": "95%",
                    "twelfthPercentage": "96%",
                    "backlogs": "0"
                }
            ],
            "skills": {
                "programmingLanguages": ["Python", "TypeScript", "JavaScript", "Go"],
                "frameworks": ["FastAPI", "React", "Node.js", "Next.js"],
                "databases": ["MongoDB", "PostgreSQL", "Redis"],
                "cloud": ["AWS", "GCP"],
                "cloudPlatforms": ["AWS", "GCP"],
                "devops": ["Docker", "Kubernetes", "Git"],
                "aiMl": ["Ollama", "LangChain", "PyTorch"],
                "tools": ["VS Code", "Postman", "Linux"],
                "softSkills": ["Problem Solving", "System Design", "Team Leadership"],
                "technicalSkills": ["Python", "TypeScript", "React", "FastAPI", "Docker"]
            },
            "experiences": [
                {
                    "company": "Tech Innovations Inc.",
                    "role": "Software Engineer Intern",
                    "title": "Software Engineer Intern",
                    "employmentType": "Internship",
                    "startDate": "2024-05",
                    "endDate": "2024-08",
                    "currentlyWorking": False,
                    "technologies": ["Python", "FastAPI", "React", "Docker"],
                    "description": "Architected scalable microservices and asynchronous API endpoints, improving throughput by 40%."
                }
            ],
            "projects": [
                {
                    "projectName": "ApplyForMe",
                    "description": "AI-powered job application assistant Chrome extension with local LLM integration and deterministic autofill.",
                    "technologies": ["React", "TypeScript", "FastAPI", "MongoDB", "Ollama"],
                    "githubUrl": "https://github.com/saikondareddy/applyforme",
                    "liveUrl": "https://applyforme.dev",
                    "role": "Lead Full Stack Developer"
                }
            ],
            "professionalLinks": {
                "linkedin": "https://linkedin.com/in/saikondareddy",
                "github": "https://github.com/saikondareddy",
                "portfolio": "https://saikonda.dev"
            },
            "careerPreferences": {
                "preferredRoles": ["Software Engineer", "Full Stack Developer", "Backend Engineer"],
                "preferredIndustries": ["Technology", "Fintech", "Artificial Intelligence"],
                "employmentTypes": ["Full-time", "Internship"],
                "workModes": ["Remote", "Hybrid"],
                "preferredLocations": ["San Francisco, CA", "Seattle, WA", "Remote"],
                "willingToRelocate": True,
                "availability": "Immediate",
                "careerObjective": "Aspiring senior software engineer focused on distributed systems and AI developer tools.",
                "careerObjectives": "Aspiring senior software engineer focused on distributed systems and AI developer tools.",
                "professionalSummary": "Results-driven computer science graduate with proven experience building full-stack web applications, microservices, and AI workflow extensions.",
                "expectedSalary": "$120,000",
                "workAuthorization": "Authorized to work in US",
                "sponsorshipRequired": False
            },
            "onboardingCompleted": True,
            "createdAt": now,
            "updatedAt": now
        }

        score, _, _ = calculate_profile_completion(sample_profile_doc)
        sample_profile_doc["completionPercentage"] = score

        await db.profiles.insert_one(sample_profile_doc)
        logger.info(f"[Seeder] Seeded full applicant profile for {SAMPLE_USER_EMAIL} (Score: {score}%)")
    else:
        logger.info(f"[Seeder] Profile already exists for {SAMPLE_USER_EMAIL}; preserving without overwrite.")

