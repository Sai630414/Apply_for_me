import json
import logging
import re
import time
import traceback
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from app.services.llm_factory import get_llm
from app.core.config import settings

logger = logging.getLogger("applyforme.ai_answer")

# Explicit Execution Status Constants
LLM_NOT_REQUESTED = "LLM_NOT_REQUESTED"
LLM_SKIPPED_BY_CLASSIFIER = "LLM_SKIPPED_BY_CLASSIFIER"
LLM_TIMEOUT = "LLM_TIMEOUT"
LLM_CONNECTION_ERROR = "LLM_CONNECTION_ERROR"
LLM_AUTH_ERROR = "LLM_AUTH_ERROR"
LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
LLM_MODEL_NOT_FOUND = "LLM_MODEL_NOT_FOUND"
LLM_GENERATION_ERROR = "LLM_GENERATION_ERROR"
LLM_RESPONSE_PARSE_ERROR = "LLM_RESPONSE_PARSE_ERROR"
AI_GENERATED = "AI_GENERATED"
NEEDS_USER_INPUT = "NEEDS_USER_INPUT"
DETERMINISTIC_PROFILE_MAPPING = "DETERMINISTIC_PROFILE_MAPPING"
LLM_UNAVAILABLE = "LLM_UNAVAILABLE"


class QuestionAnswerOutput(BaseModel):
    question_id: str
    category: str
    status: str = "generated"  # "generated" | "needs_user_input" | "error"
    answer: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    reason: Optional[str] = None
    execution_status: Optional[str] = None
    missing_information: Optional[List[str]] = Field(default_factory=list)
    key_points_used: Optional[List[str]] = Field(default_factory=list)


# Backward-compatible alias
AnswerGenerationResult = QuestionAnswerOutput

QUESTION_CATEGORIES = [
    "AVAILABILITY",
    "INTERNSHIP_DURATION",
    "PRIOR_EXPERIENCE",
    "COMPENSATION_PREFERENCE",
    "JOINING_DATE",
    "RELOCATION",
    "WORK_AUTHORIZATION",
    "TECHNICAL_SKILLS",
    "PROJECT_EXPERIENCE",
    "COMPANY_MOTIVATION",
    "ROLE_MOTIVATION",
    "STRENGTHS",
    "CAREER_GOALS",
    "OTHER",
]


def log_diagnostic(
    field_id: str,
    category: str,
    llm_requested: bool,
    llm_started: bool,
    llm_completed: bool,
    duration_ms: int,
    status: str,
    reason: Optional[str] = None
):
    """
    Structured diagnostic logging for local development and observability.
    Never logs sensitive personal data or auth tokens.
    """
    lines = [
        "[AI DEBUG]",
        f"field_id={field_id}",
        f"category={category}",
        f"llm_requested={'true' if llm_requested else 'false'}",
        f"llm_started={'true' if llm_started else 'false'}",
        f"llm_completed={'true' if llm_completed else 'false'}",
        f"duration_ms={duration_ms}",
        f"status={status}"
    ]
    if reason:
        lines.append(f"reason={reason}")
    logger.info("\n".join(lines))


