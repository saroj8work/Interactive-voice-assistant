# Architectural Specification: Conversational Voice Assistant Agent

## 1. Overview & Open-Source Lineage
This application is an intelligent, purely conversational Voice Assistant Agent backend built with **Python 3.12**, **FastAPI**, and **Pydantic / PydanticAI**. Designed strictly as a headless, decoupled **REST API service**, it can interface with any external UI client (React, Vue, Flutter, iOS, Android, or desktop applications).

### Open-Source References (Public Licenses)
Our design incorporates patterns from leading open-source projects:
* **[Pipecat AI](https://github.com/pipecat-ai/pipecat) (MIT License)**: Real-time turn-taking pipeline, audio frame ingestion, and modular STT/TTS abstractions.
* **[Home Assistant Assist](https://github.com/home-assistant/core) (Apache 2.0 License)**: Conversational intent classification taxonomy and device/system control router.
* **[PydanticAI](https://github.com/pydantic/pydantic-ai) (MIT License)**: Type-safe structured output schemas, dependency injection, and model-agnostic agent tools.
* **[ReAct & Plan-and-Solve](https://arxiv.org/abs/2210.03629)**: Deconstructing complex or composite voice commands into ordered, dependency-resolved action steps.

---

## 2. End-to-End Pipeline Architecture

> For the interactive Mermaid diagram, lifecycle stages, and concrete dialogue execution traces, see [WORKFLOW.md](WORKFLOW.md).

```
 🎙️ Audio Ingestion (WAV/MP3/WEBM/Base64) 
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
┌────────────────────────────────────────────────────────┐
│               Safe Tool Execution Engine               │
│  ├─ Open-Meteo Weather Tool                            │
│  ├─ AST-Safe Math & Percentage Calculator              │
│  ├─ Host System Info & Utility Launcher                │
│  ├─ Local Notes & Memo Persistence Storage             │
│  ├─ Background Countdown Timers & Reminders            │
│  └─ Markdown Domain Knowledge Search                   │
└────────────────────────────────────────────────────────┘
        │
        ▼
 [ Natural Conversational Response Synthesis ]
        │
        ▼
   [ Text-to-Speech (TTS) Engine ]
        │
        ▼
 🔊 Spoken Audio Response (WAV / Base64 Payload) + REST JSON Response
```

---

## 3. Core Subsystems

### 3.1. Conversational Dialogue Manager & Action Identifier
* **Location**: `app/agent/conversational.py`
* **Functionality**:
  * Tracks multi-turn dialogue history via `ConversationSession`.
  * Resolves conversational coreferences (e.g., "What about there?", "Note that down").
  * Automatically detects whether a turn is purely conversational chit-chat or requires one or more actions.
  * Formulates warm, natural language spoken replies wrapping the action execution results.

### 3.2. Markdown Domain Knowledge Engine
* **Location**: `app/knowledge/markdown_loader.py`
* **Knowledge Source**: `data/domain_knowledge.md` (configurable via `DOMAIN_KNOWLEDGE_FILE`).
* **Functionality**:
  * Ingests, parses, and sections `.md` files by headers (`#`, `##`, `###`).
  * Extracts summaries and indexed keyword vectors.
  * Performs hybrid scoring for user queries and informs the conversational agent about business rules, support hours, device presets, policies, and FAQs.
  * Supports runtime reloads via `PUT /api/knowledge`.

### 3.3. Intent Classifier & Entity Extraction
* **Location**: `app/nlu/classifier.py` and `app/nlu/models.py`
* **Intents**:
  * `weather_query`: Real-time weather, temperature, humidity.
  * `calculation_math`: Arithmetic, percentages, tips, conversions.
  * `productivity_timer`: Timers, alarms, countdowns, reminders.
  * `file_note_management`: Creating, searching, and listing notes.
  * `system_control`: Date, time, CPU cores, system platform stats.
  * `web_search_knowledge`: Domain knowledge retrieval from the `.md` file.
  * `conversational_chat`: Greetings, identity, assistance, farewells.

### 3.4. Action Planner
* **Location**: `app/planner/planner.py`
* **Functionality**:
  * Deconstructs voice commands into single-step or composite multi-step plans.
  * Example: `"Calculate 20% of 150 and save to note titled Dinner Tip"` produces:
    * `step_1`: Calculator tool evaluating `(20 / 100) * 150`.
    * `step_2`: Note tool saving note with result of `step_1` as dependency.

### 3.5. Tool Execution Registry
* **Location**: `app/tools/`
* **Safety First**:
  * Calculator uses Python's `ast` (Abstract Syntax Tree) to parse mathematical expressions safely without dangerous `eval()`.
  * System tools restrict application launching to a strict whitelist (`notepad`, `calculator`, `terminal`).
  * Weather tool leverages the free, public Open-Meteo API with offline fallback.

---

## 4. REST API Endpoint Catalog
All endpoints return standard JSON responses with CORS enabled for external web, mobile, and desktop frontend clients:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status, metadata, and endpoint index |
| `GET` | `/docs` | Interactive Swagger / OpenAPI documentation |
| `GET` | `/redoc` | ReDoc API specifications |
| `GET` | `/api/health` | Health check endpoint |
| `POST` | `/api/conversation/chat` | Natural multi-turn conversation & action execution |
| `GET` | `/api/conversation/history/{session_id}` | Retrieve session history |
| `DELETE` | `/api/conversation/{session_id}` | Reset conversation session |
| `POST` | `/api/command` | Execute structured voice/text command |
| `POST` | `/api/voice/process-file` | Ingest audio file (WAV/MP3/WEBM), transcribe, plan & execute |
| `POST` | `/api/voice/process-base64` | Ingest base64 audio payload from frontend mic |
| `POST` | `/api/classify` | Intent classification & entity extraction |
| `POST` | `/api/plan` | Generate action plan without executing |
| `POST` | `/api/pydantic/plan-and-classify` | PydanticAI-validated classification & plan |
| `POST` | `/api/tts` | Synthesize text to spoken audio (WAV / Base64) |
| `GET` | `/api/tools` | List all available registered tools & schemas |
| `GET` | `/api/timers` | List active background countdown timers |
| `GET` | `/api/knowledge` | View parsed Markdown domain knowledge sections |
| `POST` | `/api/knowledge/query` | Search the Markdown domain knowledge base |
| `PUT` | `/api/knowledge` | Live update the `.md` domain knowledge content |

