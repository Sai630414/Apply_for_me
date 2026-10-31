import pytest
from app.services.ai_answer_service import (
    classify_question_category,
    generate_answer,
    _generate_deterministic_answer,
    QuestionAnswerOutput
)
from app.services.seeder_service import SAMPLE_USER_EMAIL, SAMPLE_USER_NAME


@pytest.mark.asyncio
async def test_independent_question_classification():
    """Verify each application question is independently classified into its proper category."""
    assert classify_question_category("Will you be available for a 3-month internship?") == "INTERNSHIP_DURATION"
    assert classify_question_category("Do you have prior recruitment internship experience?") == "PRIOR_EXPERIENCE"
    assert classify_question_category("Are you comfortable for an unpaid internship?") == "COMPENSATION_PREFERENCE"
    assert classify_question_category("Are you comfortable with an unpaid internship?") == "COMPENSATION_PREFERENCE"
    assert classify_question_category("Can you join us immediately?") == "JOINING_DATE"
    assert classify_question_category("Why do you want to join Paytm?") == "COMPANY_MOTIVATION"
    assert classify_question_category("Describe a challenging technical project you built") == "PROJECT_EXPERIENCE"
    assert classify_question_category("What are your core strengths and what makes you a suitable candidate?") == "STRENGTHS"


@pytest.mark.asyncio
async def test_question_1_internship_availability_with_profile():
    """
    Question 1: 'Will you be available for a 3-month internship?'
    Applicant profile has availability='Immediate' and employmentTypes=['Full-time', 'Internship'].
    Must generate a verified availability confirmation, NEVER a generic technical skills paragraph.
    """
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy", "email": "sai@example.com"},
        "skills": {"programmingLanguages": ["Python", "TypeScript", "JavaScript", "Go"]},
        "careerPreferences": {
            "availability": "Immediate",
            "employmentTypes": ["Full-time", "Internship"]
        }
    }

    res = await generate_answer(
        question_id="avail_q1",
        question_text="Will you be available for a 3-month internship?",
        field_type="text",
        applicant_profile=profile,
        company_name="Paytm",
        job_title="Software Development Engineer"
    )

    assert res.question_id == "avail_q1"
    assert res.status == "generated"
    assert res.answer is not None
    assert "available for a 3-month internship" in res.answer.lower()
    # Critical: Must NOT be the generic skills paragraph!
    assert "solid engineering foundation in python" not in res.answer.lower()


@pytest.mark.asyncio
async def test_question_1_internship_availability_missing_requires_input():
    """If availability is missing, must return status='needs_user_input'."""
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "careerPreferences": {}
    }

    res = await generate_answer(
        question_id="avail_q_missing",
        question_text="Will you be available for a 3-month internship?",
        field_type="text",
        applicant_profile=profile
    )

    assert res.status == "needs_user_input"
    assert res.answer is None
    assert res.confidence == 0.0


@pytest.mark.asyncio
async def test_question_2_prior_recruitment_experience_truthful_negative():
    """
    Question 2: 'Do you have prior recruitment internship experience?'
    Applicant has software engineering experience at Tech Innovations Inc., but NO recruitment experience.
    Must truthfully state they do NOT have recruitment experience, never invent an internship.
    """
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "skills": {"programmingLanguages": ["Python", "TypeScript"]},
        "experiences": [
            {
                "company": "Tech Innovations Inc.",
                "role": "Software Engineer Intern",
                "description": "Architected microservices in Python."
            }
        ]
    }

    res = await generate_answer(
        question_id="exp_q2",
        question_text="Do you have prior recruitment internship experience?",
        field_type="textarea",
        applicant_profile=profile,
        company_name="Paytm",
        job_title="Software Development Engineer"
    )

    assert res.question_id == "exp_q2"
    assert res.status == "generated"
    assert res.answer is not None
    # Must truthfully state lack of recruitment experience and mention verified software engineering
    assert "no, i do not have prior recruitment" in res.answer.lower() or "do not have prior experience in recruitment" in res.answer.lower()
    assert "tech innovations" in res.answer.lower() or "software" in res.answer.lower()
    assert "solid engineering foundation in python" not in res.answer.lower()


