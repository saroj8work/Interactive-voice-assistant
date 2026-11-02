"""
Direct unit tests for FastAPI REST API endpoints and routes.
"""
import pytest
from fastapi import HTTPException

from main import root
from app.agent.llm_client import llm_client
from app.config import settings
from app.api.routes import (
    health_check,
    get_model_config,
    update_model_config,
    classify_intent,
    create_action_plan,
    execute_command,
    conversational_chat,
    pydantic_plan_and_classify,
    list_tools,
    list_timers,
    text_to_speech,
    get_domain_knowledge,
    query_domain_knowledge,
    ClassifyRequest,
    PlanRequest,
    CommandRequest,
    ChatRequest,
    TTSRequest,
    KnowledgeQueryRequest,
    ModelConfigUpdateRequest,
)


def test_root_endpoint():
    res = root()
    assert res["status"] == "operational"
    assert res["docs"] == "/docs"
    assert "health" in res["endpoints"]
    assert "model_config" in res["endpoints"]


def test_health_endpoint():
    res = health_check()
    assert res["status"] == "healthy"
    assert res["ready"] is True


def test_model_config_endpoints():
    info = get_model_config()
    assert "model_provider" in info
    assert "configured" in info

    # Test updating model credentials
    update_req = ModelConfigUpdateRequest(
        model_provider="groq",
        model_name="llama-3.3-70b-versatile",
        groq_api_key="gsk_test_mock_key_123",
    )
    res = update_model_config(update_req)
    assert res["status"] == "updated"
    assert res["model_provider"] == "groq"
    assert res["model_name"] == "llama-3.3-70b-versatile"
    assert res["configured"] is True


def test_conversational_chat_endpoint():
    llm_client.set_mock_responses([
        {
            "thought": "User asks for Paris weather.",
            "intent": "weather_query",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "weather", "action_description": "Get weather for Paris", "parameters": {"location": "Paris"}}
            ],
            "spoken_reply": "The weather in Paris is partly cloudy.",
        }
    ])

    req = ChatRequest(message="Can you tell me the weather in Paris?", generate_audio=False)
    res = conversational_chat(req)
    assert res.action_identified is True
    assert res.intent == "weather_query"
    assert "Paris" in res.assistant_reply


def test_command_execution_endpoint():
    llm_client.set_mock_responses([
        {
            "thought": "Calculate 100 / 4.",
            "intent": "calculation_math",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "calculator", "action_description": "Calculate 100 / 4", "parameters": {"expression": "100 / 4"}}
            ],
            "spoken_reply": "Calculation complete.",
        }
    ])

    req = CommandRequest(command="Calculate 100 / 4", generate_audio=False)
    res = execute_command(req)
    assert res.classification.intent == "calculation_math"
    assert len(res.executed_steps) == 1
    assert res.executed_steps[0]["status"] == "completed"
    assert res.executed_steps[0]["data"]["result"] == 25


def test_pydantic_agent_endpoint():
    llm_client.set_mock_responses([
        {
            "thought": "Tokyo weather query.",
            "intent": "weather_query",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "weather", "action_description": "Fetch weather in Tokyo", "parameters": {"location": "Tokyo"}}
            ],
            "spoken_reply": "Tokyo weather retrieved.",
        }
    ])

    req = CommandRequest(command="What's the weather in Tokyo?", generate_audio=False)
    res = pydantic_plan_and_classify(req)
    assert res.intent == "weather_query"
    assert len(res.steps) == 1


def test_tts_endpoint():
    req = TTSRequest(text="Spoken test", format="base64")
    res = text_to_speech(req)
    assert "audio_base64" in res
    assert len(res["audio_base64"]) > 0


def test_tools_endpoint():
    res = list_tools()
    tool_names = [t["name"] for t in res["tools"]]
    assert "weather" in tool_names
    assert "calculator" in tool_names
    assert "system" in tool_names
    assert "note_manager" in tool_names
    assert "timer_manager" in tool_names
    assert "knowledge_search" in tool_names


def test_timers_endpoint():
    res = list_timers()
    assert "timers" in res


def test_domain_knowledge_endpoint():
    res = get_domain_knowledge()
    assert res["total_sections"] > 0
    assert len(res["sections"]) > 0


def test_domain_knowledge_query_endpoint():
    req = KnowledgeQueryRequest(query="refund policy", top_k=2)
    res = query_domain_knowledge(req)
    assert res.found is True
    assert "refund" in res.answer.lower()