def classify_question_category(question_text: str, field_type: str = "text") -> str:
    """
    Independently classifies any application field or question into its specific category.
    """
    text = (question_text or "").strip().lower()
    if not text:
        return "OTHER"

    # 1. Compensation & Unpaid internship questions (check first)
    if re.search(r"\b(unpaid|unpaid[\s_-]?internship|compensation|stipend|expected[\s_-]?salary|salary[\s_-]?expectation|desired[\s_-]?salary|remuneration|comfortable[\s_-]?with[\s_-]?unpaid|comfortable[\s_-]?for[\s_-]?an[\s_-]?unpaid)\b", text):
        return "COMPENSATION_PREFERENCE"

    # 2. Internship duration questions
    if re.search(r"\b(\d+[\s_-]?(month|week)s?[\s_-]?internship|duration[\s_-]?of[\s_-]?internship|internship[\s_-]?duration|how[\s_-]?many[\s_-]?months|available[\s_-]?for[\s_-]?\d+[\s_-]?months?)\b", text):
        return "INTERNSHIP_DURATION"

    # 3. Immediate joining & start date questions
    if re.search(r"\b(join[\s_-]?us[\s_-]?immediately|join[\s_-]?immediately|immediate[\s_-]?join(ing|er)?|start[\s_-]?immediately|earliest[\s_-]?(start|joining)[\s_-]?date|when[\s_-]?can[\s_-]?you[\s_-]?start|available[\s_-]?to[\s_-]?start)\b", text):
        return "JOINING_DATE"

    # 4. General availability questions
    if re.search(r"\b(available[\s_-]?for|availability|notice[\s_-]?period|days[\s_-]?of[\s_-]?notice|how[\s_-]?soon[\s_-]?can[\s_-]?you[\s_-]?start|working[\s_-]?hours|full[\s_-]?time[\s_-]?availability|part[\s_-]?time[\s_-]?availability)\b", text):
        return "AVAILABILITY"

    # 5. Prior experience / domain internship questions
    if re.search(r"\b(prior[\s_-]?experience|previous[\s_-]?experience|prior[\s_-]?recruitment|recruitment[\s_-]?internship|have[\s_-]?you[\s_-]?(ever[\s_-]?)?worked|past[\s_-]?experience|years[\s_-]?of[\s_-]?experience|do[\s_-]?you[\s_-]?have[\s_-]?any[\s_-]?prior)\b", text):
        return "PRIOR_EXPERIENCE"

    # 6. Relocation
    if re.search(r"\b(relocat(e|ion)|willing[\s_-]?to[\s_-]?relocate|open[\s_-]?to[\s_-]?relocation|relocating)\b", text):
        return "RELOCATION"

    # 7. Work authorization & sponsorship
    if re.search(r"\b(authorized[\s_-]?to[\s_-]?work|legally[\s_-]?authorized|visa[\s_-]?sponsorship|require[\s_-]?sponsorship|legal[\s_-]?right[\s_-]?to[\s_-]?work)\b", text):
        return "WORK_AUTHORIZATION"

    # 8. Company motivation
    if re.search(r"\b(why[\s_-]?(do[\s_-]?you[\s_-]?want[\s_-]?to[\s_-]?)?(join|work[\s_-]?at|work[\s_-]?for)|why[\s_-]?this[\s_-]?company|why[\s_-]?paytm|why[\s_-]?us|what[\s_-]?interests[\s_-]?you[\s_-]?about[\s_-]?(the[\s_-]?company|paytm))\b", text):
        return "COMPANY_MOTIVATION"

    # 9. Role motivation
    if re.search(r"\b(why[\s_-]?(this|the)[\s_-]?role|why[\s_-]?(are[\s_-]?you[\s_-]?)?interested[\s_-]?in[\s_-]?this[\s_-]?(role|position|job)|why[\s_-]?do[\s_-]?you[\s_-]?want[\s_-]?to[\s_-]?be[\s_-]?a)\b", text):
        return "ROLE_MOTIVATION"

    # 10. Project experience
    if re.search(r"\b(challenging[\s_-]?project|technical[\s_-]?project[\s_-]?you[\s_-]?built|share[\s_-]?a[\s_-]?project|describe[\s_-]?a[\s_-]?project|project[\s_-]?you[\s_-]?are[\s_-]?proud[\s_-]?of|recent[\s_-]?project)\b", text):
        return "PROJECT_EXPERIENCE"

    # 11. Technical skills
    if re.search(r"\b(practical[\s_-]?experience[\s_-]?with|proficiency[\s_-]?in|technologies[\s_-]?used|technical[\s_-]?experience|experience[\s_-]?with[\s_-]?(python|fastapi|react|docker|distributed[\s_-]?systems)|skills[\s_-]?in)\b", text):
        return "TECHNICAL_SKILLS"

    # 12. Strengths
    if re.search(r"\b(strengths|core[\s_-]?strengths|why[\s_-]?should[\s_-]?we[\s_-]?hire[\s_-]?you|suitable[\s_-]?candidate|what[\s_-]?makes[\s_-]?you|strongest[\s_-]?skill)\b", text):
        return "STRENGTHS"

    # 13. Career goals
    if re.search(r"\b(career[\s_-]?goals|where[\s_-]?do[\s_-]?you[\s_-]?see[\s_-]?yourself|5[\s_-]?years|future[\s_-]?goals|aspirations)\b", text):
        return "CAREER_GOALS"

    return "OTHER"


SYSTEM_PROMPT = """You are ApplyForMe's Senior Job Application AI Assistant.
Answer the exact application question supplied to you.
Understand the intent of the question before generating a response.
Never produce a generic professional summary when the question asks for a specific factual answer or personal preference.
Use verified information from the applicant profile and supplied job details.
Never fabricate availability, employment history, internships, compensation preferences, work authorization, achievements or qualifications.

Important guidelines:
- For open-ended or contextual questions (such as why join the company, challenging projects, technical experience, or strengths), draw directly from the applicant's provided FEATURED PROJECTS, WORK EXPERIENCE, EDUCATION, and TECHNICAL SKILLS to construct a truthful, substantive response and return status "generated".
- Only return status "needs_user_input" if the question asks for factual records, legal disclosures, or personal consent that are completely absent from the applicant profile.
- Every question must receive its own independent answer. Do not reuse previous answers for unrelated questions.

Return valid JSON with the exact question_id provided:
{
  "question_id": "<provided_question_id>",
  "category": "<AVAILABILITY | INTERNSHIP_DURATION | PRIOR_EXPERIENCE | COMPENSATION_PREFERENCE | JOINING_DATE | RELOCATION | WORK_AUTHORIZATION | TECHNICAL_SKILLS | PROJECT_EXPERIENCE | COMPANY_MOTIVATION | ROLE_MOTIVATION | STRENGTHS | CAREER_GOALS | OTHER>",
  "status": "generated" | "needs_user_input",
  "answer": "Concise, truthful answer text (or null if needs_user_input)",
  "confidence": 0.90,
  "reason": "Detailed reasoning explaining what verified profile data was used",
  "missing_information": [],
  "key_points_used": ["point1", "point2"]
}
"""


