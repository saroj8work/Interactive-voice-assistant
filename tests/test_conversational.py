"""
Unit tests for Purely LLM-Driven Conversational Voice Agent.
"""
from app.agent.conversational import conversational_agent, ConversationalTurnResponse
from app.agent.llm_client import llm_client


def test_conversational_greeting_with_llm():
    # Mock LLM decision for casual greeting
    llm_client.set_mock_responses([
        {
            "thought": "User is greeting casually, no tools needed.",
            "intent": "conversational_chat",
            "action_required": False,
            "planned_tools": [],
            "spoken_reply": "Hello! It's great to speak with you today. How can I help you?",
        }
    ])

    res = conversational_agent.chat(
        "Hi there, how are you today?",
        session_id="llm_session_greeting",
        generate_audio=False,
    )
    assert isinstance(res, ConversationalTurnResponse)
    assert res.action_identified is False
    assert "Hello" in res.assistant_reply


def test_conversational_action_identification_with_llm():
    # Mock LLM decision for weather query action
    llm_client.set_mock_responses([
        {
            "thought": "User wants weather forecast for Tokyo. Needs weather tool.",
            "intent": "weather_query",
            "action_required": True,
            "planned_tools": [
                {
                    "tool_name": "weather",
                    "action_description": "Fetch weather for Tokyo",
                    "parameters": {"location": "Tokyo"},
                }
            ],
            "spoken_reply": "The current weather in Tokyo has been retrieved.",
        }
    ])

    res = conversational_agent.chat(
        "I need to know the weather in Tokyo please",
        session_id="llm_session_action",
        generate_audio=True,
    )
    assert isinstance(res, ConversationalTurnResponse)
    assert res.action_identified is True
    assert res.intent == "weather_query"
    assert len(res.executed_tools) == 1
    assert res.executed_tools[0]["tool"] == "weather"
    assert res.audio_base64 is not None


def test_conversational_multi_turn_with_llm():
    # Turn 1: Weather query
    llm_client.set_mock_responses([
        {
            "thought": "Query weather for London.",
            "intent": "weather_query",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "weather", "action_description": "Get London weather", "parameters": {"location": "London"}}
            ],
            "spoken_reply": "Here is the London weather report.",
        },
        # Turn 2: Follow-up note
        {
            "thought": "User refers to 'that' (London weather) to save as note.",
            "intent": "file_note_management",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "note_manager", "action_description": "Save note", "parameters": {"action": "create", "title": "London trip", "content": "London weather"}}
            ],
            "spoken_reply": "I've saved that as a note for your London trip.",
        }
    ])

    res1 = conversational_agent.chat("What is the weather in London?", session_id="llm_multi_turn", generate_audio=False)
    assert res1.action_identified is True

    res2 = conversational_agent.chat("Please save that as a note titled London trip", session_id="llm_multi_turn", generate_audio=False)
    assert res2.action_identified is True
    assert res2.intent == "file_note_management"
    assert len(res2.executed_tools) == 1
    assert res2.executed_tools[0]["tool"] == "note_manager"
