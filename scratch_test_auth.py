import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agent.conversational import conversational_agent
from app.security.authorization import UserRole

session_id = "test_auth_multiturn_flow"

print("Step 1: User requests privileged action: 'open formal report'")
turn1 = conversational_agent.chat(
    user_message="open formal report",
    session_id=session_id,
    generate_audio=False,
    user_role=UserRole.ANONYMOUS
)
print(f"  Auth Status: {turn1.authorization_status}")
print(f"  Spoken Reply: {turn1.assistant_reply}")
print(f"  UI Actions: {[a.model_dump() for a in turn1.ui_actions]}")

print("\nStep 2: User provides verbal authorization: 'authorize with passkey 4291'")
turn2 = conversational_agent.chat(
    user_message="authorize with passkey 4291",
    session_id=session_id,
    generate_audio=False,
    user_role=UserRole.ANONYMOUS
)
print(f"  Auth Status: {turn2.authorization_status}")
print(f"  Spoken Reply: {turn2.assistant_reply}")
print(f"  UI Actions: {[a.model_dump() for a in turn2.ui_actions]}")
print(f"  Audit Record: {turn2.audit_record}")