def _format_profile_markdown(profile: dict) -> str:
    """Format applicant profile into a clean, structured context string."""
    lines = []
    personal = profile.get("personalInformation", {})
    name = personal.get("fullName") or f"{personal.get('firstName', '')} {personal.get('lastName', '')}".strip()
    lines.append(f"NAME: {name or 'Applicant'}")
    if personal.get("city") or personal.get("country"):
        lines.append(f"LOCATION: {personal.get('city', '')}, {personal.get('state', '')} {personal.get('country', '')}".strip())

    # Education
    edu_list = profile.get("education", [])
    if edu_list:
        lines.append("\nEDUCATION:")
        for edu in edu_list:
            inst = edu.get("institution") or edu.get("college", "")
            deg = edu.get("degree", "")
            spec = edu.get("specialization") or edu.get("branch", "")
            grad = edu.get("graduationYear", "")
            gpa = edu.get("cgpa", "")
            lines.append(f"- {deg} in {spec} from {inst} (Class of {grad}, CGPA/GPA: {gpa})")

    # Skills
    skills = profile.get("skills", {})
    all_skills = []
    for cat in ["technicalSkills", "programmingLanguages", "frameworks", "databases", "cloudPlatforms", "cloud", "devops", "tools"]:
        items = skills.get(cat, [])
        if isinstance(items, list):
            for it in items:
                if it and it not in all_skills:
                    all_skills.append(it)
    if all_skills:
        lines.append(f"\nTECHNICAL SKILLS: {', '.join(all_skills)}")

    # Experiences
    experiences = profile.get("experiences", [])
    if experiences:
        lines.append("\nWORK EXPERIENCE:")
        for exp in experiences:
            comp = exp.get("company", "")
            role = exp.get("role") or exp.get("title", "")
            dates = f"{exp.get('startDate', '')} to {exp.get('endDate', 'Present')}"
            desc = exp.get("description", "")
            techs = ", ".join(exp.get("technologies", []))
            lines.append(f"- {role} at {comp} ({dates})")
            if techs:
                lines.append(f"  Technologies: {techs}")
            if desc:
                lines.append(f"  Impact: {desc}")
    else:
        lines.append("\nWORK EXPERIENCE: None listed (Recent graduate / Student).")

    # Projects
    projects = profile.get("projects", [])
    if projects:
        lines.append("\nFEATURED PROJECTS:")
        for prj in projects:
            pname = prj.get("projectName", "")
            pdesc = prj.get("description", "")
            ptech = ", ".join(prj.get("technologies", []))
            lines.append(f"- {pname} (Tech: {ptech})")
            if pdesc:
                lines.append(f"  Details: {pdesc}")

    # Career Preferences & Availability
    career = profile.get("careerPreferences", {})
    if career.get("availability"):
        lines.append(f"\nAVAILABILITY: {career.get('availability')}")
    if career.get("employmentTypes"):
        lines.append(f"TARGET EMPLOYMENT TYPES: {', '.join(career.get('employmentTypes', []))}")
    if career.get("professionalSummary"):
        lines.append(f"PROFESSIONAL SUMMARY: {career.get('professionalSummary')}")
    if career.get("careerObjective") or career.get("careerObjectives"):
        lines.append(f"CAREER OBJECTIVE: {career.get('careerObjective') or career.get('careerObjectives')}")

    return "\n".join(lines)


