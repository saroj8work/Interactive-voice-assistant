"""
Unit tests for Action Planner.
"""
from app.nlu.classifier import IntentClassifier
from app.planner.planner import ActionPlanner
from app.planner.schema import StepStatus


def test_single_action_plan():
    classifier = IntentClassifier()
    planner = ActionPlanner()

    res = classifier.classify("What is the weather in Berlin?")
    plan = planner.plan("What is the weather in Berlin?", res)

    assert plan.plan_id.startswith("plan_")
    assert plan.intent == "weather_query"
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "weather"
    assert plan.steps[0].parameters.get("location").lower() == "berlin"
    assert plan.steps[0].status == StepStatus.PENDING


def test_composite_action_plan():
    classifier = IntentClassifier()
    planner = ActionPlanner()

    cmd = "Calculate 15 * 4 and save note titled Work Expenses"
    res = classifier.classify(cmd)
    plan = planner.plan(cmd, res)

    assert plan.is_composite is True
    assert len(plan.steps) == 2
    assert plan.steps[0].tool_name == "calculator"
    assert plan.steps[1].tool_name == "note_manager"
    assert "step_1" in plan.steps[1].dependencies
