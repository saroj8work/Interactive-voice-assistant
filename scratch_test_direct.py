import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agent.conversational import conversational_agent
from app.security.authorization import UserRole

commands = [
    "open reagent inventory",
    "open equipment booking",
    "search chemicals",
    "toggle dark theme",
    "open formal report",
    "open project tasks",
    "close modal"
]

print("Directly testing ConversationalAgent action parsing & execution:\n")
for cmd in commands:
    try:
        turn = conversational_agent.chat(
            user_message=cmd,
            session_id="test_direct_" + cmd.replace(" ", "_"),
            generate_audio=False,
            user_role=UserRole.ANONYMOUS
        )
        print(f"COMMAND: '{cmd}'")
        print(f"  Action Identified: {turn.action_identified}")
        print(f"  Intent:            {turn.intent}")
        print(f"  UI Actions:        {[a.model_dump() for a in turn.ui_actions]}")
        print(f"  Auth Status:       {turn.authorization_status}")
        print(f"  Spoken Reply:      {turn.assistant_reply}")
        print("-" * 60)
    except Exception as e:
        print(f"COMMAND '{cmd}' ERROR: {e}")