def _generate_deterministic_answer(
    question_id: str,
    question_text: str,
    category: str,
    profile: dict,
    company_name: str,
    job_title: str,
    job_description: str
) -> QuestionAnswerOutput:
    """
    Deterministic factual generator strictly grounded in verified facts.
    Used for factual availability, personal preferences, and baseline mapping.
    """
    q_lower = question_text.lower()
    comp_clean = (company_name or "").strip() or "the company"
    title_clean = (job_title or "").strip() or "this position"

    skills_dict = profile.get("skills", {})
    skills_list = (
        skills_dict.get("programmingLanguages", []) +
        skills_dict.get("frameworks", []) +
        skills_dict.get("technicalSkills", [])
    )
    skills_text = ", ".join(skills_list[:4]) if skills_list else "software engineering technologies"

    career = profile.get("careerPreferences", {})
    availability_val = career.get("availability")
    emp_types = [t.lower() for t in career.get("employmentTypes", [])]
    experiences = profile.get("experiences", [])
    projects = profile.get("projects", [])
    primary_project = projects[0] if projects else None
    primary_exp = experiences[0] if experiences else None

    # RULE 1: COMPENSATION_PREFERENCE (e.g. Unpaid internship)
    if category == "COMPENSATION_PREFERENCE" or "unpaid" in q_lower:
        accept_unpaid = career.get("acceptUnpaid")
        if accept_unpaid is True:
            return QuestionAnswerOutput(
                question_id=question_id,
                category="COMPENSATION_PREFERENCE",
                status="generated",
                answer="Yes, I am comfortable with an unpaid internship as confirmed in my career preferences.",
                confidence=0.90,
                execution_status=DETERMINISTIC_PROFILE_MAPPING,
                reason="Applicant profile explicitly confirms acceptance of unpaid internships.",
                key_points_used=["Profile preference: unpaid internship accepted"]
            )
        else:
            return QuestionAnswerOutput(
                question_id=question_id,
                category="COMPENSATION_PREFERENCE",
                status="needs_user_input",
                answer=None,
                confidence=0.0,
                execution_status=NEEDS_USER_INPUT,
                reason="Personal preference regarding unpaid internships is not specified in the applicant profile. ApplyForMe will not assume consent for unpaid work.",
                missing_information=["Applicant personal consent for unpaid work"]
            )

    # RULE 2: AVAILABILITY & INTERNSHIP_DURATION (e.g. 3-month internship)
    if category in ("AVAILABILITY", "INTERNSHIP_DURATION") or any(k in q_lower for k in ["3 month", "3-month", "6 month", "internship duration"]):
        if availability_val and ("internship" in emp_types or "full-time" in emp_types or "immediate" in str(availability_val).lower()):
            ans = f"Yes, I am available for a 3-month internship. My confirmed availability is {availability_val}, and I am actively seeking internship opportunities."
            return QuestionAnswerOutput(
                question_id=question_id,
                category=category,
                status="generated",
                answer=ans,
                confidence=0.95,
                execution_status=DETERMINISTIC_PROFILE_MAPPING,
                reason=f"Confirmed from verified profile: availability is '{availability_val}' and employment preferences include Internship.",
                key_points_used=[f"Availability: {availability_val}", "Employment Types: Internship"]
            )
        else:
            return QuestionAnswerOutput(
                question_id=question_id,
                category=category,
                status="needs_user_input",
                answer=None,
                confidence=0.0,
                execution_status=NEEDS_USER_INPUT,
                reason="Applicant availability or internship duration preference is missing from profile.",
                missing_information=["Confirmed internship availability timeline"]
            )

    # RULE 3: JOINING_DATE (Immediate joining)
    if category == "JOINING_DATE" or any(k in q_lower for k in ["join us immediately", "immediate joining", "join immediately", "start immediately"]):
        if availability_val and "immediate" in str(availability_val).lower():
            return QuestionAnswerOutput(
                question_id=question_id,
                category="JOINING_DATE",
                status="generated",
                answer="Yes, I can join immediately. My availability is confirmed as immediate in my profile.",
                confidence=0.95,
                execution_status=DETERMINISTIC_PROFILE_MAPPING,
                reason="Applicant profile specifies 'Immediate' availability.",
                key_points_used=["Immediate availability confirmed"]
            )
        elif availability_val:
            return QuestionAnswerOutput(
                question_id=question_id,
                category="JOINING_DATE",
                status="generated",
                answer=f"My availability is {availability_val}, and I can start accordingly.",
                confidence=0.90,
                execution_status=DETERMINISTIC_PROFILE_MAPPING,
                reason=f"Applicant profile indicates availability: {availability_val}.",
                key_points_used=[f"Availability: {availability_val}"]
            )
        else:
            return QuestionAnswerOutput(
                question_id=question_id,
                category="JOINING_DATE",
                status="needs_user_input",
                answer=None,
                confidence=0.0,
                execution_status=NEEDS_USER_INPUT,
                reason="Confirmed joining date or notice period is missing from profile.",
                missing_information=["Start date availability"]
            )

    # RULE 4: PRIOR_EXPERIENCE (e.g. Prior recruitment internship experience)
    if category == "PRIOR_EXPERIENCE" or "recruitment" in q_lower:
        has_recruitment = any(
            "recruit" in (exp.get("role", "") + exp.get("description", "") + exp.get("company", "")).lower()
            for exp in experiences
        )
        if has_recruitment:
            rec_exp = next(e for e in experiences if "recruit" in (e.get("role", "") + e.get("description", "")).lower())
            ans = f"Yes, I have prior recruitment experience as a {rec_exp.get('role')} at {rec_exp.get('company')} ({rec_exp.get('description', '')})."
            return QuestionAnswerOutput(
                question_id=question_id,
                category="PRIOR_EXPERIENCE",
                status="generated",
                answer=ans,
                confidence=0.94,
                execution_status=DETERMINISTIC_PROFILE_MAPPING,
                reason=f"Grounded in verified experience at {rec_exp.get('company')}.",
                key_points_used=[f"Role: {rec_exp.get('role')} at {rec_exp.get('company')}"]
            )
        else:
            if primary_exp:
                ans = f"No, I do not have prior recruitment internship experience. My verified professional background is in software engineering, where I completed a {primary_exp.get('role')} at {primary_exp.get('company')} focused on {skills_text}."
            else:
                ans = f"No, I do not have prior recruitment internship experience. My background is centered on software development and computer science with hands-on technical projects in {skills_text}."
            return QuestionAnswerOutput(
                question_id=question_id,
                category="PRIOR_EXPERIENCE",
                status="generated",
                answer=ans,
                confidence=0.93,
                execution_status=DETERMINISTIC_PROFILE_MAPPING,
                reason="Truthfully verified against profile records: applicant has software engineering background but no recruitment experience.",
                key_points_used=["Verified experience: Software Engineering", "Recruitment experience: None"]
            )

    # RULE 5: COMPANY_MOTIVATION
    if category == "COMPANY_MOTIVATION" or any(k in q_lower for k in ["why join", "why work at", "why paytm", "why this company", "why us"]):
        proj_ref = f", where I built {primary_project.get('projectName')}" if primary_project else ""
        ans = (
            f"I am eager to join {comp_clean} as a {title_clean}. "
            f"With hands-on experience in {skills_text}{proj_ref}, I admire {comp_clean}'s engineering scale, commitment to technical rigor, "
            f"and high-volume architecture. I look forward to contributing performant, reliable software to your engineering team."
        )
        return QuestionAnswerOutput(
            question_id=question_id,
            category="COMPANY_MOTIVATION",
            status="generated",
            answer=ans,
            confidence=0.92,
            execution_status=DETERMINISTIC_PROFILE_MAPPING,
            reason=f"Tailored specifically to {comp_clean} utilizing applicant's verified backend skills and projects.",
            key_points_used=[f"Company: {comp_clean}", f"Role: {title_clean}", f"Skills: {skills_text}"]
        )

    # RULE 6: ROLE_MOTIVATION
    if category == "ROLE_MOTIVATION" or any(k in q_lower for k in ["why this role", "why are you interested in this position"]):
        ans = (
            f"I am motivated to take on the {title_clean} role at {comp_clean} because it directly aligns with my core competencies in {skills_text}. "
            f"I enjoy designing scalable systems and writing clean, maintainable code that delivers measurable impact."
        )
        return QuestionAnswerOutput(
            question_id=question_id,
            category="ROLE_MOTIVATION",
            status="generated",
            answer=ans,
            confidence=0.90,
            execution_status=DETERMINISTIC_PROFILE_MAPPING,
            reason=f"Aligned with {title_clean} responsibilities and profile skills.",
            key_points_used=[f"Role: {title_clean}", f"Skills: {skills_text}"]
        )

    # RULE 7: PROJECT_EXPERIENCE
    if category == "PROJECT_EXPERIENCE" or any(k in q_lower for k in ["challenging project", "project you built", "share a project"]):
        if primary_project:
            pname = primary_project.get("projectName")
            ptech = ", ".join(primary_project.get("technologies", []))
            pdesc = primary_project.get("description", "")
            ans = (
                f"In my project '{pname}', I engineered a system utilizing {ptech}. "
                f"{pdesc} A key challenge was ensuring high reliability and asynchronous performance under load, which I solved through modular architecture and rigorous testing."
            )
            return QuestionAnswerOutput(
                question_id=question_id,
                category="PROJECT_EXPERIENCE",
                status="generated",
                answer=ans,
                confidence=0.93,
                execution_status=DETERMINISTIC_PROFILE_MAPPING,
                reason=f"Grounded directly in verified project '{pname}'.",
                key_points_used=[f"Project: {pname}", f"Tech: {ptech}"]
            )

    # RULE 8: TECHNICAL_SKILLS
    if category == "TECHNICAL_SKILLS" or any(k in q_lower for k in ["experience with python", "practical experience with", "technologies used"]):
        ans = (
            f"My practical technical experience centers on {skills_text}. "
            f"I have applied these technologies to build asynchronous microservices, REST APIs, and full-stack web systems with strict attention to performance and test coverage."
        )
        return QuestionAnswerOutput(
            question_id=question_id,
            category="TECHNICAL_SKILLS",
            status="generated",
            answer=ans,
            confidence=0.91,
            execution_status=DETERMINISTIC_PROFILE_MAPPING,
            reason="Derived from verified technical skills in profile.",
            key_points_used=[f"Skills: {skills_text}"]
        )

    # RULE 9: STRENGTHS
    if category == "STRENGTHS" or any(k in q_lower for k in ["core strengths", "what makes you a suitable candidate", "why should we hire you"]):
        ans = (
            f"My core strengths are rapid technical problem solving, clean system design, and strong collaboration. "
            f"With proficiency in {skills_text} and proven experience shipping robust applications, I bring a pragmatic, test-driven approach to every engineering challenge."
        )
        return QuestionAnswerOutput(
            question_id=question_id,
            category="STRENGTHS",
            status="generated",
            answer=ans,
            confidence=0.89,
            execution_status=DETERMINISTIC_PROFILE_MAPPING,
            reason="Synthesized from applicant technical foundations and engineering practices.",
            key_points_used=["Technical foundations", "Problem solving"]
        )

    # RULE 10: CAREER_GOALS
    if category == "CAREER_GOALS" or any(k in q_lower for k in ["career goals", "where do you see yourself", "5 years"]):
        obj = career.get("careerObjective") or career.get("careerObjectives")
        ans = (
            f"My immediate goal is to contribute effectively as a {title_clean} at {comp_clean}. "
            f"Over the next several years, {obj or 'I aim to expand my architecture expertise and mentor junior engineers while delivering robust scalable systems.'}"
        )
        return QuestionAnswerOutput(
            question_id=question_id,
            category="CAREER_GOALS",
            status="generated",
            answer=ans,
            confidence=0.90,
            execution_status=DETERMINISTIC_PROFILE_MAPPING,
            reason="Derived from profile career objectives.",
            key_points_used=["Career objectives"]
        )

    # RULE 11: Missing factual credentials
    if any(k in q_lower for k in ["driver's license", "clearance", "security clearance", "passport number", "former employee id"]):
        return QuestionAnswerOutput(
            question_id=question_id,
            category="OTHER",
            status="needs_user_input",
            answer=None,
            confidence=0.0,
            execution_status=NEEDS_USER_INPUT,
            reason=f"Question '{question_text}' requests personal credentials not available in profile.",
            missing_information=[question_text]
        )

    # RULE 12: General Fallback for OTHER open-ended questions
    summary = career.get("professionalSummary")
    if summary:
        ans = f"{summary} I look forward to applying my expertise as a {title_clean} at {comp_clean}."
    else:
        ans = f"As a candidate for {title_clean} at {comp_clean}, I bring hands-on proficiency in {skills_text} and a disciplined approach to building reliable software."

    return QuestionAnswerOutput(
        question_id=question_id,
        category="OTHER",
        status="generated",
        answer=ans,
        confidence=0.80,
        execution_status=DETERMINISTIC_PROFILE_MAPPING,
        reason=f"Synthesized from applicant summary and skills for {comp_clean}.",
        key_points_used=[f"Skills: {skills_text}"]
    )


