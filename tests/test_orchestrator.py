"""
Unit tests for End-to-End Voice Agent Orchestrator.
"""
from app.agent.orchestrator import orchestrator
from app.agent.llm_client import llm_client


def test_orchestrator_process_command():
    llm_client.set_mock_responses([
        {
            "thought": "Query London weather.",
            "intent": "weather_query",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "weather", "action_description": "Fetch London weather", "parameters": {"location": "London"}}
            ],
            "spoken_reply": "London weather retrieved.",
        }
    ])

    result = orchestrator.process_command(
        "What is the weather in London?", generate_audio=True
    )
    assert result.transcript == "What is the weather in London?"
    assert result.classification.intent == "weather_query"
    assert len(result.executed_steps) >= 1
    assert result.executed_steps[0]["status"] == "completed"
    assert len(result.final_response) > 0
    assert result.audio_base64 is not None
    assert result.execution_time_ms > 0


def test_orchestrator_composite_command():
    llm_client.set_mock_responses([
        {
            "thought": "Calculate 50 * 2 and save note.",
            "intent": "calculation_math",
            "action_required": True,
            "planned_tools": [
                {"tool_name": "calculator", "action_description": "Calculate 50 * 2", "parameters": {"expression": "50 * 2"}},
                {"tool_name": "note_manager", "action_description": "Save note", "parameters": {"action": "create", "title": "Test Calculation", "content": "100"}},
            ],
            "spoken_reply": "Calculated 100 and saved note.",
        }
    ])

    result = orchestrator.process_command(
        "Calculate 50 * 2 and save note titled Test Calculation",
        generate_audio=False,
    )
    assert result.plan.is_composite is True
    assert len(result.executed_steps) == 2
    assert result.executed_steps[0]["tool"] == "calculator"
    assert result.executed_steps[0]["status"] == "completed"
    assert result.executed_steps[1]["tool"] == "note_manager"
    assert result.executed_steps[1]["status"] == "completed"
