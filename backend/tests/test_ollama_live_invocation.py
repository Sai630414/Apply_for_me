import pytest
import asyncio
import time
from langchain_ollama import ChatOllama
from app.services.ai_answer_service import (
    generate_answer,
    classify_question_category,
    AI_GENERATED,
    NEEDS_USER_INPUT,
    DETERMINISTIC_PROFILE_MAPPING,
    LLM_TIMEOUT,
    LLM_CONNECTION_ERROR
)
from app.core.config import settings
from app.services.seeder_service import SAMPLE_USER_EMAIL, SAMPLE_USER_NAME


@pytest.mark.asyncio
async def test_direct_chat_ollama_invocation():
    """Requirement 3: Confirm direct ChatOllama model invocation works with non-empty content."""
    llm = ChatOllama(
        model=getattr(settings, "OLLAMA_MODEL", "qwen2.5:3b"),
        base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.4,
        client_kwargs={"timeout": 120.0},
        async_client_kwargs={"timeout": 120.0}
    )
    t0 = time.time()
    response = await llm.ainvoke("Answer in one sentence: Why do you want to join Paytm?")
    duration = time.time() - t0

    assert response is not None
    assert response.content is not None
    assert len(response.content.strip()) > 10
    print(f"\n[Test] Direct ChatOllama response in {duration:.2f}s: {response.content.strip()[:100]}...")


@pytest.mark.asyncio
async def test_langchain_service_ai_generation():
    """Verify generate_answer invokes Ollama and returns AI_GENERATED with structured output."""
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy", "email": "sai@example.com"},
        "skills": {
            "programmingLanguages": ["Python", "TypeScript", "Go"],
            "frameworks": ["FastAPI", "React", "Docker"]
        },
        "projects": [
            {
                "projectName": "ApplyForMe",
                "description": "AI-powered job application assistant",
                "technologies": ["Python", "FastAPI", "React"]
            }
        ],
        "careerPreferences": {
            "availability": "Immediate",
            "employmentTypes": ["Full-time", "Internship"]
        }
    }

    res = await generate_answer(
        question_id="why_paytm_01",
        question_text="Why do you want to join Paytm?",
        field_type="textarea",
        applicant_profile=profile,
        company_name="Paytm",
        job_title="Software Development Engineer (Backend)"
    )

    assert res.question_id == "why_paytm_01"
    assert res.status == "generated"
    assert res.answer is not None
    assert len(res.answer.strip()) > 20
    assert res.execution_status == AI_GENERATED
    assert res.confidence >= 0.85
    print(f"\n[Test] Generated AI Answer: {res.answer[:120]}...")


@pytest.mark.asyncio
async def test_missing_personal_preference_returns_needs_user_input():
    """Verify unknown personal preference (unpaid internship) returns NEEDS_USER_INPUT."""
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "careerPreferences": {}  # No acceptUnpaid
    }

    res = await generate_answer(
        question_id="unpaid_test_01",
        question_text="Are you comfortable for an unpaid internship?",
        field_type="text",
        applicant_profile=profile,
        company_name="Paytm"
    )

    assert res.question_id == "unpaid_test_01"
    assert res.status == "needs_user_input"
    assert res.answer is None
    assert res.confidence == 0.0
    assert res.execution_status == NEEDS_USER_INPUT


@pytest.mark.asyncio
async def test_confirmed_availability_deterministic_mapping():
    """Verify confirmed availability returns DETERMINISTIC_PROFILE_MAPPING without hitting LLM."""
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "careerPreferences": {"availability": "Immediate", "employmentTypes": ["Internship"]}
    }

    res = await generate_answer(
        question_id="avail_test_01",
        question_text="Will you be available for a 3-month internship?",
        field_type="text",
        applicant_profile=profile
    )

    assert res.status == "generated"
    assert res.answer is not None
    assert res.execution_status == DETERMINISTIC_PROFILE_MAPPING


@pytest.mark.asyncio
async def test_ollama_unavailable_graceful_handling(monkeypatch):
    """Verify that when Ollama is unreachable, LLM_CONNECTION_ERROR is logged and handled safely."""
    # Point to an invalid port to simulate offline Ollama
    invalid_llm = ChatOllama(
        model="qwen2.5:3b",
        base_url="http://localhost:59999",
        client_kwargs={"timeout": 1.0},
        async_client_kwargs={"timeout": 1.0}
    )
    import app.services.ai_answer_service as ai_svc
    monkeypatch.setattr(ai_svc, "get_llm", lambda: invalid_llm)
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 1.0)

    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "skills": {"technicalSkills": ["Python", "FastAPI"]}
    }

    res = await generate_answer(
        question_id="offline_test",
        question_text="Why do you want to join Paytm?",
        field_type="textarea",
        applicant_profile=profile,
        company_name="Paytm"
    )

    assert res.question_id == "offline_test"
    # Fallback response is marked with explicit offline/unavailable status
    assert res.execution_status in ("LLM_UNAVAILABLE", "LLM_CONNECTION_ERROR", "LLM_TIMEOUT")


def test_autofill_map_fields_e2e_with_ollama(client):
    """Verify POST /api/autofill/map-fields generates answers and returns AI answers correctly."""
    login_resp = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "companyName": "Paytm",
        "jobTitle": "Software Development Engineer (Backend)",
        "fields": [
            {"elementId": "field_why", "name": "whyPaytm", "type": "textarea", "label": "Why do you want to join Paytm?"},
            {"elementId": "field_unpaid", "name": "unpaid", "type": "text", "label": "Are you comfortable for an unpaid internship?"},
            {"elementId": "field_avail", "name": "availability", "type": "text", "label": "Will you be available for 3 months internship?"}
        ]
    }

    resp = client.post("/api/autofill/map-fields", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    mappings = {m["elementIdentifier"]: m for m in data["mappings"]}

    # Contextual question (Ollama generation)
    m_why = mappings["field_why"]
    assert m_why["fillValue"] is not None
    assert len(m_why["fillValue"]) > 20
    assert m_why["category"] == "AI_GENERATED_ANSWER"

    # Unknown personal preference
    m_unpaid = mappings["field_unpaid"]
    assert m_unpaid["category"] == "USER_INPUT_REQUIRED"
    assert m_unpaid["fillValue"] is None

    # Availability
    m_avail = mappings["field_avail"]
    assert m_avail["fillValue"] is not None
    assert "available for a 3-month internship" in m_avail["fillValue"].lower()

