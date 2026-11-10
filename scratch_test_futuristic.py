import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agent.conversational import conversational_agent
from app.security.authorization import UserRole

commands = [
    "Record note: Observed complete cell lysis after 15 minutes at 56 degrees",
    "Add reagent 10X PBS Buffer, 500 mL, lot 9942, location Shelf B",
    "Deduct 50 mL of Ethanol",
    "Create task: Autoclave pipette tips by Friday",
    "Calculate dilution for 100 mM to 10 mM in 50 mL",
    "Create new entry: Western Blot Validation Assay",
    "Open reagent inventory",
]

print("Testing Futuristic Bench Scientist Voice Actions:\n")
for cmd in commands:
    turn = conversational_agent.chat(
        user_message=cmd,
        session_id="test_futuristic",
        generate_audio=False,
        user_role=UserRole.ANONYMOUS
    )
    print(f"COMMAND: '{cmd}'")
    print(f"  Action Identified: {turn.action_identified}")
    print(f"  Spoken Reply:      {turn.assistant_reply}")
    print(f"  UI Actions:        {[a.model_dump() for a in turn.ui_actions]}")
    print("-" * 65)