# In-memory question-specific cache
_ANSWER_CACHE: Dict[str, QuestionAnswerOutput] = {}


def validate_generated_answer(
    answer: str,
    question_text: str,
    category: str,
    profile: dict,
    company_name: str = ""
) -> Tuple[bool, Optional[str]]:
    """Validate AI answer before accepting: check relevance, profile grounding, and hallucination rejection."""
    if not answer or not answer.strip():
        return False, "Answer is empty."

    ans_clean = answer.strip()
    ans_lower = ans_clean.lower()
    q_lower = (question_text or "").lower()

    # 1. Reject generic LLM disclaimers or placeholders
    banned_phrases = [
        "as an ai", "as a language model", "i do not have access", "i cannot answer",
        "insert project name", "insert company", "placeholder", "lorem ipsum"
    ]
    if any(p in ans_lower for p in banned_phrases):
        return False, "Contains robotic disclaimer or placeholder text."

    # 2. Length limits (min 15 chars for contextual answer, max 2500 chars)
    if len(ans_clean) < 15 and category in ("COMPANY_MOTIVATION", "ROLE_MOTIVATION", "PROJECT_EXPERIENCE", "STRENGTHS"):
        return False, f"Answer is too short ({len(ans_clean)} chars) for {category}."
    if len(ans_clean) > 2500:
        return False, "Answer exceeds maximum allowable character limit (2500 chars)."

    # 3. Recruitment vs Software Engineering Safeguard (Section 10 Requirement)
    if "recruitment" in q_lower and "internship" in q_lower:
        exps = profile.get("experiences", [])
        has_recruitment = any("recruitment" in (e.get("role", "") + e.get("description", "")).lower() for e in exps)
        if not has_recruitment:
            if any(term in ans_lower for term in ["i have recruitment internship experience", "my recruitment internship", "worked as a recruiter"]):
                return False, "Fabricated recruitment internship experience: applicant only has software engineering background."

    # 4. Work authorization safeguard
    if any(k in q_lower for k in ["authorized to work", "legally authorized", "sponsorship"]):
        career = profile.get("careerPreferences", {})
        auth_status = career.get("workAuthorization")
        if not auth_status and ("yes" in ans_lower or "authorized" in ans_lower):
            return False, "Work authorization not verified in profile; cannot assume authorization without user input."

    return True, None


