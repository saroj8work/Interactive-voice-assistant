# Interactive Voice Assistant Agent

An intelligent, purely conversational Voice Assistant Agent backend built with **Python 3.12**, **FastAPI**, and **Pydantic / PydanticAI**.

Designed as a decoupled **REST API service** ready to connect to any external user interface (React, Vue, Flutter, iOS, Android, or desktop applications).

---

## 🌟 Key Features

* 💬 **Purely Conversational & Context-Aware**: Speak naturally in multi-turn dialogues. The agent remembers conversational context, resolves coreferences (e.g., *"What about there?"*, *"Save that to my notes"*), and wraps action outcomes into natural spoken replies.
* ⚡ **Automatic Action Identification & Execution**: Distinguishes between casual conversation and action requests. Automatically plans and executes tools during dialogue.
* 📚 **Markdown-Driven Domain Knowledge (`.md`)**: The agent's knowledge base is ingested directly from a Markdown file (`data/domain_knowledge.md`). Easily customize support guides, FAQs, policies, and device control rules by editing standard markdown.
* 📋 **Multi-Step Action Planning**: Automatically breaks down complex or composite voice commands into ordered steps with parameter dependency resolution (e.g., *calculate tip → format note → save to disk*).
* 🛡️ **Pydantic & PydanticAI Type Safety**: Built with type-safe schemas for inputs, outputs, tool definitions, and structured planning.
* 🛠️ **Built-in Safe Tools**:
  * **Weather**: Real-time temperature, humidity, and conditions worldwide (Open-Meteo public API).
  * **Calculator**: Safe math evaluations using Python AST parser (no unsafe `eval()`).
  * **System**: Operating system stats, CPU cores, date/time, and whitelisted utility launch.
  * **Notes & Memos**: Create, list, search, and persist notes locally on disk (`./data/notes`).
  * **Productivity Timers**: Background countdown timers and reminders.
  * **Domain Knowledge Search**: Semantic section retrieval from `.md` files.
* 🎙️ **Flexible Audio & Voice Ingestion**: Ingests raw audio files (`.wav`, `.mp3`, `.webm`), base64 audio streams, or pre-transcribed text with automatic Text-to-Speech (TTS) audio response generation.
* 🌐 **Production-Ready REST API with CORS**: Ready for cross-origin requests from any frontend framework with interactive OpenAPI Swagger documentation at `/docs`.

---

## 🏗️ Architecture & Workflow

> 📖 **Comprehensive Visual Guide**: See [WORKFLOW.md](WORKFLOW.md) for the full Mermaid flowchart, lifecycle stages, and execution traces.

```
🎙️ Voice / Audio Input (WAV, MP3, WEBM, or Base64)
                   │
                   ▼
         [ Speech-to-Text (STT) ]
                   │
                   ▼
    [ Conversational Dialogue Manager ] ◄───► [ Multi-Turn Session Memory ]
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
[ Intent Classifier ]  [ Markdown Domain Knowledge Base (.md) ]
        │                     │
        ▼                     ▼
 [ Action Planner ] ◄─────────┘
        │
        ▼
   [ Action Plan (Ordered PlanSteps with Dependencies) ]
        │
        ▼
   [ Safe Tool Execution Registry ]
   (Weather, Calculator, System, Notes, Timers, Markdown Knowledge)
        │
        ▼
 [ Natural Conversational Response Synthesis ]
        │
        ▼
   [ Text-to-Speech (TTS) Engine ]
        │
        ▼
 🔊 Spoken Audio Response (WAV / Base64) + REST JSON Response
```