@pytest.mark.asyncio
async def test_question_3_unpaid_internship_requires_user_input():
    """
    Question 3: 'Are you comfortable for an unpaid internship?'
    This is a personal preference. When not confirmed in profile, MUST return needs_user_input.
    Never assume consent for unpaid work and never generate a generic paragraph.
    """
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "careerPreferences": {
            "expectedSalary": "$120,000"
            # No acceptUnpaid
        }
    }

    res = await generate_answer(
        question_id="unpaid_q3",
        question_text="Are you comfortable for an unpaid internship?",
        field_type="text",
        applicant_profile=profile,
        company_name="Paytm"
    )

    assert res.question_id == "unpaid_q3"
    assert res.category == "COMPENSATION_PREFERENCE"
    assert res.status == "needs_user_input"
    assert res.answer is None
    assert res.confidence == 0.0
    assert "unpaid" in res.reason.lower()


@pytest.mark.asyncio
async def test_question_4_immediate_joining():
    """
    Question 4: 'Can you join us immediately?'
    With availability='Immediate', must return confirmed joining answer.
    """
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "careerPreferences": {
            "availability": "Immediate"
        }
    }

    res = await generate_answer(
        question_id="join_q4",
        question_text="Can you join us immediately?",
        field_type="text",
        applicant_profile=profile
    )

    assert res.question_id == "join_q4"
    assert res.status == "generated"
    assert res.answer is not None
    assert "join immediately" in res.answer.lower()
    assert "solid engineering foundation in python" not in res.answer.lower()


def test_e2e_autofill_map_fields_four_questions_pipeline(client):
    """
    End-to-end integration test against /api/autofill/map-fields simulating all 4 Paytm questions
    and verifying each question receives its own distinct, truthful answer or status.
    """
    # 1. Dev login
    login_resp = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit all 4 questions
    payload = {
        "companyName": "Paytm",
        "jobTitle": "Software Development Engineer (Backend)",
        "fields": [
            {"elementId": "q1-avail", "name": "avail3Months", "type": "text", "label": "Will you be available for 3 months internship?"},
            {"elementId": "q2-exp", "name": "priorRecruitmentExp", "type": "textarea", "label": "Do you have any prior recruitment internship experience?"},
            {"elementId": "q3-unpaid", "name": "unpaidComfortable", "type": "text", "label": "Are you comfortable for an unpaid internship?"},
            {"elementId": "q4-immediate", "name": "joinImmediately", "type": "text", "label": "Can you join us immediately?"},
            {"elementId": "q5-why-paytm", "name": "whyPaytm", "type": "textarea", "label": "Why do you want to join Paytm?"}
        ]
    }

    resp = client.post("/api/autofill/map-fields", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    mappings = {m["elementIdentifier"]: m for m in data["mappings"]}

    # Q1: Available for 3 months
    q1 = mappings["q1-avail"]
    assert q1["fillValue"] is not None
    assert "available for a 3-month internship" in q1["fillValue"].lower()

    # Q2: Prior recruitment experience (truthful negative)
    q2 = mappings["q2-exp"]
    assert q2["fillValue"] is not None
    assert "no, i do not have prior recruitment" in q2["fillValue"].lower() or "do not have prior experience in recruitment" in q2["fillValue"].lower()

    # Q3: Unpaid internship (MUST be USER_INPUT_REQUIRED, NEVER filled!)
    q3 = mappings["q3-unpaid"]
    assert q3["category"] == "USER_INPUT_REQUIRED"
    assert q3["fillValue"] is None
    assert q3["requiresReview"] is True

    # Q4: Immediate joining
    q4 = mappings["q4-immediate"]
    assert q4["fillValue"] is not None
    assert "join immediately" in q4["fillValue"].lower()

    # Q5: Why Paytm (company motivation)
    q5 = mappings["q5-why-paytm"]
    assert q5["fillValue"] is not None
    assert "paytm" in q5["fillValue"].lower()

    # CRITICAL: Verify NO two answers are identical! Every question received a distinct answer!
    filled_answers = [m["fillValue"] for m in mappings.values() if m["fillValue"]]
    assert len(filled_answers) == len(set(filled_answers)), "Detected duplicate answers across unrelated questions!"

