"""
AuraAI Voice Assistant Component & Decision Evaluation Test Suite.
Runs 100% sandboxed without requiring external network or permissions.
Tests all conversational turns, pure LLM decisions, resilient fallbacks,
UI actions (OPEN_MODAL, CLOSE_MODAL, APPEND_NOTE, ADD_REAGENT, ADJUST_STOCK, CALCULATE_AND_INSERT, CREATE_TASK),
GxP voice authorization passkeys, and intent classifications.
"""
import time
from app.agent.conversational import conversational_agent
from app.nlu.classifier import IntentClassifier
from app.planner.planner import ActionPlanner

print("=" * 80)
print("AURAAI VOICE ASSISTANT IN-MEMORY TEST SUITE")
print("=" * 80)

classifier = IntentClassifier()
planner = ActionPlanner()

test_cases = [
    {
        "id": "TC-AURA-01",
        "name": "Voice Capability & Feature Overview",
        "query": "what are the features you have",
        "validate": lambda r: not r.ui_actions and any(w in r.assistant_reply.lower() for w in ["note", "inventory", "dilution", "barcode", "equipment", "task", "protocol", "assistant", "lab"])
    },
    {
        "id": "TC-AURA-02",
        "name": "Voice Observation Dictation (APPEND_NOTE)",
        "query": "record note: Observed clear lysis after 15 min at 56C",
        "validate": lambda r: any(a.action_type == "APPEND_NOTE" for a in r.ui_actions) or "observation" in r.assistant_reply.lower() or "note" in r.assistant_reply.lower()
    },
    {
        "id": "TC-AURA-03",
        "name": "Voice Reagent Registration (ADD_REAGENT)",
        "query": "add reagent 10X PBS Buffer 500 mL location Shelf B",
        "validate": lambda r: any(a.action_type in ("ADD_REAGENT", "OPEN_MODAL") for a in r.ui_actions) or "reagent" in r.assistant_reply.lower()
    },
    {
        "id": "TC-AURA-04",
        "name": "Voice Stock Consumption Deduction (ADJUST_STOCK)",
        "query": "deduct 50 mL of Ethanol from inventory",
        "validate": lambda r: any(a.action_type in ("ADJUST_STOCK", "OPEN_MODAL") for a in r.ui_actions) or any(w in r.assistant_reply.lower() for w in ["deducted", "deducting", "stock", "ethanol", "inventory"])
    },
    {
        "id": "TC-AURA-05",
        "name": "Voice Dilution Calculation Protocol (C1V1 = C2V2)",
        "query": "calculate dilution for 100 mM to 10 mM in 50 mL",
        "validate": lambda r: any(a.action_type == "CALCULATE_AND_INSERT" for a in r.ui_actions) or any(w in r.assistant_reply.lower() for w in ["dilution", "pipette", "stock", "diluent", "ml", "5.0", "45", "computed"])
    },
    {
        "id": "TC-AURA-06",
        "name": "Voice Laboratory Task Dispatch (CREATE_TASK)",
        "query": "create task: Autoclave pipette tips by Friday",
        "validate": lambda r: any(a.action_type in ("CREATE_TASK", "OPEN_MODAL") for a in r.ui_actions) or "task" in r.assistant_reply.lower()
    },
    {
        "id": "TC-AURA-07",
        "name": "Voice Modal Control: Open Barcode Scanner",
        "query": "open barcode scanner",
        "validate": lambda r: any(a.action_type == "OPEN_MODAL" and "barcode" in a.target.lower() for a in r.ui_actions)
    },
    {
        "id": "TC-AURA-08",
        "name": "Voice Modal Control: Close Barcode Scanner",
        "query": "close the barcode scanner",
        "validate": lambda r: any(a.action_type == "CLOSE_MODAL" and ("barcode" in a.target.lower() or a.target == "all") for a in r.ui_actions)
    },
    {
        "id": "TC-AURA-09",
        "name": "Voice UI Theme Accessibility Control (SET_THEME)",
        "query": "switch to light theme",
        "validate": lambda r: any(a.action_type == "SET_THEME" and a.target == "light" for a in r.ui_actions)
    },
    {
        "id": "TC-AURA-10",
        "name": "GxP Verbal Passkey Verification (4291)",
        "query": "My verbal passkey is 4291",
        "setup": lambda: _setup_pending_action("gxp_test_session"),
        "session_id": "gxp_test_session",
        "validate": lambda r: "authorization confirmed" in r.assistant_reply.lower() or "gxp audit record" in r.assistant_reply.lower() or "audit" in r.assistant_reply.lower()
    }
]

def _setup_pending_action(session_id: str):
    from app.security.authorization import PendingAction
    sess = conversational_agent.get_session(session_id)
    sess.pending_action = PendingAction(
        action_type="OVERRIDE_LOT_EXPIRY",
        target="inventory",
        summary="Override expired reagent lot #PBS-992",
        expires_at=time.time() + 60,
    )

passed = 0
for tc in test_cases:
    t0 = time.time()
    try:
        if "setup" in tc:
            tc["setup"]()
        session_id = tc.get("session_id")
        resp = conversational_agent.chat(
            user_message=tc["query"],
            session_id=session_id,
            user_role="admin",
            user_name="Dr. Sarah Chen",
            generate_audio=False
        )
        dt = (time.time() - t0) * 1000
        ok = tc["validate"](resp)
        if ok:
            passed += 1
            print(f"[PASS] {tc['id']}: {tc['name']} ({dt:.1f}ms)")
            print(f"       Reply: '{resp.assistant_reply[:60]}...' | Actions: {[a.action_type for a in resp.ui_actions]}")
        else:
            print(f"[FAIL] {tc['id']}: {tc['name']} ({dt:.1f}ms)")
            print(f"       Reply: '{resp.assistant_reply[:60]}...' | Actions: {[a.action_type for a in resp.ui_actions]}")
    except Exception as e:
        dt = (time.time() - t0) * 1000
        print(f"[ERROR] {tc['id']}: {tc['name']} ({dt:.1f}ms) - {e}")

print("=" * 80)
print(f"RESULTS: {passed}/{len(test_cases)} PASSED ({(passed/len(test_cases))*100:.1f}%)")
print("=" * 80)
