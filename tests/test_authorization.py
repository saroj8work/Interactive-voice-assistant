"""
Unit tests for Futuristic Voice Identity, Multi-Turn Action Authorization,
and 21 CFR Part 11 Cryptographic Audit Trails.
"""
import pytest
from app.agent.conversational import conversational_agent
from app.agent.llm_client import llm_client, LLMAgentDecision, PlannedToolCall, UIAction
from app.security.authorization import (
    action_authorizer,
    UserRole,
    ActionSeverity,
    PendingAction,
)


@pytest.fixture(autouse=True)
def reset_sessions():
    conversational_agent.sessions.clear()
    action_authorizer.audit_log.clear()


def test_classify_action_severity():
    # Safe actions
    assert action_authorizer.classify_action_severity("OPEN_MODAL", "inventory", {}) == ActionSeverity.SAFE
    assert action_authorizer.classify_action_severity("OPEN_MODAL", "equipment", {}) == ActionSeverity.SAFE
    assert action_authorizer.classify_action_severity("SET_THEME", "dark", {}) == ActionSeverity.SAFE

    # Privileged actions
    assert action_authorizer.classify_action_severity("TRIGGER_BUTTON", "formal_report_submit", {}) == ActionSeverity.PRIVILEGED
    assert action_authorizer.classify_action_severity("DELETE", "sample_batch_402", {}) == ActionSeverity.PRIVILEGED
    assert action_authorizer.classify_action_severity("TRIGGER_BUTTON", "purge_inventory", {}) == ActionSeverity.PRIVILEGED


def test_safe_action_executes_freely_for_anyone():
    """Any speaker in the room can navigate and ask questions without challenge."""
    llm_client.set_mock_responses([
        {
            "thought": "User wants to open reagent inventory.",
            "intent": "system_control",
            "action_required": True,
            "planned_tools": [],
            "ui_actions": [
                {"action_type": "OPEN_MODAL", "target": "inventory", "parameters": {}}
            ],
            "spoken_reply": "Opening the inventory manager now."
        }
    ])

    response = conversational_agent.chat(
        user_message="Open the reagent inventory",
        session_id="test_sess_safe",
        generate_audio=False,
        user_role=UserRole.ANONYMOUS,
    )

    assert response.authorization_status == "NONE"
    assert len(response.ui_actions) == 1
    assert response.ui_actions[0].target == "inventory"
    assert "Opening the inventory" in response.assistant_reply


def test_privileged_action_intercepted_for_anonymous_speaker():
    """When an unauthorized speaker requests a privileged action, challenge is issued."""
    llm_client.set_mock_responses([
        {
            "thought": "User requested formal report submission.",
            "intent": "system_control",
            "action_required": True,
            "planned_tools": [],
            "ui_actions": [
                {"action_type": "TRIGGER_BUTTON", "target": "formal_report_submit", "parameters": {}}
            ],
            "spoken_reply": "Submitting the formal report."
        }
    ])

    response = conversational_agent.chat(
        user_message="Submit the final formal report for Experiment 104",
        session_id="test_sess_priv",
        generate_audio=False,
        user_role=UserRole.ANONYMOUS,
        user_name="Lab Guest",
    )

    # UI action MUST be withheld!
    assert response.authorization_status == "CHALLENGE_ISSUED"
    assert len(response.ui_actions) == 0
    assert "requires Project Administrator authorization" in response.assistant_reply

    # Session now holds pending action
    session = conversational_agent.sessions["test_sess_priv"]
    assert session.pending_action is not None
    assert session.pending_action.target == "formal_report_submit"


def test_multi_turn_authorization_rejection_on_wrong_passkey():
    """Second turn: unauthorized speaker fails challenge -> action safely cancelled."""
    # Step 1: Issue challenge
    llm_client.set_mock_responses([
        {
            "thought": "Purge sample requested",
            "intent": "system_control",
            "action_required": True,
            "planned_tools": [],
            "ui_actions": [
                {"action_type": "TRIGGER_BUTTON", "target": "purge_inventory", "parameters": {}}
            ],
            "spoken_reply": "Purging inventory."
        }
    ])

    turn1 = conversational_agent.chat(
        user_message="Purge old inventory samples",
        session_id="test_sess_reject",
        generate_audio=False,
        user_role=UserRole.MEMBER,
    )
    assert turn1.authorization_status == "CHALLENGE_ISSUED"
    assert len(turn1.ui_actions) == 0

    # Step 2: Speaker says invalid code or 'cancel'
    turn2 = conversational_agent.chat(
        user_message="Just do it, or cancel",
        session_id="test_sess_reject",
        generate_audio=False,
    )

    assert turn2.authorization_status == "REJECTED"
    assert len(turn2.ui_actions) == 0
    assert "safely cancelled" in turn2.assistant_reply

    # Session pending action cleared
    session = conversational_agent.sessions["test_sess_reject"]
    assert session.pending_action is None


def test_multi_turn_authorization_success_with_passkey_and_audit():
    """Second turn: Admin provides verbal passkey -> action executes with GxP audit record."""
    # Step 1: Issue challenge
    llm_client.set_mock_responses([
        {
            "thought": "Submit formal report",
            "intent": "system_control",
            "action_required": True,
            "planned_tools": [],
            "ui_actions": [
                {"action_type": "TRIGGER_BUTTON", "target": "formal_report_submit", "parameters": {}}
            ],
            "spoken_reply": "Submitting report."
        }
    ])

    turn1 = conversational_agent.chat(
        user_message="Submit the final formal report",
        session_id="test_sess_approve",
        generate_audio=False,
        user_role=UserRole.ANONYMOUS,
        user_name="Junior Researcher",
    )
    assert turn1.authorization_status == "CHALLENGE_ISSUED"
    assert len(turn1.ui_actions) == 0

    # Step 2: Admin provides verbal passkey ('4291')
    turn2 = conversational_agent.chat(
        user_message="This is the project admin, authorize with passkey 4291",
        session_id="test_sess_approve",
        generate_audio=False,
        user_name="Dr. Sarah Chen",
    )

    assert turn2.authorization_status == "AUTHORIZED"
    assert len(turn2.ui_actions) == 1
    assert turn2.ui_actions[0].target == "formal_report_submit"
    assert "Authorization confirmed" in turn2.assistant_reply

    # Verify 21 CFR Part 11 GxP Audit Record
    assert turn2.audit_record is not None
    assert turn2.audit_record.authorization_method == "VERBAL_PASSKEY"
    assert turn2.audit_record.target == "formal_report_submit"
    assert len(turn2.audit_record.digital_signature_hash) == 64 # SHA-256 hex string


def test_preauthenticated_admin_executes_directly_with_audit():
    """If user is already authenticated as ADMIN, privileged action runs with immediate audit log."""
    llm_client.set_mock_responses([
        {
            "thought": "Admin requested report submission",
            "intent": "system_control",
            "action_required": True,
            "planned_tools": [],
            "ui_actions": [
                {"action_type": "TRIGGER_BUTTON", "target": "formal_report_submit", "parameters": {}}
            ],
            "spoken_reply": "Executing formal report submission."
        }
    ])

    response = conversational_agent.chat(
        user_message="Submit the formal report",
        session_id="test_admin_direct",
        generate_audio=False,
        user_role=UserRole.ADMIN,
        user_name="Dr. Sarah Chen",
    )

    assert response.authorization_status == "AUTHORIZED"
    assert len(response.ui_actions) == 1
    assert response.audit_record is not None
    assert response.audit_record.authorized_by == "Dr. Sarah Chen"

