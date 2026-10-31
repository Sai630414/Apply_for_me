"""Standalone diagnostic script to verify Groq connectivity and intelligent answer generation."""

import asyncio
import os
import sys
import time

# Ensure backend directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Fix Windows console encoding for terminal display
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.core.config import settings
from app.services.llm_factory import get_llm, reset_llm
from app.services.ai_answer_service import generate_answer, AI_GENERATED


async def verify_groq():
    print("=" * 60)
    print(" ApplyForMe - Groq LLM Connectivity & Generation Verification")
    print("=" * 60)

    provider = getattr(settings, "LLM_PROVIDER", "").lower()
    model = getattr(settings, "GROQ_MODEL", "")
    api_key = getattr(settings, "GROQ_API_KEY", "")

    print(f"Provider Configured: {provider}")
    print(f"Model Configured   : {model}")
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    print(f"API Key Present    : {'YES (' + masked_key + ')' if api_key else 'NO'}")

    if provider != "groq":
        print(f"\n[Warning] LLM_PROVIDER is currently '{provider}', not 'groq'.")
        print("Set LLM_PROVIDER=groq in backend/.env to run with Groq.")
        return False

    if not api_key:
        print("\n[Error] GROQ_API_KEY is missing in backend/.env!")
        return False

    reset_llm()

    # Step 1: Direct ainvoke ping
    print("\n[Step 1] Sending test ping via LangChain ainvoke()...")
    t0 = time.time()
    try:
        llm = get_llm()
        resp = await llm.ainvoke("Respond with: Groq connection successful!")
        elapsed = time.time() - t0
        content = resp.content if hasattr(resp, "content") else str(resp)
        print(f"-> Success! Latency: {elapsed:.2f}s")
        print(f"-> Response: {content.strip()}")
    except Exception as exc:
        elapsed = time.time() - t0
        print(f"-> FAILED after {elapsed:.2f}s: {type(exc).__name__}: {exc}")
        return False

    # Step 2: Test intelligent contextual answer generation
    print("\n[Step 2] Testing application answer generation via generate_answer()...")
    test_profile = {
        "personalInformation": {
            "fullName": "Sai Konda Reddy",
            "email": "saikondareddypala@gmail.com",
            "city": "San Francisco",
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
            "technicalSkills": ["Python", "TypeScript", "FastAPI", "React", "Docker", "MongoDB"]
        },
        "projects": [
            {
                "projectName": "ApplyForMe",
                "technologies": ["React", "TypeScript", "FastAPI", "MongoDB", "Groq"],
                "description": "AI job application autofill assistant extension with intelligent grounded field synthesis."
            }
        ],
        "careerPreferences": {
            "availability": "Immediate",
            "employmentTypes": ["Full-time", "Internship"],
            "willingToRelocate": True
        }
    }

    t0 = time.time()
    try:
        ans_output = await generate_answer(
            question_id="test_motivation_q",
            question_text="Why do you want to join Paytm and work on payment systems?",
            field_type="textarea",
            applicant_profile=test_profile,
            company_name="Paytm",
            job_title="Backend Engineer",
            job_description="Design high-throughput payment infrastructure."
        )
        elapsed = time.time() - t0
        print(f"-> Success! Generation time: {elapsed:.2f}s")
        print(f"-> Question Category : {ans_output.category}")
        print(f"-> Execution Status  : {ans_output.execution_status}")
        print(f"-> Status            : {ans_output.status}")
        print(f"-> Confidence        : {ans_output.confidence}")
        print(f"-> Answer Length     : {len(ans_output.answer or '')} chars")
        print(f"-> Answer Preview    : {ans_output.answer}")
        print(f"-> Reason            : {ans_output.reason}")

        assert ans_output.status == "generated"
        assert ans_output.execution_status == AI_GENERATED
        assert ans_output.answer and len(ans_output.answer) > 20
        print("\nAll Groq assertions passed successfully!")
        return True
    except Exception as exc:
        print(f"-> FAILED: {type(exc).__name__}: {exc}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_groq())
    sys.exit(0 if success else 1)

