import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY")

system_prompt = """You are AuraAI, an intelligent conversational AI agent embedded directly into an Electronic Lab Notebook (ELN).
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
- If user asks to open something (e.g., 'open barcode scanner', 'show inventory', 'equipment'), emit OPEN_MODAL with the target.
- If user asks to close, dismiss, or exit something (e.g., 'close barcode scanner', 'close modal', 'exit modal'), emit CLOSE_MODAL with the target.
- If user asks about your features or capabilities ('what are the features you have', 'what can you do', 'who are you'), set action_required=false, ui_actions=[], and summarize your capabilities: hands-free voice note dictation, protocol note creation, chemical & reagent inventory tracking, dilution calculations, barcode scanning, and equipment booking.
- If user dictates a note or observation ('record note: ...', 'note down: ...'), emit APPEND_NOTE with the observation text.
- If user registers a reagent ('add reagent 10X PBS 500 mL'), emit ADD_REAGENT with parsed name, quantity, unit, lot, location.
- If user asks to calculate a dilution, emit CALCULATE_AND_INSERT with markdown dilution protocol table.
"""

def call_gemini(user_msg):
    candidate_models = [
        "gemini-3-flash-preview",
        "gemini-3.8-flash-lite-tts",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
    ]
    combined_prompt = f"{system_prompt}\n\n[USER]: {user_msg}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": combined_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}
    }
    for cand in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{cand}:generateContent?key={key}"
        try:
            r = requests.post(url, json=payload, timeout=6.0)
            if r.status_code == 200:
                raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw), cand
        except Exception as e:
            continue
    raise RuntimeError("All models failed")

tests = [
    "close the barcode scanner",
    "open barcode scanner",
    "what are the features you have",
    "record note: observed clear lysis after 15 min at 56C",
    "add reagent 10X PBS Buffer 500 mL location Shelf B"
]

print("TESTING DIRECT GEMINI CANDIDATE POOL:")
for q in tests:
    res, model_used = call_gemini(q)
    print(f"\nUser: '{q}' (via {model_used})")
    print(f"  Thought:    {res.get('thought')}")
    print(f"  Spoken:     {res.get('spoken_reply')}")
    print(f"  UI Actions: {res.get('ui_actions')}")

