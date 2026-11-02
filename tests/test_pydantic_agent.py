"""
Unit tests for PydanticAI-structured LLM Voice Assistant Agent.
"""
from app.agent.pydantic_agent import pydantic_voice_agent, VoiceAgentClassificationAndPlan
from app.agent.llm_client import llm_client
from app.nlu.models import IntentType


def test_pydantic_agent_weather_with_llm():
    llm_client.set_mock_responses([
        {
            "thought": "User asks for Paris weather. Requires weather tool.",
            "intent": "weather_query",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "weather", "action_description": "Fetch weather in Paris", "parameters": {"location": "Paris"}}
            ],
            "spoken_reply": "Here is the weather in Paris.",
        }
    ])

    result = pydantic_voice_agent.plan_and_classify("What's the weather like in Paris?")
    assert isinstance(result, VoiceAgentClassificationAndPlan)
    assert result.intent == IntentType.WEATHER_QUERY
    assert len(result.steps) == 1
    assert result.steps[0].tool_name == "weather"
    assert result.steps[0].parameters.get("location") == "Paris"


def test_pydantic_agent_composite_with_llm():
    llm_client.set_mock_responses([
        {
            "thought": "Composite request: calculate math and then create a note.",
            "intent": "calculation_math",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "calculator", "action_description": "Calculate 25 * 4", "parameters": {"expression": "25 * 4"}},
                {"tool_name": "note_manager", "action_description": "Save to note Budget", "parameters": {"action": "create", "title": "Budget", "content": "100"}},
            ],
            "spoken_reply": "Calculated 100 and saved to note Budget.",
        }
    ])

    result = pydantic_voice_agent.plan_and_classify("Calculate 25 * 4 and save note titled Budget")
    assert isinstance(result, VoiceAgentClassificationAndPlan)
    assert result.is_composite is True
    assert len(result.steps) == 2
    assert result.steps[0].tool_name == "calculator"
    assert result.steps[1].tool_name == "note_manager"
