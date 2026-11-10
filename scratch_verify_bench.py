import urllib.request
import json

actions = [
    ("APPEND_NOTE", "Record note: Observed clear lysis after 15 minutes at 56 degrees"),
    ("ADD_REAGENT", "Add reagent 10X PBS Buffer, 500 mL, location Shelf B"),
    ("ADJUST_STOCK", "Deduct 50 mL of Ethanol"),
    ("CREATE_TASK", "Create task: Autoclave pipette tips by Friday"),
    ("CALCULATE_AND_INSERT", "Calculate dilution for 100 mM to 10 mM in 50 mL")
]

print("=" * 65)
print("VERIFYING BENCH SCIENTIST FORM-FILLING & DATA-ENTRY ENDPOINTS")
print("=" * 65)

for action_name, cmd in actions:
    payload = json.dumps({"message": cmd, "session_id": "bench_test", "generate_audio": False}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8010/api/conversation/chat", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"\nAction: {action_name}")
        print(f"  Command:     {cmd}")
        print(f"  Agent Reply: {data.get('assistant_reply')}")
        print(f"  UI Actions:  {data.get('ui_actions')}")

