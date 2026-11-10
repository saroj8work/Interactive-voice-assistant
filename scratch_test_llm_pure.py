import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={key}"

system_prompt = """You are AuraAI, an intelligent conversational AI agent embedded directly into a modern Electronic Lab Notebook (ELN).
You must analyze the user's laboratory and application requests purely using LLM reasoning and decide actions.
Respond strictly in JSON matching this schema:
{
  "thought": "brief reasoning explaining intent and chosen action",
  "intent": "system_control | conversational_chat | file_note_management | calculation_math | web_search_knowledge",
  "action_required": true,
  "planned_tools": [],
  "ui_actions": [
    {
      "action_type": "OPEN_MODAL | CLOSE_MODAL | APPEND_NOTE | ADD_REAGENT | CREATE_ENTRY | ADJUST_STOCK | CALCULATE_AND_INSERT | SET_THEME | TOGGLE_SIDEBAR",
      "target": "barcode_scanner | inventory | equipment | tasks | templates | locations | history | notebook_entry | dark | light",
      "parameters": {}
    }
  ],
  "spoken_reply": "warm, concise natural spoken response"
}

Behavior Guidelines:
- If user asks to open something (e.g., 'open barcode scanner', 'show inventory'), emit OPEN_MODAL with the target.
- If user asks to close, dismiss, or exit something (e.g., 'close barcode scanner', 'exit modal'), emit CLOSE_MODAL with the target.
- If user asks about your features or capabilities ('what are the features you have', 'what can you do'), set action_required=false, ui_actions=[], and summarize: you assist bench scientists with hands-free observation logging, protocol note creation, chemical & reagent inventory tracking, dilution calculations, barcode scanning, and equipment booking.
- If user dictates a note or observation ('record note: ...', 'note down: ...'), emit APPEND_NOTE with the observation text.
- If user registers a reagent ('add reagent 10X PBS 500 mL'), emit ADD_REAGENT with parsed name, quantity, unit, lot, location.
- If user asks to calculate a dilution, emit CALCULATE_AND_INSERT with markdown dilution protocol table.
"""

tests = [
    "close the barcode scanner",
    "open barcode scanner",
    "what are the features you have",
    "record note: observed clear lysis after 15 min at 56C",
    "add reagent 10X PBS Buffer 500 mL location Shelf B"
]

print("=" * 65)
print("TESTING 100% PURE LLM DECISION MAKING (gemini-3-flash-preview)")
print("=" * 65)

for q in tests:
    t0 = time.time()
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{system_prompt}\n\nUser request: {q}"}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }
    r = requests.post(url, json=payload, timeout=8)
    dt = round(time.time() - t0, 2)
    print(f"\nQUERY: '{q}' ({dt}s)")
    if r.status_code == 200:
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(raw)
        print("  Thought:   ", data.get("thought"))
        print("  Spoken:    ", data.get("spoken_reply"))
        print("  UI Actions:", data.get("ui_actions"))
    else:
        print("  Error:", r.status_code, r.text[:120])