*Open-Source Lineage*: Inspired by open-source standards from **[Pipecat AI](https://github.com/pipecat-ai/pipecat)** (MIT), **[Home Assistant Assist](https://github.com/home-assistant/core)** (Apache 2.0), and **[PydanticAI](https://github.com/pydantic/pydantic-ai)** (MIT).

---

## 🚀 Quickstart

### 1. Requirements
* Python 3.10+ (Tested on Python 3.12)
* pip

### 2. Installation
```bash
git clone https://github.com/your-username/Interactive-voice-assistant.git
cd Interactive-voice-assistant

# Install dependencies
pip install -r requirements.txt
```

### 3. Model Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Set your chosen model provider and credentials in `.env`:
```ini
# Choose Provider: 'gemini' | 'groq' | 'openai' | 'anthropic' | 'ollama'
MODEL_PROVIDER=gemini

# Specific Model Name (Optional, defaults to provider recommendation)
# Examples:
#   Gemini: gemini-1.5-flash | gemini-2.0-flash
#   Groq:   llama-3.3-70b-versatile | llama-3.1-8b-instant
#   OpenAI: gpt-4o-mini | gpt-4o
#   Ollama: llama3.2 | qwen2.5
MODEL_NAME=gemini-1.5-flash

# API Credentials for your provider:
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434

# Path to Domain Knowledge Markdown File:
DOMAIN_KNOWLEDGE_FILE=./data/domain_knowledge.md
```

> **Dynamic Runtime Updates**: You can also check or update model credentials on the fly via the REST API (`GET /api/config/model` and `POST /api/config/model`).

### 4. Running the Server
```bash
python main.py
```
The server will start at `http://localhost:8000`.

* **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc API Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## ⚙️ Model Configuration API

### Check Active Model Status
```bash
curl -X GET "http://localhost:8000/api/config/model"
```
**Response**:
```json
{
  "model_provider": "gemini",
  "model_name": "gemini-1.5-flash",
  "configured": true,
  "has_gemini_key": true,
  "has_groq_key": false,
  "has_openai_key": false,
  "has_anthropic_key": false,
  "ollama_base_url": "http://localhost:11434",
  "domain_knowledge_file": "C:\\...\\data\\domain_knowledge.md"
}
```

### Switch Model Provider Dynamically
```bash
curl -X POST "http://localhost:8000/api/config/model" \
     -H "Content-Type: application/json" \
     -d '{
       "model_provider": "groq",
       "model_name": "llama-3.3-70b-versatile",
       "groq_api_key": "gsk_your_key_here"
     }'
```

## 📡 REST API Examples

### 1. Conversational Voice Chat (Multi-Turn Dialogue)
Naturally converse with the agent. The agent detects implicit or explicit actions automatically:
```bash
curl -X POST "http://localhost:8000/api/conversation/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Hey, what is the weather like in Tokyo right now?",
       "session_id": "user_session_101",
       "generate_audio": true
     }'
```

**Response**:
```json
{
  "session_id": "user_session_101",
  "user_message": "Hey, what is the weather like in Tokyo right now?",
  "assistant_reply": "The current weather in Tokyo (Japan) is Clear sky with a temperature of 21.2°C, humidity of 48%, and wind speed of 7.4 km/h. Would you like me to note this down or check another city?",
  "action_identified": true,
  "intent": "weather_query",
  "confidence": 0.95,
  "executed_tools": [
    {
      "tool": "weather",
      "description": "Fetch weather forecast for 'Tokyo'",
      "status": "completed",
      "message": "The current weather in Tokyo (Japan) is Clear sky with a temperature of 21.2°C..."
    }
  ],
  "audio_base64": "UklGRiQ...",
  "turn_latency_ms": 115.4
}
```

### 2. Follow-Up Dialogue with Coreference Memory
```bash
curl -X POST "http://localhost:8000/api/conversation/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Please take a note with that info for my travel itinerary",
       "session_id": "user_session_101"
     }'
```

### 3. Querying Domain Knowledge from Markdown (`.md`)
```bash
curl -X POST "http://localhost:8000/api/knowledge/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is the return policy?",
       "top_k": 2
     }'
```

### 4. Updating Domain Knowledge at Runtime
```bash
curl -X PUT "http://localhost:8000/api/knowledge" \
     -H "Content-Type: application/json" \
     -d '{
       "content": "# Updated Knowledge Base\n\n## Return Policy\nAll items can be returned within 45 days."
     }'
```

### 5. Composite Action Command Execution
```bash
curl -X POST "http://localhost:8000/api/command" \
     -H "Content-Type: application/json" \
     -d '{
       "command": "Calculate 15% tip on $85 and note it down as Lunch Expense"
     }'
```

### 6. Process Spoken Audio File (STT → NLU → Action → TTS)
```bash
curl -X POST "http://localhost:8000/api/voice/process-file" \
     -F "audio_file=@sample_voice.wav" \
     -F "generate_audio=true"
```

---

## 🧪 Testing

Run the comprehensive unit and integration test suite:
```bash
python -m pytest -v
```

All 39 unit and integration tests verify:
* Conversational turn memory and coreference resolution
* Markdown domain knowledge ingestion and querying
* Pydantic & PydanticAI structured planning schemas
* Tool safety (AST calculator sandbox against code injection)
* Intent classification and entity extraction
* REST endpoints and CORS headers

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
Open-source reference implementations inspired by Pipecat AI, Home Assistant Assist, and PydanticAI.