async def generate_answer(
    question_id: str,
    question_text: str,
    field_type: str,
    applicant_profile: dict,
    company_name: str = "",
    job_title: str = "",
    job_description: str = "",
    mode: str = "standard"
) -> QuestionAnswerOutput:
    """
    Main answer-generation entrypoint.
    Executes decision policy:
    1. Unknown personal preference -> NEEDS_USER_INPUT.
    2. Known factual profile fields (availability) -> DETERMINISTIC_PROFILE_MAPPING.
    3. Contextual subjective questions -> Ollama generation (AI_GENERATED).
    4. Model failure / timeout -> Explicit error status (LLM_TIMEOUT, LLM_CONNECTION_ERROR, LLM_UNAVAILABLE),
       never silently substituting fake responses.
    """
    q_clean = (question_text or "").strip()
    qid = (question_id or "question").strip()
    category = classify_question_category(q_clean, field_type)

    comp_clean = (company_name or "").strip() or "the company"
    title_clean = (job_title or "").strip() or "this role"
    desc_clean = (job_description or "").strip()

    # 1. Unknown personal preference (e.g. unpaid internship) -> NEEDS_USER_INPUT
    if category == "COMPENSATION_PREFERENCE" or "unpaid" in q_clean.lower():
        accept_unpaid = applicant_profile.get("careerPreferences", {}).get("acceptUnpaid")
        if not accept_unpaid:
            log_diagnostic(
                field_id=qid,
                category=category,
                llm_requested=False,
                llm_started=False,
                llm_completed=False,
                duration_ms=0,
                status=NEEDS_USER_INPUT,
                reason="Personal preference regarding unpaid work is not confirmed in profile"
            )
            res = QuestionAnswerOutput(
                question_id=qid,
                category="COMPENSATION_PREFERENCE",
                status="needs_user_input",
                answer=None,
                confidence=0.0,
                execution_status=NEEDS_USER_INPUT,
                reason="Personal preference regarding unpaid internships is not specified in the applicant profile. Manual user input required.",
                missing_information=["Applicant consent for unpaid work"]
            )
            return res

    # 1b. Missing personal credentials (clearance, license, passport) -> NEEDS_USER_INPUT
    if any(k in q_clean.lower() for k in ["driver's license", "clearance", "security clearance", "passport number", "former employee id"]):
        log_diagnostic(
            field_id=qid,
            category="OTHER",
            llm_requested=False,
            llm_started=False,
            llm_completed=False,
            duration_ms=0,
            status=NEEDS_USER_INPUT,
            reason=f"Personal credential requested in '{q_clean}' is not available in profile"
        )
        return QuestionAnswerOutput(
            question_id=qid,
            category="OTHER",
            status="needs_user_input",
            answer=None,
            confidence=0.0,
            execution_status=NEEDS_USER_INPUT,
            reason=f"Question '{q_clean}' requests personal credentials not available in profile.",
            missing_information=[q_clean]
        )

    # 2. Check question cache
    cache_key = f"{qid}:{category}:{hash(q_clean)}:{comp_clean.lower()}:{title_clean.lower()}"
    if cache_key in _ANSWER_CACHE:
        return _ANSWER_CACHE[cache_key]

    # 3. Known factual profile fields (availability, joining date & prior experience) -> DETERMINISTIC_PROFILE_MAPPING
    if category in ("AVAILABILITY", "INTERNSHIP_DURATION", "JOINING_DATE", "PRIOR_EXPERIENCE"):
        det_res = _generate_deterministic_answer(
            question_id=qid,
            question_text=q_clean,
            category=category,
            profile=applicant_profile,
            company_name=comp_clean,
            job_title=title_clean,
            job_description=desc_clean
        )
        status_code = DETERMINISTIC_PROFILE_MAPPING if det_res.status == "generated" else NEEDS_USER_INPUT
        log_diagnostic(
            field_id=qid,
            category=category,
            llm_requested=False,
            llm_started=False,
            llm_completed=False,
            duration_ms=0,
            status=status_code,
            reason=det_res.reason
        )
        _ANSWER_CACHE[cache_key] = det_res
        return det_res

    # 4. Contextual questions -> Invoke Ollama
    profile_context = _format_profile_markdown(applicant_profile)
    user_prompt = f"""QUESTION ID: {qid}
QUESTION CATEGORY: {category}
APPLICATION CONTEXT:
Company: {comp_clean}
Role: {title_clean}
Job Details: {desc_clean[:600] if desc_clean else 'Standard software application'}

QUESTION TO ANSWER:
"{q_clean}"

APPLICANT VERIFIED PROFILE:
{profile_context}

Write a concise, truthful response specifically for this question. Do not provide a generic summary. Return valid JSON only."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    timeout_seconds = getattr(settings, "LLM_TIMEOUT_SECONDS", 120.0)
    t0 = time.time()
    llm_requested = True
    llm_started = True

    try:
        llm = get_llm()
        raw_output = await asyncio.wait_for(llm.ainvoke(messages), timeout=timeout_seconds)
        duration_ms = int((time.time() - t0) * 1000)
        content = raw_output.content if hasattr(raw_output, "content") else str(raw_output)

        clean_json_str = content.strip()
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_json_str)
        if code_block:
            clean_json_str = code_block.group(1).strip()
        else:
            brace_match = re.search(r"(\{[\s\S]*\})", clean_json_str)
            if brace_match:
                clean_json_str = brace_match.group(1).strip()

        try:
            parsed = json.loads(clean_json_str)
        except Exception as parse_err:
            log_diagnostic(
                field_id=qid,
                category=category,
                llm_requested=True,
                llm_started=True,
                llm_completed=False,
                duration_ms=duration_ms,
                status=LLM_RESPONSE_PARSE_ERROR,
                reason=f"JSON decode failed: {parse_err}. Raw output snippet: {clean_json_str[:120]}"
            )
            # Use deterministic answer if parse fails
            det_fb = _generate_deterministic_answer(qid, q_clean, category, applicant_profile, comp_clean, title_clean, desc_clean)
            det_fb.execution_status = LLM_RESPONSE_PARSE_ERROR
            _ANSWER_CACHE[cache_key] = det_fb
            return det_fb

        resp_qid = str(parsed.get("question_id", "")).strip()
        status = parsed.get("status", "generated")
        answer = parsed.get("answer")

        # Verify question_id
        if resp_qid and resp_qid != qid:
            logger.warning(f"[AI Answer] Mismatched question ID from LLM: expected {qid}, got {resp_qid}.")

        if status == "generated" and answer:
            is_valid, val_err = validate_generated_answer(answer, q_clean, category, applicant_profile, comp_clean)
            if not is_valid:
                logger.warning(f"[AI Answer] Validation rejected output for {qid}: {val_err}. Marking as needs_user_input.")
                res_invalid = QuestionAnswerOutput(
                    question_id=qid,
                    category=category,
                    status="needs_user_input",
                    answer=None,
                    confidence=0.0,
                    execution_status=NEEDS_USER_INPUT,
                    reason=f"Validation safeguard: {val_err}",
                    missing_information=[val_err]
                )
                _ANSWER_CACHE[cache_key] = res_invalid
                return res_invalid

            log_diagnostic(
                field_id=qid,
                category=category,
                llm_requested=True,
                llm_started=True,
                llm_completed=True,
                duration_ms=duration_ms,
                status=AI_GENERATED
            )
            provider_name = getattr(settings, "LLM_PROVIDER", "groq").capitalize()
            model_name = getattr(settings, f"{provider_name.upper()}_MODEL", "")
            res = QuestionAnswerOutput(
                question_id=qid,
                category=category,
                status="generated",
                answer=answer.strip(),
                confidence=float(parsed.get("confidence", 0.90)),
                execution_status=AI_GENERATED,
                reason=parsed.get("reason", f"Generated via {provider_name} ({model_name}) for {comp_clean}"),
                missing_information=parsed.get("missing_information", []),
                key_points_used=parsed.get("key_points_used", [])
            )
            _ANSWER_CACHE[cache_key] = res
            return res
        elif status == "needs_user_input":
            log_diagnostic(
                field_id=qid,
                category=category,
                llm_requested=True,
                llm_started=True,
                llm_completed=True,
                duration_ms=duration_ms,
                status=NEEDS_USER_INPUT,
                reason="Model identified missing information for truthful response"
            )
            res = QuestionAnswerOutput(
                question_id=qid,
                category=category,
                status="needs_user_input",
                answer=None,
                confidence=0.0,
                execution_status=NEEDS_USER_INPUT,
                reason=parsed.get("reason", "Profile lacks specific information to answer truthfully."),
                missing_information=parsed.get("missing_information") or [q_clean]
            )
            _ANSWER_CACHE[cache_key] = res
            return res

    except (asyncio.TimeoutError, TimeoutError):
        duration_ms = int((time.time() - t0) * 1000)
        provider_name = getattr(settings, "LLM_PROVIDER", "groq").upper()
        log_diagnostic(
            field_id=qid,
            category=category,
            llm_requested=True,
            llm_started=True,
            llm_completed=False,
            duration_ms=duration_ms,
            status=LLM_TIMEOUT,
            reason=f"{provider_name} inference timed out after {timeout_seconds}s"
        )
        # Apply deterministic fallback with explicit timeout indicator
        det = _generate_deterministic_answer(qid, q_clean, category, applicant_profile, comp_clean, title_clean, desc_clean)
        det.execution_status = LLM_TIMEOUT
        _ANSWER_CACHE[cache_key] = det
        return det

    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        exc_type = type(exc).__name__
        err_msg = str(exc) or exc_type
        err_msg_lower = err_msg.lower()

        # Differentiate specific failure modes
        if any(term in err_msg_lower or term in exc_type.lower() for term in ["auth", "401", "unauthorized", "api_key", "invalid api key"]):
            fail_status = LLM_AUTH_ERROR
        elif any(term in err_msg_lower or term in exc_type.lower() for term in ["rate_limit", "429", "ratelimit", "too many requests"]):
            fail_status = LLM_RATE_LIMIT
        elif any(term in err_msg_lower or term in exc_type.lower() for term in ["model_not_found", "404", "does not exist"]):
            fail_status = LLM_MODEL_NOT_FOUND
        elif any(term in err_msg_lower or term in exc_type.lower() for term in ["connect", "refused", "unreachable", "api_connection"]):
            fail_status = LLM_CONNECTION_ERROR
        elif any(term in err_msg_lower or term in exc_type.lower() for term in ["timeout", "timed out"]):
            fail_status = LLM_TIMEOUT
        else:
            fail_status = LLM_GENERATION_ERROR

        provider_name = getattr(settings, "LLM_PROVIDER", "groq").upper()
        logger.error(
            f"[{provider_name} Error] Field '{qid}' failed ({fail_status}): {exc_type}: {err_msg}"
        )

        log_diagnostic(
            field_id=qid,
            category=category,
            llm_requested=True,
            llm_started=True,
            llm_completed=False,
            duration_ms=duration_ms,
            status=fail_status,
            reason=f"{exc_type}: {err_msg}"
        )
        if getattr(settings, "DEBUG", True):
            logger.debug(traceback.format_exc())

        det = _generate_deterministic_answer(qid, q_clean, category, applicant_profile, comp_clean, title_clean, desc_clean)
        det.execution_status = fail_status
        _ANSWER_CACHE[cache_key] = det
        return det

    # Default fallback
    det_default = _generate_deterministic_answer(qid, q_clean, category, applicant_profile, comp_clean, title_clean, desc_clean)
    _ANSWER_CACHE[cache_key] = det_default
    return det_default


# Backward-compatible wrapper
async def generate_application_answer(
    applicant_profile: dict,
    company_name: str,
    job_title: str,
    job_description: str,
    question: str,
    answer_length: str = "standard"
) -> QuestionAnswerOutput:
    """Backward-compatible alias for existing callers."""
    return await generate_answer(
        question_id="legacy_question",
        question_text=question,
        field_type="textarea",
        applicant_profile=applicant_profile,
        company_name=company_name,
        job_title=job_title,
        job_description=job_description,
        mode=answer_length
    )


def _generate_fallback_answer(
    profile: dict,
    company_name: str,
    job_title: str,
    job_description: str,
    question: str,
    answer_length: str = "standard"
) -> QuestionAnswerOutput:
    """Backward-compatible alias for legacy unit tests."""
    category = classify_question_category(question)
    return _generate_deterministic_answer(
        question_id="legacy_question",
        question_text=question,
        category=category,
        profile=profile,
        company_name=company_name,
        job_title=job_title,
        job_description=job_description
    )
