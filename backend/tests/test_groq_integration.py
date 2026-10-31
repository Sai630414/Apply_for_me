import pytest
import os
from unittest.mock import patch
from app.core.config import settings
from app.services.llm_factory import get_llm, reset_llm
from app.services.ai_answer_service import (
    generate_answer,
    AI_GENERATED,
    NEEDS_USER_INPUT,
    DETERMINISTIC_PROFILE_MAPPING,
    LLM_AUTH_ERROR
)
from app.services.seeder_service import SAMPLE_USER_EMAIL, SAMPLE_USER_NAME


@pytest.fixture(autouse=True)
def ensure_groq_settings(monkeypatch):
    """Ensure tests run against Groq provider."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    reset_llm()
    yield
    reset_llm()


def test_groq_initialization():
    """Verify ChatGroq initializes with configured model and parameters."""
    reset_llm()
    llm = get_llm()
    assert llm is not None
    assert type(llm).__name__ == "ChatGroq"
    assert hasattr(llm, "model_name")
    assert getattr(settings, "LLM_PROVIDER") == "groq"


def test_ollama_fallback_preservation(monkeypatch):
    """Verify LLM_PROVIDER=ollama continues to initialize ChatOllama."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    reset_llm()
    llm = get_llm()
    assert llm is not None
    assert type(llm).__name__ == "ChatOllama"
    assert getattr(settings, "LLM_PROVIDER") == "ollama"


def test_missing_groq_api_key_raises_informative_error(monkeypatch):
    """Verify informative error if GROQ_API_KEY is empty when LLM_PROVIDER=groq."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    reset_llm()
    with pytest.raises(ValueError, match="GROQ_API_KEY must be provided"):
        get_llm()


@pytest.mark.asyncio
async def test_groq_direct_ainvoke():
    """Verify actual asynchronous ainvoke() call to Groq."""
    llm = get_llm()
    resp = await llm.ainvoke("Reply with exactly: PONG")
    content = resp.content if hasattr(resp, "content") else str(resp)
    assert len(content.strip()) > 0
    assert "PONG" in content.upper()


@pytest.mark.asyncio
async def test_groq_distinct_answers_for_different_questions():
    """Verify Groq generates tailored, distinct answers for different questions."""
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "skills": {"technicalSkills": ["Python", "FastAPI", "Docker", "MongoDB"]},
        "experiences": [
            {
                "company": "Tech Innovations Inc.",
                "role": "Software Engineer Intern",
                "technologies": ["Python", "FastAPI"],
                "description": "Architected asynchronous microservices."
            }
        ],
        "projects": [
            {
                "projectName": "ApplyForMe",
                "technologies": ["React", "FastAPI", "MongoDB"],
                "description": "AI job application autofill assistant extension."
            }
        ],
        "careerPreferences": {
            "availability": "Immediate",
            "employmentTypes": ["Internship", "Full-time"]
        }
    }

    # Q1: Motivation
    ans1 = await generate_answer(
        question_id="groq_q1",
        question_text="Why do you want to join Paytm?",
        field_type="textarea",
        applicant_profile=profile,
        company_name="Paytm",
        job_title="Software Development Engineer"
    )

    # Q2: Project Experience
    ans2 = await generate_answer(
        question_id="groq_q2",
        question_text="Describe a challenging technical project you built.",
        field_type="textarea",
        applicant_profile=profile,
        company_name="Paytm",
        job_title="Software Development Engineer"
    )

    assert ans1.status == "generated"
    assert ans1.execution_status == AI_GENERATED
    assert ans2.status == "generated"
    assert ans2.execution_status == AI_GENERATED

    # Ensure answers are completely distinct and question-specific
    assert ans1.answer != ans2.answer
    assert "Paytm" in ans1.answer or "payment" in ans1.answer.lower()
    assert "ApplyForMe" in ans2.answer or "FastAPI" in ans2.answer


@pytest.mark.asyncio
async def test_groq_factual_safeguards():
    """Verify factual constraints: unpaid internship -> NEEDS_USER_INPUT, recruitment exp -> No."""
    profile = {
        "personalInformation": {"fullName": "Sai Konda Reddy"},
        "experiences": [
            {
                "company": "Tech Innovations Inc.",
                "role": "Software Engineer Intern",
                "technologies": ["Python", "FastAPI"]
            }
        ],
        "careerPreferences": {"availability": "Immediate"}  # acceptUnpaid is None
    }

    # 1. Unpaid internship
    res_unpaid = await generate_answer(
        question_id="q_unpaid",
        question_text="Are you comfortable with an unpaid internship?",
        field_type="text",
        applicant_profile=profile
    )
    assert res_unpaid.status == "needs_user_input"
    assert res_unpaid.execution_status == NEEDS_USER_INPUT

    # 2. Recruitment experience check: software internship must not be claimed as recruitment experience
    res_rec = await generate_answer(
        question_id="q_recruitment",
        question_text="Do you have any prior recruitment internship experience?",
        field_type="text",
        applicant_profile=profile
    )
    assert res_rec.status == "generated"
    assert "No" in res_rec.answer
    assert "software engineering" in res_rec.answer.lower()


def test_provider_status_api_endpoint(client):
    """Verify GET /api/ai/provider-status returns provider info without exposing keys."""
    login_resp = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/ai/provider-status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "groq"
    assert data["model"] == settings.GROQ_MODEL
    assert data["configured"] is True
    assert data["status"] == "ready"
    assert "api_key" not in str(data).lower() or "configured" in data


def test_test_provider_connectivity_endpoint(client):
    """Verify POST /api/ai/test-provider exercises live ping without exposing keys."""
    login_resp = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/ai/test-provider", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["provider"] == "groq"
    assert data["latency_ms"] > 0
    assert "api_key" not in str(data).lower()


def test_autofill_map_fields_e2e_with_groq(client):
    """Verify POST /api/autofill/map-fields uses Groq and populates fields in parallel."""
    login_resp = client.post("/api/auth/dev-login", json={
        "email": SAMPLE_USER_EMAIL,
        "name": SAMPLE_USER_NAME
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    req_body = {
        "companyName": "Paytm",
        "jobTitle": "Backend Engineer",
        "jobDescription": "Build scalable distributed payment infrastructure.",
        "url": "https://jobs.lever.co/paytm/backend-engineer",
        "fields": [
            {"elementId": "full-name", "name": "fullName", "type": "text", "label": "Full Name"},
            {"elementId": "email-address", "name": "email", "type": "email", "label": "Email"},
            {"elementId": "why-paytm", "name": "whyJoin", "type": "textarea", "label": "Why do you want to join Paytm?"},
            {"elementId": "challenging-proj", "name": "project", "type": "textarea", "label": "Describe a challenging project."}
        ]
    }

    resp = client.post("/api/autofill/map-fields", json=req_body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["totalFields"] == 4
    by_id = {m["elementIdentifier"]: m for m in data["mappings"]}

    assert by_id["full-name"]["fillValue"] == "Sai Konda Reddy"
    assert by_id["why-paytm"]["category"] == "AI_GENERATED_ANSWER"
    assert by_id["why-paytm"]["fillValue"] is not None
    assert by_id["challenging-proj"]["category"] == "AI_GENERATED_ANSWER"
    assert by_id["challenging-proj"]["fillValue"] is not None
    assert by_id["why-paytm"]["fillValue"] != by_id["challenging-proj"]["fillValue"]

