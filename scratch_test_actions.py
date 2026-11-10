import urllib.request
import json
import sys

commands = [
    "open reagent inventory",
    "open equipment booking",
    "search chemicals",
    "toggle dark theme",
    "open formal report",
    "open project tasks",
    "close modal"
]

print("Testing Action Commands against http://127.0.0.1:8010/api/conversation/chat ...\n")
for cmd in commands:
    payload = json.dumps({
        "message": cmd,
        "session_id": "test_actions_" + cmd.replace(" ", "_"),
        "generate_audio": False
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8010/api/conversation/chat",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"COMMAND: '{cmd}'")
            print(f"  Action Identified: {data.get('action_identified')}")
            print(f"  Intent:            {data.get('intent')}")
            print(f"  UI Actions:        {data.get('ui_actions')}")
            print(f"  Auth Status:       {data.get('authorization_status')}")
            print(f"  Spoken Reply:      {data.get('assistant_reply')}")
            print("-" * 60)
    except Exception as e:
        print(f"COMMAND '{cmd}' FAILED: {e}")

