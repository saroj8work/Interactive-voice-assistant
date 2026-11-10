import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
openai_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

system_prompt = (
    "You are AuraAI, an advanced autonomous conversational AI lab assistant.\n"
    "You must decide actions using LLM intelligence. Respond strictly in JSON:\n"
    "{\n"
    '  "thought": "chain of thought",\n'
    '  "intent": "system_control | conversational_chat | file_note_management | calculation_math",\n'
    '  "action_required": true,\n'
    '  "planned_tools": [],\n'
    '  "ui_actions": [\n'
    '    {"action_type": "OPEN_MODAL | CLOSE_MODAL | APPEND_NOTE | ADD_REAGENT | CREATE_ENTRY | ADJUST_STOCK | CALCULATE_AND_INSERT", "target": "barcode_scanner | inventory | equipment | notebook_entry | tasks", "parameters": {}}\n'
    "  ],\n"
    '  "spoken_reply": "natural voice response"\n'
    "}"
)

tests = [
    "close the barcode scanner",
    "open barcode scanner",
    "what are the features you have",
    "record note: observed clear lysis at 56C",
    "add reagent 10X PBS Buffer 500 mL location Shelf B"
]

for q in tests:
    payload = {
        "model": "gemini-flash-lite-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    r = requests.post(openai_url, headers=headers, json=payload, timeout=8)
    print(f"\nQUERY: {q}")
    if r.status_code == 200:
        parsed = json.loads(r.json()["choices"][0]["message"]["content"])
        print("  Thought:   ", parsed.get("thought"))
        print("  Spoken:    ", parsed.get("spoken_reply"))
        print("  UI Actions:", parsed.get("ui_actions"))
    else:
        print("  Error:", r.status_code, r.text[:120])

