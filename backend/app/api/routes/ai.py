from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.api.deps import get_db, get_current_user
from app.schemas.ai import (
    AnswerGenerationRequest,
    AnswerGenerationResponse,
    FieldClassificationRequest,
    FieldClassificationResponse,
    JobAnalysisRequest,
    JobAnalysisResponse
)
from app.services.profile_service import ProfileService
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["AI Engine"])


@router.post("/generate-answer", response_model=AnswerGenerationResponse)
async def generate_answer(
    payload: AnswerGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Generate contextual, tailored application answer using applicant's profile and OmniRoute.
    Strictly forbids fabrication and adheres to validated experience.
    """
    user_id = str(current_user["_id"])
    profile = await ProfileService.get_user_profile(user_id, db)
    return await AIService.generate_answer(payload, profile, user_id, db)


@router.post("/classify-field", response_model=FieldClassificationResponse)
async def classify_field(
    payload: FieldClassificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Classify ambiguous form inputs that could not be mapped by deterministic heuristics.
    """
    # Simple semantic heuristics for ambiguous inputs
    combined = f"{payload.fieldName} {payload.fieldLabel} {payload.placeholder}".lower()
    if "degree" in combined or "major" in combined:
        return FieldClassificationResponse(
            mappedPath="education.degree",
            confidence=0.88,
            fieldCategory="education"
        )
    if "college" in combined or "school" in combined:
        return FieldClassificationResponse(
            mappedPath="education.college",
            confidence=0.89,
            fieldCategory="education"
        )
    if "summary" in combined or "bio" in combined:
        return FieldClassificationResponse(
            mappedPath="careerPreferences.professionalSummary",
            confidence=0.85,
            fieldCategory="career"
        )
    return FieldClassificationResponse(
        mappedPath=None,
        confidence=0.0,
        fieldCategory="unknown"
    )


@router.post("/analyze-job", response_model=JobAnalysisResponse)
async def analyze_job(
    payload: JobAnalysisRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Analyze job description requirements against applicant skills.
    """
    user_id = str(current_user["_id"])
    profile = await ProfileService.get_user_profile(user_id, db)
    
    # Extract user skills
    skills_obj = profile.get("skills", {})
    user_skills = set(
        [s.lower() for s in (
            skills_obj.get("technicalSkills", []) +
            skills_obj.get("programmingLanguages", []) +
            skills_obj.get("frameworks", []) +
            skills_obj.get("tools", [])
        )]
    )

    jd_lower = payload.jobDescription.lower()
    common_tech = ["python", "javascript", "typescript", "react", "node", "sql", "docker", "aws", "git", "mongodb", "fastapi"]
    detected = [tech for tech in common_tech if tech in jd_lower]
    matching = [tech for tech in detected if tech in user_skills]
    missing = [tech for tech in detected if tech not in user_skills]
    score = int((len(matching) / max(len(detected), 1)) * 100) if detected else 80

    return JobAnalysisResponse(
        detectedSkills=detected,
        matchingSkills=matching,
        missingSkills=missing,
        matchScore=score,
        roleSummary=f"{payload.jobTitle} at {payload.companyName}"
    )


@router.get("/provider-status")
async def get_provider_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Check the active LLM provider configuration and operational status.
    Never exposes raw API keys.
    """
    from app.core.config import settings
    provider = getattr(settings, "LLM_PROVIDER", "groq").lower().strip()
    if provider == "groq":
        model = getattr(settings, "GROQ_MODEL", "")
        has_key = bool(getattr(settings, "GROQ_API_KEY", ""))
    else:
        model = getattr(settings, "OLLAMA_MODEL", "")
        has_key = True

    return {
        "provider": provider,
        "model": model,
        "configured": has_key,
        "status": "ready" if has_key else "missing_credentials",
        "temperature": getattr(settings, "LLM_TEMPERATURE", 0.4),
        "timeout_seconds": getattr(settings, "LLM_TIMEOUT_SECONDS", 120.0),
        "concurrency": getattr(settings, "LLM_CONCURRENCY", 1)
    }


@router.post("/test-provider")
async def test_provider_connectivity(
    current_user: dict = Depends(get_current_user)
):
    """
    Verify live connectivity to configured LLM provider via a minimal ainvoke test.
    """
    import time
    from app.services.llm_factory import get_llm
    from app.core.config import settings

    provider = getattr(settings, "LLM_PROVIDER", "groq").lower().strip()
    t0 = time.time()
    try:
        llm = get_llm()
        resp = await llm.ainvoke("Respond with the single word: PONG")
        latency_ms = int((time.time() - t0) * 1000)
        content = resp.content if hasattr(resp, "content") else str(resp)
        return {
            "success": True,
            "provider": provider,
            "latency_ms": latency_ms,
            "response": content.strip()
        }
    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        return {
            "success": False,
            "provider": provider,
            "latency_ms": latency_ms,
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }


