import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.llm_factory import get_llm
from app.schemas.ai import (
    AnswerGenerationRequest,
    AnswerGenerationResponse,
    FieldClassificationRequest,
    FieldClassificationResponse,
    JobAnalysisRequest,
    JobAnalysisResponse
)

logger = logging.getLogger("applyforme.ai")

SYSTEM_PROMPT_ANSWER = """
You are ApplyForMe's AI Application Assistant. Your job is to draft compelling, truthful, and tailored answers for job application questions.

CRITICAL RULES:
1. Never fabricate experience, past companies, or job roles.
2. Never fabricate certifications, degrees, or awards.
3. Never invent CGPA, grades, or academic metrics.
4. Never claim skills or technologies not explicitly listed in the applicant's profile.
5. Emphasize actual projects, technologies, and achievements from the profile.
6. Tailor the answer contextually to the target company and role.
7. Tone must be professional, articulate, and confident.
8. If the applicant lacks relevant details for a question, state what is known and flag clarificationNeeded.
9. Avoid cliches or generic templates.
10. You must return valid JSON matching the schema:
{
  "answer": "string",
  "confidence": float (0.0 to 1.0),
  "keyPointsUsed": ["string"],
  "clarificationNeeded": "string or null"
}
"""


class AIService:
    @staticmethod
    def _format_profile_context(profile: dict) -> str:
        """Create structured summary of applicant's verified credentials."""
        lines = []
        personal = profile.get("personalInformation", {})
        lines.append(f"Applicant Name: {personal.get('fullName') or personal.get('firstName', '') + ' ' + personal.get('lastName', '')}")
        lines.append(f"Location: {personal.get('city', '')}, {personal.get('country', '')}")

        # Education
        education = profile.get("education", [])
        if education:
            lines.append("\nEducation:")
            for edu in education:
                lines.append(f"- {edu.get('degree', '')} in {edu.get('branch', '')} from {edu.get('college', '')} (Graduation: {edu.get('graduationYear', '')}, CGPA: {edu.get('cgpa', 'N/A')})")

        # Skills
        skills = profile.get("skills", {})
        all_skills = []
        for cat in ["technicalSkills", "programmingLanguages", "frameworks", "cloudPlatforms", "tools"]:
            items = skills.get(cat, [])
            if items:
                all_skills.extend(items)
        if all_skills:
            lines.append(f"\nVerified Skills: {', '.join(all_skills)}")

        # Experiences
        experiences = profile.get("experiences", [])
        if experiences:
            lines.append("\nWork Experience:")
            for exp in experiences:
                lines.append(f"- {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('duration', '')}): {exp.get('description', '')}")

        # Projects
        projects = profile.get("projects", [])
        if projects:
            lines.append("\nKey Projects:")
            for prj in projects:
                tech = ", ".join(prj.get("technologies", []))
                lines.append(f"- {prj.get('projectName', '')} ({tech}): {prj.get('description', '')}")

        # Career Summary
        career = profile.get("careerPreferences", {})
        if career.get("professionalSummary"):
            lines.append(f"\nProfessional Summary: {career.get('professionalSummary')}")
        if career.get("careerObjectives"):
            lines.append(f"Career Objectives: {career.get('careerObjectives')}")

        return "\n".join(lines)

    @staticmethod
    async def generate_answer(
        req: AnswerGenerationRequest,
        profile: dict,
        user_id: str,
        db: Optional[AsyncIOMotorDatabase]
    ) -> AnswerGenerationResponse:
        """Generate tailored application answer using Ollama and profile context."""
        from app.services.ai_answer_service import generate_application_answer

        res = await generate_application_answer(
            applicant_profile=profile,
            company_name=req.companyName,
            job_title=req.jobTitle,
            job_description=req.jobDescription or "",
            question=req.question,
            answer_length=req.mode or "standard"
        )

        ans = res.answer or "Information required to answer this question truthfully is missing from the applicant profile."
        confidence = res.confidence
        key_points = res.key_points_used or []
        clarification = ", ".join(res.missing_information) if res.missing_information else None

        # Save to generated_answers collection if DB is available
        if db is not None:
            try:
                await db.generated_answers.insert_one({
                    "userId": user_id,
                    "question": req.question,
                    "company": req.companyName,
                    "role": req.jobTitle,
                    "generatedAnswer": ans,
                    "confidence": confidence,
                    "createdAt": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.warning(f"Could not save generated answer to DB: {e}")

        return AnswerGenerationResponse(
            question=req.question,
            companyName=req.companyName,
            jobTitle=req.jobTitle,
            answer=ans,
            confidence=confidence,
            keyPointsUsed=key_points,
            clarificationNeeded=clarification
        )

